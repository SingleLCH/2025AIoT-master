# -*- coding: utf-8 -*-
"""
作业问答页面
包含TODO列表界面、摄像头预览和完整的流程控制
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QStackedWidget, QFrame, QGridLayout)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QBrush
from embedded_camera_widget import EmbeddedCameraWidget
from homework_qa_handler import HomeworkQAHandler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TodoStepWidget(QWidget):
    """单个TODO步骤组件"""
    
    def __init__(self, step_number: int, title: str, description: str, parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_completed = False
        self.is_current = False
        # 设置背景颜色
        # self.setFixedWidth(400)
        # self.setStyleSheet("""
        #     QWidget {
        #         background-color: white;
        #         border-radius: 10px;
        #         border: 1px solid #dee2e6;
        #     }
        # """)
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout()  # 水平布局
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # 步骤图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                color: white;
            }
        """)
        layout.addWidget(self.icon_label)
        
        # 步骤内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("微软雅黑", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #000000;")
        content_layout.addWidget(self.title_label)
        
        self.desc_label = QLabel(self.description)
        self.desc_label.setFont(QFont("微软雅黑", 14))
        # self.desc_label.setStyleSheet("color: #7f8c8d;")
        self.desc_label.setStyleSheet("color: #000000;")
        content_layout.addWidget(self.desc_label)
        
        layout.addLayout(content_layout, 1)
        
        self.setLayout(layout)
        self.update_status()
    
    def set_completed(self):
        """设置为已完成状态"""
        self.is_completed = True
        self.is_current = False
        self.update_status()
    
    def set_current(self):
        """设置为当前步骤"""
        self.is_current = True
        self.is_completed = False
        self.update_status()
    
    def set_pending(self):
        """设置为待执行状态"""
        self.is_current = False
        self.is_completed = False
        self.update_status()
    
    def update_status(self):
        """更新状态显示"""
        if self.is_completed:
            # 已完成：绿色背景，对号图标
            self.icon_label.setText("✓")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #A3BE8C;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: #000000; 
                }
            """)# color: #2E3440; 
            # self.title_label.setStyleSheet("color: #A3BE8C; font-weight: bold;")
            self.title_label.setStyleSheet("color: #000000; font-weight: bold;")
            self.setStyleSheet("QWidget { background-color: #FFFFFF; border-left: 4px solid #A3BE8C; color: #ECEFF4; }")  # background-color: #2F3A2F
            
        elif self.is_current:
            # 当前步骤：蓝色背景，数字图标
            self.icon_label.setText(str(self.step_number))
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #81A1C1;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: #000000;
                }
            """)
            self.title_label.setStyleSheet("color: #81A1C1; font-weight: bold;")
            # self.title_label.setStyleSheet("color: #000000; font-weight: bold;")
            self.setStyleSheet("QWidget { background-color: #FFFFFF; border-left: 4px solid #81A1C1; color: #ECEFF4; }")
            
        else:
            # 待执行：灰色背景，空心圆图标
            self.icon_label.setText("○")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #6C7B7D;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: #000000;
                }
            """)
            self.title_label.setStyleSheet("color: #000000;") # color: #6C7B7D;
            self.setStyleSheet("QWidget { background-color: #FFFFFF; border-left: 4px solid #6C7B7D; color: #ECEFF4; }")


class HomeworkQAPage(QWidget):
    """作业问答主页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    process_completed = pyqtSignal(dict)  # 流程完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 组件
        self.qa_handler = None
        self.camera_widget = None
        
        # TODO步骤组件
        self.step_widgets = []
        
        self.setup_ui()
        self.init_handler()
    
    def setup_ui(self):
        """设置界面"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧：TODO列表
        self.setup_todo_panel(main_layout)
        
        # 右侧：摄像头预览
        self.setup_camera_panel(main_layout)
        
        self.setLayout(main_layout)
    
    def setup_todo_panel(self, main_layout):
        """设置TODO列表面板"""
        todo_frame = QFrame()
        todo_frame.setFixedWidth(400)
        todo_frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        todo_layout = QVBoxLayout()
        todo_layout.setContentsMargins(20, 20, 20, 20)
        todo_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("作业问答流程")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 15px;
                background-color: #2E3440;
                border-radius: 8px;
                border-left: 6px solid #B48EAD;
            }
        """)
        todo_layout.addWidget(title_label)
        
        # TODO步骤
        steps_data = [
            (1, "第一步：拍摄题目", "拍摄需要问答的题目照片"),
            (2, "第二步：科目识别", "语音识别你要询问的科目"),
            (3, "第三步：困惑点识别", "语音识别你遇到的困惑"),
            (4, "第四步：提交分析", "上传数据并等待AI分析")
        ]
        
        for step_num, title, desc in steps_data:
            step_widget = TodoStepWidget(step_num, title, desc)
            step_widget.set_pending()  # 初始状态为待执行
            self.step_widgets.append(step_widget)
            todo_layout.addWidget(step_widget)
        
        # 简化状态显示（仅显示当前状态，无按钮和提示）
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("微软雅黑", 14, QFont.Bold))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #A3BE8C;
                padding: 20px;
                background-color: #2F3A2F;
                border-radius: 8px;
                border: 2px solid #A3BE8C;
            }
        """)
        todo_layout.addWidget(self.status_label)
        
        todo_frame.setLayout(todo_layout)
        main_layout.addWidget(todo_frame)
    
    def setup_camera_panel(self, main_layout):
        """设置摄像头预览面板"""
        camera_frame = QFrame()
        camera_frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        camera_layout = QVBoxLayout()
        camera_layout.setContentsMargins(20, 20, 20, 20)
        camera_layout.setSpacing(15)
        
        # 摄像头标题
        camera_title = QLabel("摄像头预览")
        camera_title.setAlignment(Qt.AlignCenter)
        camera_title.setFont(QFont("微软雅黑", 24, QFont.Bold))
        camera_title.setStyleSheet("""
            QLabel {
                color: #ECEFF4;
                padding: 10px;
                background-color: #2E3440;
                border-radius: 6px;
            }
        """)
        camera_layout.addWidget(camera_title)
        
        # 摄像头预览组件
        self.camera_widget = EmbeddedCameraWidget(
            title="拍照摄像头",
            preview_size=(640, 480),
            clip_mode=2
        )
        camera_layout.addWidget(self.camera_widget)
        
        # 预览状态
        self.camera_status_label = QLabel("摄像头准备中...")
        self.camera_status_label.setAlignment(Qt.AlignCenter)
        self.camera_status_label.setFont(QFont("微软雅黑", 18))
        self.camera_status_label.setStyleSheet("""
            QLabel {
                color: #D8DEE9;
                padding: 10px;
                background-color: #434C5E;
                border-radius: 5px;
            }
        """)
        camera_layout.addWidget(self.camera_status_label)
        
        camera_frame.setLayout(camera_layout)
        main_layout.addWidget(camera_frame, 1)
    
    def init_handler(self):
        """初始化处理器"""
        try:
            self.qa_handler = HomeworkQAHandler()
            
            # 连接信号
            self.qa_handler.process_started.connect(self.on_process_started)
            self.qa_handler.step_completed.connect(self.on_step_completed)
            self.qa_handler.photo_captured.connect(self.on_photo_captured)
            self.qa_handler.subject_recognition_started.connect(self.on_subject_recognition_started)
            self.qa_handler.subject_recognition_completed.connect(self.on_subject_recognition_completed)
            self.qa_handler.difficulty_recognition_started.connect(self.on_difficulty_recognition_started)
            self.qa_handler.difficulty_recognition_completed.connect(self.on_difficulty_recognition_completed)
            self.qa_handler.upload_started.connect(self.on_upload_started)
            self.qa_handler.upload_completed.connect(self.on_upload_completed)
            self.qa_handler.process_completed.connect(self.on_process_completed)
            self.qa_handler.error_occurred.connect(self.on_error_occurred)
            self.qa_handler.back_requested.connect(self.back_requested.emit)
            
            # 设置摄像头
            camera = self.qa_handler.get_camera()
            if camera:
                self.camera_widget.set_camera(camera)
                self.camera_status_label.setText("摄像头已就绪")
            else:
                self.camera_status_label.setText("摄像头初始化失败")
            
            logger.info("作业问答页面初始化完成")
            
            # 自动启动流程，不需要用户点击按钮
            self.auto_start_process()
            
        except Exception as e:
            logger.error(f"初始化处理器失败: {e}")
            self.status_label.setText(f"初始化失败: {e}")
    
    def auto_start_process(self):
        """自动开始流程（页面初始化后直接启动）"""
        if self.qa_handler:
            logger.info("自动启动作业问答流程")
            self.qa_handler.start_process()
    
    def start_process(self):
        """开始流程（保留兼容性）"""
        if self.qa_handler:
            self.qa_handler.start_process()
    
    def handle_control_command(self, action: str):
        """处理MQTT控制指令"""
        logger.info(f"作业问答页面接收到控制指令: {action}")

        if action == 'back':  # 6-0-2 返回主菜单
            self.back_requested.emit()
        else:
            # 将其他指令转发给作业问答处理器
            if self.qa_handler:
                logger.info(f"转发控制指令给作业问答处理器: {action}")
                self.qa_handler._on_mqtt_command(action)
            else:
                logger.warning("作业问答处理器未初始化，无法处理指令")
    
    # 信号处理方法
    def on_process_started(self):
        """流程开始"""
        self.status_label.setText("请拍摄题目照片")
        self.step_widgets[0].set_current()
        logger.info("作业问答流程已开始")
    
    def on_step_completed(self, step_number: int):
        """步骤完成"""
        logger.info(f"步骤 {step_number} 已完成")
        
        # 更新步骤状态
        if 1 <= step_number <= len(self.step_widgets):
            self.step_widgets[step_number - 1].set_completed()
            
            # 设置下一步为当前步骤
            if step_number < len(self.step_widgets):
                self.step_widgets[step_number].set_current()
                
                # 根据完成的步骤更新状态显示
                if step_number == 1:
                    self.status_label.setText("请进行科目识别")
                elif step_number == 2:
                    self.status_label.setText("请进行困惑点识别")
                elif step_number == 3:
                    self.status_label.setText("准备数据上传")
    
    def on_photo_captured(self, photo_path: str):
        """拍照完成"""
        self.status_label.setText("拍照成功！正在进入科目识别...")
        self.camera_widget.flash_capture()  # 闪烁效果
        logger.info(f"照片已保存: {photo_path}")
    
    def on_subject_recognition_started(self):
        """科目识别开始"""
        self.status_label.setText("科目识别中，请说出你要询问的科目...")
        logger.info("科目识别已开始")
    
    def on_subject_recognition_completed(self, subject: str):
        """科目识别完成"""
        self.status_label.setText(f"科目识别完成：{subject}，正在进入困惑点识别...")
        logger.info(f"科目识别结果: {subject}")
    
    def on_difficulty_recognition_started(self):
        """困惑点识别开始"""
        self.status_label.setText("困惑点识别中，请说出你遇到的困惑...")
        logger.info("困惑点识别已开始")
    
    def on_difficulty_recognition_completed(self, difficulty: str):
        """困惑点识别完成"""
        self.status_label.setText(f"困惑点识别完成：{difficulty}，准备上传...")
        logger.info(f"困惑点识别结果: {difficulty}")
    
    def on_upload_started(self):
        """上传开始"""
        self.status_label.setText("正在上传数据到服务器...")
        logger.info("数据上传已开始")
    
    def on_upload_completed(self, result: dict):
        """上传完成"""
        self.status_label.setText("分析完成！按6-0-3返回功能选择")
        logger.info("数据上传完成")
    
    def on_process_completed(self, result_data: dict):
        """流程完成"""
        self.status_label.setText("作业问答流程完成！按6-0-3返回功能选择")
        
        # 重置所有步骤状态
        for step_widget in self.step_widgets:
            step_widget.set_pending()
        
        # 发射完成信号
        self.process_completed.emit(result_data)
        
        logger.info("作业问答流程已完成")
    
    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.status_label.setText(f"错误: {error_msg}")
        
        # 重置步骤状态
        for step_widget in self.step_widgets:
            step_widget.set_pending()
        
        logger.error(f"作业问答流程错误: {error_msg}")
    
    def cleanup(self):
        """清理资源"""
        if self.camera_widget:
            self.camera_widget.stop_preview()
        
        if self.qa_handler:
            self.qa_handler.stop()
            self.qa_handler = None
        
        logger.info("作业问答页面资源已清理") 