# -*- coding: utf-8 -*-
"""
拍照搜题三级页面
包含TODO列表界面、摄像头预览和完整的流程控制
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QStackedWidget, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from embedded_camera_widget import EmbeddedCameraWidget
from todo_step_components import TodoFlowPanel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PhotoHomeworkPage(QWidget):
    """拍照搜题三级页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回上一级信号
    process_started = pyqtSignal(str)  # 流程开始信号 (mode: 'school'/'home')
    
    def __init__(self, parent=None, handler=None):
        super().__init__(parent)
        self.current_mode = None  # 'school' 或 'home'
        self.current_stage = None  # 'face_recognition' 或 'photo_homework'
        
        # 摄像头预览组件
        self.face_camera_widget = None
        self.photo_camera_widget = None
        
        # TODO流程面板
        self.todo_flow_panel = None
        
        self.setup_ui()
        
        # 新增：handler为PhotoHomeworkHandler实例
        if handler is not None:
            handler.face_recognition_failed.connect(self.on_face_recognition_failed)
            handler.process_completed.connect(self.on_analysis_completed)
        
    def setup_ui(self):
        """设置界面"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧：TODO列表
        self.setup_todo_panel(main_layout)
        
        # 右侧：摄像头预览和流程控制
        self.setup_content_panel(main_layout)
        
        self.setLayout(main_layout)
        
    def setup_todo_panel(self, main_layout):
        """设置TODO列表面板"""
        # 作业批改的操作步骤（将在start_school_mode/start_home_mode中设置具体步骤）
        self.todo_flow_panel = None
        self.todo_panel_container = QWidget()
        main_layout.addWidget(self.todo_panel_container)
        
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
        content_layout.setSpacing(20)
        
        # 顶部导航栏
        nav_bar = self.create_nav_bar()
        content_layout.addWidget(nav_bar)
        
        # 主内容区域 - 使用堆叠布局切换不同阶段
        self.content_stack = QStackedWidget()
        
        # 人脸识别阶段页面
        self.face_recognition_page = self.create_face_recognition_page()
        self.content_stack.addWidget(self.face_recognition_page)
        
        # 拍照作业阶段页面
        self.photo_homework_page = self.create_photo_homework_page()
        self.content_stack.addWidget(self.photo_homework_page)
        
        content_layout.addWidget(self.content_stack)
        
        content_frame.setLayout(content_layout)
        main_layout.addWidget(content_frame)
        
    def create_nav_bar(self):
        """创建导航栏"""
        nav_frame = QFrame()
        nav_frame.setFixedHeight(60)
        nav_frame.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-bottom: 2px solid #2c3e50;
                border-radius: 8px;
            }
        """)
        
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(20, 10, 20, 10)
        
        # 返回按钮（隐藏，因为只能通过MQTT控制）
        self.back_btn = QPushButton("← 返回")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7b7c;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.back_btn.setVisible(False)  # 隐藏返回按钮，只能通过MQTT控制
        nav_layout.addWidget(self.back_btn)
        
        nav_layout.addStretch()
        
        # 标题
        self.title_label = QLabel("智能作业批改系统")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)
        nav_layout.addWidget(self.title_label)
        
        nav_layout.addStretch()
        
        # 模式指示器
        self.mode_label = QLabel("")
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("""
            QLabel {
                color: #f1c40f;
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
                border: 1px solid #f1c40f;
                border-radius: 15px;
            }
        """)
        nav_layout.addWidget(self.mode_label)
        
        nav_frame.setLayout(nav_layout)
        return nav_frame
        
    def create_face_recognition_page(self):
        """创建人脸识别阶段页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 阶段标题
        stage_label = QLabel("人脸识别")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        stage_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 10px;
                border-left: 5px solid #3498db;
            }
        """)
        layout.addWidget(stage_label)
        
        # 人脸识别摄像头预览
        self.face_camera_widget = EmbeddedCameraWidget(
            title="人脸识别摄像头", 
            preview_size=(720, 540),
            clip_mode = 3
        )
        layout.addWidget(self.face_camera_widget)
        
        # 流程指示
        process_label = QLabel("请将面部对准摄像头，等待系统拍照识别")
        process_label.setAlignment(Qt.AlignCenter)
        process_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 16px;
                padding: 10px;
            }
        """)
        layout.addWidget(process_label)
        
        layout.addStretch()
        page.setLayout(layout)
        return page
        
    def create_photo_homework_page(self):
        """创建拍照作业阶段页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 阶段标题
        stage_label = QLabel("拍摄作业")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        stage_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 10px;
                border-left: 5px solid #e74c3c;
            }
        """)
        layout.addWidget(stage_label)
        
        # 拍照摄像头预览
        self.photo_camera_widget = EmbeddedCameraWidget(
            title="作业拍照摄像头", 
            preview_size=(720, 540),
            clip_mode=2
        )
        layout.addWidget(self.photo_camera_widget)
        
        # 流程指示
        process_label = QLabel("请将作业放在摄像头下方，等待系统拍照")
        process_label.setAlignment(Qt.AlignCenter)
        process_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 16px;
                padding: 10px;
            }
        """)
        layout.addWidget(process_label)
        
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def start_school_mode(self, face_camera, photo_camera):
        """开始学校模式"""
        self.current_mode = 'school'
        self.mode_label.setText("公用模式")
        self.title_label.setText("智能作业批改系统 - 公用模式")
        
        # 创建学校模式的步骤（包含人脸识别）
        if not self.todo_flow_panel:
            steps_data = [
                (1, "第一步：人脸识别", "识别学生身份进行记录"),
                (2, "第二步：拍摄作业", "拍摄需要批改的作业照片"),
                (3, "第三步：AI分析", "上传照片进行智能分析"),
                (4, "第四步：结果展示", "显示批改结果和建议")
            ]
            self.todo_flow_panel = TodoFlowPanel("作业批改流程", steps_data)
            container_layout = QVBoxLayout(self.todo_panel_container)
            container_layout.addWidget(self.todo_flow_panel)
        
        # 设置第一步为当前步骤
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("正在进行人脸识别...")
        
        # 确保摄像头设置和预览启动
        if self.face_camera_widget:
            logger.info(f"设置人脸识别摄像头: {face_camera}")
            self.face_camera_widget.set_camera(face_camera)
            # 强制启动预览
            if face_camera == "SIMULATED_CAMERA" or (face_camera and hasattr(face_camera, 'isOpened') and face_camera.isOpened()):
                self.face_camera_widget.start_preview()
                logger.info("人脸识别摄像头预览已启动")
        
        # 切换到人脸识别页面
        self.current_stage = 'face_recognition'
        self.content_stack.setCurrentWidget(self.face_recognition_page)
        
        logger.info("学校模式开始 - 人脸识别阶段")
        self.process_started.emit('school')
        
    def start_home_mode(self, photo_camera):
        """开始家庭模式"""
        self.current_mode = 'home'
        self.mode_label.setText("个人模式")
        self.title_label.setText("智能作业批改系统 - 个人模式")
        
        # 创建家庭模式的步骤（不包含人脸识别）
        if not self.todo_flow_panel:
            steps_data = [
                (1, "第一步：拍摄作业", "拍摄需要批改的作业照片"),
                (2, "第二步：AI分析", "上传照片进行智能分析"),
                (3, "第三步：结果展示", "显示批改结果和建议")
            ]
            self.todo_flow_panel = TodoFlowPanel("作业批改流程", steps_data)
            container_layout = QVBoxLayout(self.todo_panel_container)
            container_layout.addWidget(self.todo_flow_panel)
        
        # 设置第一步为当前步骤（家庭模式直接从拍摄开始）
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("正在准备拍摄作业...")
        
        # 确保摄像头设置和预览启动
        if self.photo_camera_widget:
            logger.info(f"设置拍照摄像头: {photo_camera}")
            self.photo_camera_widget.set_camera(photo_camera)
            # 强制启动预览
            if photo_camera == "SIMULATED_CAMERA" or (photo_camera and hasattr(photo_camera, 'isOpened') and photo_camera.isOpened()):
                self.photo_camera_widget.start_preview()
                logger.info("拍照摄像头预览已启动")
        
        # 切换到拍照作业页面
        self.current_stage = 'photo_homework'
        self.content_stack.setCurrentWidget(self.photo_homework_page)
        
        logger.info("家庭模式开始 - 拍照作业阶段")
        self.process_started.emit('home')
        
    def on_face_recognition_completed(self, student_info: dict):
        """人脸识别完成（仅在学校模式下使用）"""
        logger.info(f"人脸识别完成: {student_info}")
        
        # 更新流程状态（只有学校模式才会调用此方法）
        if self.current_mode == 'school':
            self.todo_flow_panel.set_step_completed(1)
            self.todo_flow_panel.set_step_current(2)
            
            # 获取学生姓名并显示个性化提示
            student_name = student_info.get('name', '同学')
            self.todo_flow_panel.update_status(f"{student_name}同学，请确认拍摄作业")
        
        # 设置拍照摄像头
        if self.photo_camera_widget:
            # 这里应该从handler获取拍照摄像头
            logger.info("切换到拍照作业阶段")
            self.photo_camera_widget.start_preview()
        
        # 切换到拍照作业页面
        self.current_stage = 'photo_homework'
        self.content_stack.setCurrentWidget(self.photo_homework_page)
        
    def on_photo_captured(self):
        """拍照完成"""
        logger.info("拍照完成")
        
        # 更新流程状态 - 根据模式调整步骤编号
        if self.current_mode == 'school':
            # 学校模式：拍照是第2步，AI分析是第3步
            self.todo_flow_panel.set_step_completed(2)
            self.todo_flow_panel.set_step_current(3)
        else:
            # 家庭模式：拍照是第1步，AI分析是第2步
            self.todo_flow_panel.set_step_completed(1)
            self.todo_flow_panel.set_step_current(2)
        
        self.todo_flow_panel.update_status("拍照完成，正在进行AI分析...")
        
        # 闪烁效果
        if self.photo_camera_widget:
            self.photo_camera_widget.flash_capture()
        
    def on_upload_ready(self):
        """准备上传"""
        logger.info("准备上传")
        self.todo_flow_panel.update_status("准备上传数据...")
        
    def on_analysis_started(self):
        """分析开始"""
        logger.info("分析开始")
        
        # 确保AI分析步骤被正确标记为当前步骤
        if self.current_mode == 'school':
            # 学校模式：确保第3步（AI分析）为当前步骤
            if self.todo_flow_panel:
                self.todo_flow_panel.set_step_current(3)
        else:
            # 家庭模式：确保第2步（AI分析）为当前步骤
            if self.todo_flow_panel:
                self.todo_flow_panel.set_step_current(2)
        
        # 更新状态显示
        if self.todo_flow_panel:
            self.todo_flow_panel.update_status("正在进行AI分析，请稍候...")
        
    def get_photo_camera(self):
        """获取拍照摄像头"""
        return self.photo_camera_widget.camera if self.photo_camera_widget else None
        
    def cleanup(self):
        """清理资源"""
        if self.face_camera_widget:
            self.face_camera_widget.stop_preview()
        if self.photo_camera_widget:
            self.photo_camera_widget.stop_preview()
        
    def on_face_recognition_failed(self):
        """人脸识别失败"""
        logger.warning("人脸识别失败")
        self.todo_flow_panel.update_status("人脸识别失败，请重试", "#e74c3c")
        
        # 重置第一步状态
        self.todo_flow_panel.reset_all_steps()
        self.todo_flow_panel.set_step_current(1)
        
        # 在5秒后重置为学校模式
        QTimer.singleShot(5000, self._restart_school_mode)
        
    def _restart_school_mode(self):
        """重新启动学校模式"""
        logger.info("重新启动学校模式")
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("正在重新进行人脸识别...")
        
        # 切换回人脸识别页面
        self.current_stage = 'face_recognition'
        self.content_stack.setCurrentWidget(self.face_recognition_page)
        
    def on_analysis_completed(self, result_data: dict):
        """分析完成"""
        logger.info("分析完成")
        
        # 更新流程状态 - 根据模式调整步骤编号
        if self.current_mode == 'school':
            # 学校模式：AI分析是第3步，结果展示是第4步
            self.todo_flow_panel.set_step_completed(3)
            self.todo_flow_panel.set_step_current(4)
        else:
            # 家庭模式：AI分析是第2步，结果展示是第3步
            self.todo_flow_panel.set_step_completed(2)
            self.todo_flow_panel.set_step_current(3)
        
        self.todo_flow_panel.update_status("分析完成，正在展示结果...")
        
        # 短暂显示完成状态后重置
        QTimer.singleShot(2000, self._complete_process)
        
    def _complete_process(self):
        """完成流程"""
        # 根据模式完成最后一步
        if self.current_mode == 'school':
            self.todo_flow_panel.set_step_completed(4)
        else:
            self.todo_flow_panel.set_step_completed(3)
        
        self.todo_flow_panel.update_status("作业批改完成！按6-0-2返回功能选择")
        
        # 5秒后重置所有步骤
        QTimer.singleShot(5000, self._reset_process)
        
    def _reset_process(self):
        """重置流程"""
        self.todo_flow_panel.reset_all_steps()
        self.todo_flow_panel.update_status("准备就绪")
        
    def on_result_display_closed(self):
        """结果显示关闭"""
        logger.info("结果显示关闭")
        self._reset_process()
        
    def handle_control_command(self, action: str):
        """处理控制命令"""
        logger.info(f"作业批改页面收到控制指令: {action}")
        
        if action == "back":
            logger.info("执行返回操作")
            self.back_requested.emit()
        else:
            logger.warning(f"未处理的控制指令: {action}")