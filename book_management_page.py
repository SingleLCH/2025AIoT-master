# -*- coding: utf-8 -*-
"""
图书管理页面
用于学校模式下的图书借阅登记功能
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QStackedWidget, QPushButton, QFrame, QGridLayout,
                           QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap

from embedded_camera_widget import EmbeddedCameraWidget as CameraWidget
from todo_step_components import TodoFlowPanel

logger = logging.getLogger(__name__)


class BookManagementPage(QWidget):
    """图书管理页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    process_started = pyqtSignal(str)  # 流程开始信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状态变量
        self.current_stage = None  # 当前阶段
        self.title_label = None
        self.content_stack = None
        self.todo_flow_panel = None
        self.todo_panel_container = None
        
        # 🔧 复用作业批改逻辑：保存拍照摄像头引用
        self._photo_camera = None
        
        # 摄像头组件
        self.face_camera_widget = None
        self.photo_camera_widget = None
        
        # 页面组件
        self.face_recognition_page = None
        self.photo_book_page = None
        self.result_page = None
        
        # 结果显示
        self.student_name_label = None
        self.book_name_label = None
        self.result_info_label = None
        
        self.init_ui()
        logger.info("图书管理页面初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧流程面板
        self.create_todo_panel(content_layout)
        
        # 右侧主要内容
        self.create_main_content(content_layout)
        
        main_layout.addLayout(content_layout)
        
        # 创建底部操作区
        self.create_bottom_bar(main_layout)
    
    def create_header(self, layout):
        """创建头部"""
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                           stop:0 #2196F3, stop:1 #1976D2);
                border-radius: 10px;
                margin-bottom: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 15, 30, 15)
        
        # 标题
        self.title_label = QLabel("智能图书管理系统")
        self.title_label.setStyleSheet("""
            color: white;
            font-size: 24px;
            font-weight: bold;
            background: transparent;
        """)
        header_layout.addWidget(self.title_label)
        
        # 占位符，保持布局平衡
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
    
    def create_todo_panel(self, layout):
        """创建左侧流程面板"""
        self.todo_panel_container = QWidget()
        self.todo_panel_container.setFixedWidth(400)#白色框的区域部分
        self.todo_panel_container.setStyleSheet("""
            QWidget {
                background-color: #3B4252;
                border-radius: 10px;
                border: 1px solid #e9ecef;
            }
        """)
        
        layout.addWidget(self.todo_panel_container)
    
    def create_main_content(self, layout):
        """创建主要内容区域"""
        # 创建堆栈窗口
        self.content_stack = QStackedWidget()
        self.content_stack.setMaximumWidth(1200)  # 限制最大宽度，避免遮挡流程面板
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # 创建各个页面
        self.create_face_recognition_page()
        self.create_photo_book_page()
        self.create_result_page()
        
        layout.addWidget(self.content_stack)
    
    def create_face_recognition_page(self):
        """创建人脸识别页面"""
        self.face_recognition_page = QWidget()
        layout = QVBoxLayout(self.face_recognition_page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("学生身份识别")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 20px;
        """)
        layout.addWidget(title_label)
        
        # 🔧 复用作业批改逻辑：摄像头预览使用人脸识别专用裁剪模式
        self.face_camera_widget = CameraWidget(
            title="人脸识别摄像头",
            preview_size=(640, 480),
            clip_mode=3  # 使用人脸识别专用裁剪模式，确保预览画面与分析画面一致
        )
        self.face_camera_widget.setFixedSize(640, 480)
        self.face_camera_widget.setStyleSheet("""
            border: 2px solid #e9ecef;
            border-radius: 10px;
        """)
        layout.addWidget(self.face_camera_widget, alignment=Qt.AlignCenter)
        
        # 🔧 复用作业批改逻辑：更新提示信息，指导用户正确定位
        hint_label = QLabel("请将面部对准摄像头中心区域进行身份识别")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("""
            font-size: 16px;
            color: #666;
            margin-top: 20px;
        """)
        layout.addWidget(hint_label)
        
        self.content_stack.addWidget(self.face_recognition_page)
    
    def create_photo_book_page(self):
        """创建图书拍照页面"""
        self.photo_book_page = QWidget()
        layout = QVBoxLayout(self.photo_book_page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("图书信息采集")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 20px;
        """)
        layout.addWidget(title_label)
        
        # 摄像头预览
        self.photo_camera_widget = CameraWidget()
        self.photo_camera_widget.setFixedSize(640, 480)
        self.photo_camera_widget.setStyleSheet("""
            border: 2px solid #e9ecef;
            border-radius: 10px;
        """)
        layout.addWidget(self.photo_camera_widget, alignment=Qt.AlignCenter)
        
        # 提示信息
        hint_label = QLabel("请将图书封面或内页对准摄像头进行拍照")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("""
            font-size: 16px;
            color: #666;
            margin-top: 20px;
        """)
        layout.addWidget(hint_label)
        
        self.content_stack.addWidget(self.photo_book_page)
    
    def create_result_page(self):
        """创建结果展示页面"""
        self.result_page = QWidget()
        layout = QVBoxLayout(self.result_page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # 标题
        title_label = QLabel("图书登记完成")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
            margin-bottom: 30px;
        """)
        layout.addWidget(title_label)
        
        # 结果信息面板
        result_frame = QFrame()
        result_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 15px;
                border: 1px solid #e9ecef;
                padding: 30px;
            }
        """)
        
        result_layout = QVBoxLayout(result_frame)
        result_layout.setSpacing(20)
        
        # 学生信息
        student_layout = QHBoxLayout()
        student_icon_label = QLabel("👤")
        student_icon_label.setStyleSheet("font-size: 24px;")
        student_text_label = QLabel("借阅学生：")
        student_text_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.student_name_label = QLabel("未识别")
        self.student_name_label.setStyleSheet("font-size: 18px; color: #2196F3;")
        
        student_layout.addWidget(student_icon_label)
        student_layout.addWidget(student_text_label)
        student_layout.addWidget(self.student_name_label)
        student_layout.addStretch()
        result_layout.addLayout(student_layout)
        
        # 图书信息
        book_layout = QHBoxLayout()
        book_icon_label = QLabel("📚")
        book_icon_label.setStyleSheet("font-size: 24px;")
        book_text_label = QLabel("图书名称：")
        book_text_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.book_name_label = QLabel("未识别")
        self.book_name_label.setStyleSheet("font-size: 18px; color: #FF9800;")
        
        book_layout.addWidget(book_icon_label)
        book_layout.addWidget(book_text_label)
        book_layout.addWidget(self.book_name_label)
        book_layout.addStretch()
        result_layout.addLayout(book_layout)
        
        # 状态信息
        self.result_info_label = QLabel("登记成功！")
        self.result_info_label.setAlignment(Qt.AlignCenter)
        self.result_info_label.setStyleSheet("""
            font-size: 16px;
            color: #4CAF50;
            background-color: #e8f5e8;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        """)
        result_layout.addWidget(self.result_info_label)
        
        layout.addWidget(result_frame)
        
        # 添加返回按钮
        return_btn = QPushButton("继续登记")
        return_btn.setFixedSize(150, 50)
        return_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        return_btn.clicked.connect(self.restart_process)
        layout.addWidget(return_btn, alignment=Qt.AlignCenter)
        
        self.content_stack.addWidget(self.result_page)
    
    def create_bottom_bar(self, layout):
        """创建底部操作栏"""
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(60)
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #e9ecef;
            }
        """)
        
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        # 状态提示
        status_label = QLabel("使用手势或语音指令进行操作")
        status_label.setStyleSheet("""
            color: #666;
            font-size: 14px;
        """)
        bottom_layout.addWidget(status_label)
        
        bottom_layout.addStretch()
        
        # 指令提示
        hint_label = QLabel("6-0-1: 拍照 | 6-0-2: 返回")
        hint_label.setStyleSheet("""
            color: #999;
            font-size: 12px;
            font-family: monospace;
        """)
        bottom_layout.addWidget(hint_label)
        
        layout.addWidget(bottom_frame)
    
    def start_book_management_mode(self, face_camera, photo_camera):
        """开始图书管理模式"""
        
        # 创建流程步骤
        if not self.todo_flow_panel:
            steps_data = [
                (1, "第一步：身份识别", "识别借阅学生身份"),
                (2, "第二步：图书拍照", "拍摄图书封面或内页"),
                (3, "第三步：智能识别", "AI识别图书信息"),
                (4, "第四步：完成登记", "保存借阅记录")
            ]
            self.todo_flow_panel = TodoFlowPanel("图书管理流程", steps_data)
            container_layout = QVBoxLayout(self.todo_panel_container)
            container_layout.addWidget(self.todo_flow_panel)
        
        # 设置第一步为当前步骤
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("等待6-0-1指令开始身份识别")
        
        # 🔧 复用作业批改逻辑：初始化时只设置人脸识别摄像头
        if self.face_camera_widget:
            logger.info(f"设置人脸识别摄像头: {face_camera}")
            self.face_camera_widget.set_camera(face_camera)
            if face_camera == "SIMULATED_CAMERA" or (face_camera and hasattr(face_camera, 'isOpened') and face_camera.isOpened()):
                self.face_camera_widget.start_preview()
                logger.info("人脸识别摄像头预览已启动")
        
        # 🔧 复用作业批改逻辑：保存拍照摄像头对象，但暂不设置（避免状态冲突）
        self._photo_camera = photo_camera
        
        # 切换到人脸识别页面
        self.current_stage = 'face_recognition'
        self.content_stack.setCurrentWidget(self.face_recognition_page)
        
        logger.info("图书管理模式开始")
        self.process_started.emit('book_management')
    
    def on_face_recognition_completed(self, student_info: dict):
        """人脸识别完成"""
        logger.info(f"人脸识别完成: {student_info}")
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(1)
        self.todo_flow_panel.set_step_current(2)
        
        # 获取学生姓名并显示个性化提示
        student_name = student_info.get('name', '同学')
        self.todo_flow_panel.update_status(f"{student_name}同学，请使用6-0-1拍摄图书")
        
        # 🔧 复用作业批改逻辑：人脸识别完成后才设置并启动拍照摄像头预览
        if self.photo_camera_widget and hasattr(self, '_photo_camera'):
            logger.info(f"设置图书拍照摄像头: {self._photo_camera}")
            self.photo_camera_widget.set_camera(self._photo_camera)
            # 强制启动预览
            if self._photo_camera == "SIMULATED_CAMERA" or (self._photo_camera and hasattr(self._photo_camera, 'isOpened') and self._photo_camera.isOpened()):
                self.photo_camera_widget.start_preview()
                logger.info("图书拍照摄像头预览已启动")
            else:
                logger.warning(f"图书拍照摄像头未就绪: {self._photo_camera}")
        
        # 切换到图书拍照页面
        self.current_stage = 'photo_book'
        self.content_stack.setCurrentWidget(self.photo_book_page)
    
    def on_photo_captured(self):
        """拍照完成"""
        logger.info("图书拍照完成")
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(2)
        self.todo_flow_panel.set_step_current(3)
        self.todo_flow_panel.update_status("正在识别图书信息...")
    
    def on_analysis_started(self):
        """AI分析开始"""
        logger.info("图书识别分析开始")
        self.todo_flow_panel.update_status("正在识别图书信息...")
    
    def on_analysis_progress(self, progress_msg: str):
        """AI分析进度更新"""
        self.todo_flow_panel.update_status(progress_msg)
    
    def on_analysis_completed(self, book_name: str):
        """AI分析完成"""
        logger.info(f"图书识别完成: {book_name}")
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(3)
        self.todo_flow_panel.set_step_current(4)
        self.todo_flow_panel.update_status("正在保存登记信息...")
    
    def on_upload_completed(self, result: dict):
        """上传完成，显示结果"""
        logger.info(f"图书登记完成: {result}")
        
        # 更新流程状态
        self.todo_flow_panel.set_step_completed(4)
        self.todo_flow_panel.update_status("图书登记完成！")
        
        # 更新结果显示
        self.student_name_label.setText(result.get('student_name', '未知'))
        self.book_name_label.setText(result.get('book_name', '未识别'))
        self.result_info_label.setText("📚 图书登记成功！记录已保存到数据库")
        
        # 切换到结果页面
        self.current_stage = 'result'
        self.content_stack.setCurrentWidget(self.result_page)
        
        # 停止摄像头预览
        if self.photo_camera_widget:
            self.photo_camera_widget.stop_preview()
    
    def on_error_occurred(self, error_msg: str):
        """处理错误"""
        logger.error(f"图书管理流程错误: {error_msg}")
        self.todo_flow_panel.update_status(f"错误: {error_msg}")
        
        # 显示错误信息
        self.result_info_label.setText(f"❌ 操作失败: {error_msg}")
        self.result_info_label.setStyleSheet("""
            font-size: 16px;
            color: #f44336;
            background-color: #ffebee;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        """)
    
    def restart_process(self):
        """重新开始流程"""
        logger.info("重新开始图书管理流程")
        # 重置流程状态
        self.todo_flow_panel.reset_all_steps()
        self.todo_flow_panel.set_step_current(1)
        self.todo_flow_panel.update_status("等待6-0-1指令开始身份识别")
        
        # 重置结果显示
        self.student_name_label.setText("未识别")
        self.book_name_label.setText("未识别")
        self.result_info_label.setText("等待登记...")
        self.result_info_label.setStyleSheet("""
            font-size: 16px;
            color: #4CAF50;
            background-color: #e8f5e8;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        """)
        
        # 🔧 复用作业批改逻辑：停止拍照摄像头预览，重新启动人脸识别摄像头预览
        if self.photo_camera_widget:
            self.photo_camera_widget.stop_preview()
        
        if self.face_camera_widget:
            self.face_camera_widget.start_preview()
        
        # 切换到人脸识别页面
        self.current_stage = 'face_recognition'
        self.content_stack.setCurrentWidget(self.face_recognition_page)
        
        # 发出重新开始信号
        self.process_started.emit('book_management')
    
    def on_face_recognition_started(self):
        """人脸识别开始"""
        logger.info("人脸识别开始")
        self.todo_flow_panel.update_status("正在进行身份识别...")
    
    def on_back_clicked(self):
        """返回按钮点击"""
        logger.info("返回功能选择页面")
        # 停止所有摄像头预览
        if self.face_camera_widget:
            self.face_camera_widget.stop_preview()
        if self.photo_camera_widget:
            self.photo_camera_widget.stop_preview()
        
        self.back_requested.emit()
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理图书管理页面资源")
        if self.face_camera_widget:
            self.face_camera_widget.stop_preview()
        if self.photo_camera_widget:
            self.photo_camera_widget.stop_preview() 