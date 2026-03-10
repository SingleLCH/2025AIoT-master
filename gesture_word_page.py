# -*- coding: utf-8 -*-
"""
指尖单词功能页面
实现拍照识别手指指向的单词，并语音播放
包含TODO列表界面、摄像头预览和完整的流程控制
"""

import os
import logging
import glob
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSplitter, QFrame
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from camera_handler import CameraHandler
from embedded_camera_widget import EmbeddedCameraWidget
# from gesture_word_handler import GestureWordHandler  # 现在使用增强版处理器
from todo_step_components import TodoFlowPanel

logger = logging.getLogger(__name__)


class PhotoCaptureHandler(QThread):
    """拍照处理器 - 专门处理拍照功能"""

    # 信号定义
    photo_captured = pyqtSignal(str)  # 拍照完成信号，传递照片路径
    error_occurred = pyqtSignal(str)  # 错误信号
    camera_ready = pyqtSignal(object)  # 摄像头准备就绪信号

    def __init__(self):
        super().__init__()
        self.photo_folder = "gesture_photos"  # 指尖单词照片保存文件夹
        self.camera_handler = None
        self.is_processing = False

        # 确保照片文件夹存在
        self._ensure_photo_folder()

    def _ensure_photo_folder(self):
        """确保照片文件夹存在"""
        if not os.path.exists(self.photo_folder):
            os.makedirs(self.photo_folder)
            logger.info(f"创建指尖单词照片文件夹: {self.photo_folder}")

    def init_camera(self):
        """初始化摄像头"""
        try:
            # 🔧 修复：重新进入时强制重新初始化摄像头
            if self.camera_handler:
                logger.info("清理旧的摄像头处理器...")
                self.camera_handler.close_cameras()
                self.camera_handler = None
            
            logger.info("初始化指尖单词摄像头处理器...")
            self.camera_handler = CameraHandler()
            # 设置照片保存文件夹
            self.camera_handler.photo_folder = self.photo_folder

            # 连接信号
            self.camera_handler.photo_captured.connect(self._on_photo_captured)
            self.camera_handler.error_occurred.connect(self.error_occurred.emit)

            logger.info(f"指尖单词摄像头处理器初始化成功，照片保存到: {self.photo_folder}")

            # 获取拍照摄像头并发送准备信号
            photo_camera = self.camera_handler.get_photo_camera()
            if photo_camera is not None:
                self.camera_ready.emit(photo_camera)
                logger.info("摄像头对象获取成功，已发送准备信号")
            else:
                logger.warning("摄像头对象为None，可能存在初始化问题")
                
            return True
        except Exception as e:
            error_msg = f"初始化摄像头失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def capture_photo(self):
        """拍照"""
        if not self.camera_handler:
            error_msg = "摄像头处理器未初始化"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return

        try:
            logger.info("开始指尖单词拍照...")
            self.is_processing = True
            success = self.camera_handler.capture_photos_for_gesture(photo_count=1)
            logger.info(f"指尖单词拍照结果: {success}")
        except Exception as e:
            error_msg = f"拍照过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self.is_processing = False

    def _on_photo_captured(self, success: bool):
        """处理拍照结果"""
        logger.info(f"拍照完成，成功: {success}")

        if not success:
            self.error_occurred.emit("拍照失败，请重试")
            return

        # 获取最新拍摄的照片路径
        try:
            photo_path = self._get_latest_photo_path()
            if photo_path:
                logger.info(f"拍照成功: {photo_path}")
                self.photo_captured.emit(photo_path)
            else:
                self.error_occurred.emit("拍照成功但无法获取照片路径")
        except Exception as e:
            error_msg = f"获取照片路径失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def _get_latest_photo_path(self):
        """获取最新拍摄的照片路径"""
        try:
            pattern = os.path.join(self.photo_folder, "*.png")
            photo_files = glob.glob(pattern)

            if photo_files:
                # 按修改时间排序，获取最新的文件
                latest_photo = max(photo_files, key=os.path.getmtime)
                return latest_photo
            else:
                return None

        except Exception as e:
            logger.error(f"获取最新照片路径异常: {e}")
            return None

    def cleanup(self):
        """清理资源"""
        logger.info("清理PhotoCaptureHandler资源...")
        if self.camera_handler:
            try:
                # 🔧 修复：正确释放摄像头资源
                self.camera_handler.close_cameras()
                logger.info("摄像头资源已释放")
            except Exception as e:
                logger.warning(f"释放摄像头资源时出错: {e}")
        self.camera_handler = None
        self.is_processing = False
        logger.info("PhotoCaptureHandler资源清理完成")
        logger.info("拍照处理器资源已清理")


class GestureWordPage(QWidget):
    """指尖单词功能页面"""

    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    process_completed = pyqtSignal(str)  # 流程完成信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_handler = None  # 拍照处理器
        self.word_handler = None   # 单词识别处理器
        self.camera_widget = None
        self.recognized_word = ""
        self.status_label = None  # 状态标签
        
        # TODO流程面板
        self.todo_flow_panel = None

        self.setup_ui()
        self.init_handlers()
    
    def setup_ui(self):
        """设置界面"""
        main_layout = QHBoxLayout()  # 水平布局
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 左侧：TODO列表
        self.setup_todo_panel(main_layout)

        # 右侧：识别结果和摄像头预览
        self.setup_content_panel(main_layout)

        self.setLayout(main_layout)
        
    def setup_todo_panel(self, main_layout):
        """设置TODO列表面板"""
        # 指尖单词的操作步骤
        steps_data = [
            (1, "第一步：拍摄单词", "拍摄包含单词的照片"),
            (2, "第二步：识别单词", "AI识别手指指向的单词"),
            (3, "第三步：发音练习", "三遍发音播放，间隔1秒"),
            (4, "第四步：发音评测", "最多3轮评测，90分及格")
        ]
        
        self.todo_flow_panel = TodoFlowPanel("指尖单词流程", steps_data)
        main_layout.addWidget(self.todo_flow_panel)

    def setup_content_panel(self, main_layout):
        """设置内容面板"""
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # 主标题
        title_label = QLabel("指尖单词 - 单词识别与朗读")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 5px;
                background-color: #2E3440;
                border-radius: 8px;
                border-left: 4px solid #EBCB8B;
            }
        """)
        title_label.setFixedHeight(40)
        content_layout.addWidget(title_label)

        # 创建水平分割器（两列布局）
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #bdc3c7;
                width: 2px;
            }
        """)

        # 左侧面板：识别结果区域
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右侧面板：摄像头预览区域
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置两列的比例（左侧:右侧 = 1:1.5）
        splitter.setSizes([400, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter)

        content_frame.setLayout(content_layout)
        main_layout.addWidget(content_frame)

    def create_left_panel(self):
        """创建左侧面板：识别结果区域"""
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            QWidget {
                background-color: #3B4252;
                border-radius: 12px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        layout = QVBoxLayout(left_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel("🔍 识别结果")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("微软雅黑", 18, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 10px;
                background-color: #2E3440;
                border-radius: 8px;
                border-left: 4px solid #88C0D0;
            }
        """)
        layout.addWidget(title)

        # 单词显示区域（重用原有方法但调整样式）
        self.word_display_frame = self.create_word_display()
        layout.addWidget(self.word_display_frame)

        # 分数显示区域
        self.score_display_frame = self.create_score_display()
        layout.addWidget(self.score_display_frame)

        # 添加弹性空间
        layout.addStretch()

        return left_widget

    def create_right_panel(self):
        """创建右侧面板：摄像头预览区域"""
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            QWidget {
                background-color: #3B4252;
                border-radius: 12px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel("📷 摄像头预览")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("微软雅黑", 18, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 10px;
                background-color: #2E3440;
                border-radius: 8px;
                border-left: 4px solid #BF616A;
            }
        """)
        layout.addWidget(title)

        # 摄像头预览（重用原有方法）
        self.camera_widget = EmbeddedCameraWidget(
            title="指尖单词摄像头",
            preview_size=(600, 450),
            clip_mode=1
        )
        layout.addWidget(self.camera_widget)

        # 添加弹性空间
        layout.addStretch()

        return right_widget

    def create_word_display(self):
        """创建单词显示区域"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 2px solid #3498db;
                color: #ECEFF4;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 单词标题
        word_title = QLabel("识别单词")
        word_title.setAlignment(Qt.AlignCenter)
        word_title.setFont(QFont("微软雅黑", 16, QFont.Bold))
        word_title.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 8px;
                background-color: #2E3440;
                border-radius: 6px;
            }
        """)
        layout.addWidget(word_title)

        # 单词显示标签
        self.word_label = QLabel("等待识别...")
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.word_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 20px;
                background-color: #434C5E;
                border-radius: 8px;
                border: 1px solid #4C566A;
            }
        """)
        layout.addWidget(self.word_label)

        # 单词播放按钮
        self.play_button = QPushButton("🔊 播放发音")
        self.play_button.setEnabled(False)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #88C0D0;
                color: #2E3440;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5E81AC;
                color: #ECEFF4;
            }
            QPushButton:disabled {
                background-color: #4C566A;
                color: #6C7B7D;
            }
        """)
        layout.addWidget(self.play_button)

        return frame

    def create_score_display(self):
        """创建分数显示区域"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 2px solid #e74c3c;
                color: #ECEFF4;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 分数标题
        score_title = QLabel("发音评测")
        score_title.setAlignment(Qt.AlignCenter)
        score_title.setFont(QFont("微软雅黑", 16, QFont.Bold))
        score_title.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 8px;
                background-color: #2E3440;
                border-radius: 6px;
            }
        """)
        layout.addWidget(score_title)

        # 轮次显示标签
        self.round_label = QLabel("第 1 轮")
        self.round_label.setAlignment(Qt.AlignCenter)
        self.round_label.setFont(QFont("微软雅黑", 16, QFont.Bold))
        self.round_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 10px;
                background-color: #5E81AC;
                border-radius: 6px;
                border: 1px solid #81A1C1;
            }
        """)
        layout.addWidget(self.round_label)

        # 分数显示标签
        self.score_label = QLabel("得分：-- / 100")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.score_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 15px;
                background-color: #434C5E;
                border-radius: 8px;
                border: 1px solid #4C566A;
            }
        """)
        layout.addWidget(self.score_label)

        # 录音按钮
        self.record_button = QPushButton("🎤 开始录音")
        self.record_button.setEnabled(False)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #95a5a6;
            }
        """)
        layout.addWidget(self.record_button)

        return frame

    def init_handlers(self):
        """初始化处理器"""
        # 初始化拍照处理器
        self.photo_handler = PhotoCaptureHandler()
        self.photo_handler.photo_captured.connect(self.on_photo_captured)
        self.photo_handler.error_occurred.connect(self.on_error_occurred)
        self.photo_handler.camera_ready.connect(self.on_camera_ready)

        # 初始化单词处理器 - 使用增强版处理器
        from enhanced_gesture_word_handler import EnhancedGestureWordHandler
        self.word_handler = EnhancedGestureWordHandler()
        self.word_handler.word_recognized.connect(self.on_word_recognized)
        self.word_handler.tts_started.connect(self.on_tts_started)
        self.word_handler.tts_completed.connect(self.on_tts_completed)
        self.word_handler.status_updated.connect(self.on_status_updated)
        self.word_handler.error_occurred.connect(self.on_error_occurred)
        
        # 连接增强版处理器的额外信号
        self.word_handler.recording_started.connect(self.on_recording_started)
        self.word_handler.recording_completed.connect(self.on_recording_completed)
        self.word_handler.score_updated.connect(self.on_score_updated)
        self.word_handler.process_completed.connect(self.on_process_completed)

        # 初始化摄像头
        self.photo_handler.init_camera()

        # 连接按钮信号
        self.play_button.clicked.connect(self._play_word_audio)
        self.record_button.clicked.connect(self._start_recording)
        
        # 启动流程
        self.start_process()

    def start_process(self):
        """开始流程"""
        logger.info("开始指尖单词流程")
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("准备拍照\n请将手指指向单词")

    def on_camera_ready(self, camera):
        """摄像头准备就绪"""
        if self.camera_widget:
            self.camera_widget.set_camera(camera)
            self.camera_widget.start_preview()
            logger.info("摄像头预览已启动")

    def on_photo_captured(self, photo_path: str):
        """拍照完成"""
        logger.info(f"拍照完成: {photo_path}")
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(1)
        self.todo_flow_panel.set_step_current(2)
        self.todo_flow_panel.update_status("拍照完成\n正在识别单词...")
        
        # 闪烁效果
        if self.camera_widget:
            self.camera_widget.flash_capture()
        
        # 开始识别
        self.word_handler.recognize_word_from_image(photo_path)

    def on_word_recognized(self, word: str):
        """单词识别完成"""
        logger.info(f"单词识别完成: {word}")
        self.recognized_word = word
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(2)
        self.todo_flow_panel.set_step_current(3)
        self.todo_flow_panel.update_status(f"识别成功：{word}\n开始发音练习...")
        
        # 更新界面
        self.word_label.setText(word)
        self.play_button.setEnabled(True)
        
        # 重置轮次显示
        self.round_label.setText("第 1 轮")

    def on_tts_started(self, word: str):
        """语音播放开始"""
        logger.info(f"开始播放: {word}")
        self.todo_flow_panel.update_status(f"正在播放：{word}")

    def on_tts_completed(self):
        """语音播放完成"""
        logger.info("语音播放完成")
        
        # 增强版处理器会自动继续流程，不需要手动启用录音按钮
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(3)
        self.todo_flow_panel.set_step_current(4)
        self.todo_flow_panel.update_status("播放完成\n等待下一步...")

    def on_status_updated(self, message: str, color: str):
        """状态更新"""
        logger.info(f"状态更新: {message}")
        self.todo_flow_panel.update_status(message, color)

    def on_error_occurred(self, error_msg: str):
        """错误发生"""
        logger.error(f"错误: {error_msg}")
        self.todo_flow_panel.update_status(f"错误: {error_msg}","#e74c3c")

    def on_recording_started(self):
        """录音开始"""
        logger.info("录音开始")
        self.todo_flow_panel.update_status("录音中\n请大声说出单词...")
        self.record_button.setText("🎤 录音中...")
        self.record_button.setEnabled(False)

    def on_recording_completed(self, recording_path: str):
        """录音完成"""
        logger.info(f"录音完成: {recording_path}")
        self.todo_flow_panel.update_status("录音完成\n正在评测...")
        self.record_button.setText("🎤 开始录音")

    def on_score_updated(self, score: float, round_num: int):
        """分数更新"""
        logger.info(f"分数更新: {score} (第{round_num}轮)")
        
        # 更新轮次显示
        self.round_label.setText(f"第 {round_num} 轮")
        
        # 更新分数显示
        self.score_label.setText(f"得分：{score:.1f} / 100")
        
        # 根据分数设置颜色
        if score >= 90:
            color = "#27ae60"  # 绿色
        elif score >= 80:
            color = "#f39c12"  # 橙色
        else:
            color = "#e74c3c"  # 红色
            
        self.score_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                padding: 15px;
                background-color: #434C5E;
                border-radius: 8px;
                border: 1px solid #4C566A;
                font-weight: bold;
            }}
        """)

    def on_process_completed(self, word: str, success: bool):
        """流程完成"""
        logger.info(f"流程完成: {word}, 成功: {success}")
        
        if success:
            self.todo_flow_panel.set_step_completed(4)
            self.todo_flow_panel.update_status("指尖单词学习完成！\n请返回功能选择")
        else:
            self.todo_flow_panel.update_status("学习过程中出现错误" "#e74c3c")
        
        # 发射完成信号
        self.process_completed.emit(word)
        
        # 5秒后重置流程
        QTimer.singleShot(5000, self.reset_process)

    def reset_process(self):
        """重置流程"""
        logger.info("重置指尖单词流程")
        
        # 重置TODO状态
        self.todo_flow_panel.reset_all_steps()
        self.todo_flow_panel.update_status("准备就绪")
        
        # 重置界面
        self.word_label.setText("等待识别...")
        self.round_label.setText("第 1 轮")
        self.score_label.setText("得分：-- / 100")
        self.score_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 15px;
                background-color: #434C5E;
                border-radius: 8px;
                border: 1px solid #4C566A;
            }
        """)
        self.play_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.record_button.setText("🎤 开始录音")
        
        # 重置变量
        self.recognized_word = ""

    def capture_photo(self):
        """拍照"""
        if self.photo_handler and not self.photo_handler.is_processing:
            self.photo_handler.capture_photo()
        else:
            logger.warning("拍照处理器未准备好或正在处理中")

    def handle_control_command(self, action: str):
        """处理控制命令"""
        logger.info(f"收到控制命令: {action}")
        
        if action == "confirm":
            # 🔧 修复：处理6-0-1确认信号，执行拍照
            logger.info("指尖识词页面收到确认信号，开始拍照")
            self.capture_photo()
        elif action == "capture":
            self.capture_photo()
        elif action == "play":
            if self.play_button.isEnabled():
                self._play_word_audio()
        elif action == "record":
            if self.record_button.isEnabled():
                self._start_recording()
        elif action == "reset":
            self.reset_process()
        elif action == "back":
            # 6-0-2 返回功能选择页面
            logger.info("指尖单词页面返回")
            self.back_requested.emit()

    def _play_word_audio(self):
        """播放单词音频"""
        if self.recognized_word and self.word_handler:
            logger.info(f"播放单词音频: {self.recognized_word}")
            self.word_handler.start_tts(self.recognized_word)
        else:
            logger.warning("没有识别的单词或处理器未准备好")
            
    def _start_recording(self):
        """开始录音"""
        if self.recognized_word:
            logger.info(f"开始录音评测: {self.recognized_word}")
            # 由于GestureWordHandler没有录音功能，这里暂时只显示状态
            self.todo_flow_panel.update_status("录音功能暂未实现")
        else:
            logger.warning("没有识别的单词")

    def cleanup(self):
        """清理资源"""
        logger.info("清理指尖单词页面资源")
        
        # 🔧 修复：确保摄像头资源正确释放
        if self.photo_handler:
            self.photo_handler.cleanup()
            self.photo_handler = None
        
        if self.word_handler:
            try:
                self.word_handler.cleanup()
            except:
                pass
            self.word_handler = None
        
        if self.camera_widget:
            self.camera_widget.stop_preview()
            self.camera_widget = None
        
        # 重置状态
        self.recognized_word = ""
        
        logger.info("指尖单词页面资源清理完成") 