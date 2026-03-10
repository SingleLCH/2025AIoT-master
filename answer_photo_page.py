# -*- coding: utf-8 -*-
"""
作业问答拍照页面
使用实时预览界面，类似拍照搜题功能
"""

import os
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from camera_handler import CameraHandler
from embedded_camera_widget import EmbeddedCameraWidget

logger = logging.getLogger(__name__)


class AnswerPhotoHandler(QThread):
    """作业问答拍照处理器"""

    # 信号定义
    photo_captured = pyqtSignal(bool)  # 拍照完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    camera_ready = pyqtSignal(object)  # 摄像头准备就绪信号

    def __init__(self):
        super().__init__()
        self.photo_folder = "answer_photos"  # 作业问答照片保存文件夹
        self.camera_handler = None
        self.is_processing = False

        # 确保照片文件夹存在
        self._ensure_photo_folder()

    def _ensure_photo_folder(self):
        """确保照片文件夹存在"""
        if not os.path.exists(self.photo_folder):
            os.makedirs(self.photo_folder)
            logger.info(f"创建照片文件夹: {self.photo_folder}")

    def init_camera(self):
        """初始化摄像头"""
        try:
            if not self.camera_handler:
                logger.info("初始化作业问答摄像头处理器...")
                self.camera_handler = CameraHandler()
                # 设置照片保存文件夹
                self.camera_handler.photo_folder = self.photo_folder

                # 连接信号
                self.camera_handler.photo_captured.connect(self.photo_captured.emit)
                self.camera_handler.error_occurred.connect(self.error_occurred.emit)

                logger.info(f"作业问答摄像头处理器初始化成功，照片保存到: {self.photo_folder}")

                # 获取拍照摄像头并发送准备信号
                photo_camera = self.camera_handler.get_photo_camera()
                self.camera_ready.emit(photo_camera)
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
            logger.info("开始作业问答拍照...")
            self.is_processing = True
            success = self.camera_handler.capture_photos_for_homework(photo_count=1)
            logger.info(f"作业问答拍照结果: {success}")
        except Exception as e:
            error_msg = f"拍照过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self.is_processing = False

    def stop(self):
        """停止处理器并释放摄像头资源"""
        try:
            self.is_processing = False

            if self.camera_handler:
                logger.info("关闭作业问答摄像头处理器...")
                self.camera_handler.close_cameras()
                self.camera_handler = None
                logger.info("作业问答摄像头处理器已释放")

            logger.info("作业问答拍照处理器已停止")

        except Exception as e:
            logger.error(f"停止处理器失败: {e}")


class AnswerPhotoPage(QWidget):
    """作业问答拍照页面 - 实时预览界面"""

    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    photo_captured = pyqtSignal()  # 拍照完成信号
    upload_completed = pyqtSignal(dict)  # 上传完成信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_handler = None
        self.camera_widget = None

        self.setup_ui()
        self.init_photo_handler()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 主标题
        title_label = QLabel("作业问答 - 拍照提问")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("微软雅黑", 24, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 15px;
                border-left: 6px solid #9b59b6;
            }
        """)
        layout.addWidget(title_label)

        # 摄像头预览区域
        self.camera_widget = EmbeddedCameraWidget(
            title="拍照摄像头",
            preview_size=(720, 540)
        )
        layout.addWidget(self.camera_widget)

        # 操作提示
        hint_label = QLabel("操作提示：6-0-1 拍照 | 6-0-2 返回主菜单")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setFont(QFont("微软雅黑", 14))
        hint_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)
        layout.addWidget(hint_label)

        # 状态显示
        self.status_label = QLabel("摄像头准备中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("微软雅黑", 12))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #495057;
                padding: 10px;
                background-color: #e9ecef;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
    
    def init_photo_handler(self):
        """初始化拍照处理器"""
        try:
            self.photo_handler = AnswerPhotoHandler()

            # 连接信号
            self.photo_handler.photo_captured.connect(self.on_photo_captured)
            self.photo_handler.error_occurred.connect(self.on_error_occurred)
            self.photo_handler.camera_ready.connect(self.on_camera_ready)

            # 初始化摄像头
            self.photo_handler.init_camera()

        except Exception as e:
            logger.error(f"初始化拍照处理器失败: {e}")
            self.status_label.setText(f"初始化失败: {e}")

    def on_camera_ready(self, camera):
        """摄像头准备就绪"""
        if self.camera_widget and camera:
            self.camera_widget.set_camera(camera)
            self.status_label.setText("摄像头已就绪，可以开始拍照")
        else:
            self.status_label.setText("摄像头初始化失败")

    def on_photo_captured(self, success: bool):
        """拍照完成"""
        if success:
            self.status_label.setText("拍照成功！照片已保存到 answer_photos 文件夹")
            self.photo_captured.emit()
        else:
            self.status_label.setText("拍照失败，请重试")

    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.status_label.setText(f"错误: {error_msg}")
        logger.error(error_msg)
    
    def capture_photo(self):
        """拍照"""
        if self.photo_handler:
            self.photo_handler.capture_photo()

    def handle_control_command(self, action: str):
        """处理MQTT控制指令"""
        logger.info(f"作业问答页面接收到控制指令: {action}")

        if action == 'confirm':  # 6-0-1 拍照
            self.capture_photo()
        elif action == 'back':  # 6-0-2 返回主菜单
            self.back_requested.emit()

    def cleanup(self):
        """清理资源"""
        if self.camera_widget:
            self.camera_widget.stop_preview()

        if self.photo_handler:
            self.photo_handler.stop()
            self.photo_handler = None

        logger.info("作业问答页面资源已清理")
