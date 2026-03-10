# -*- coding: utf-8 -*-
"""
通用拍照处理器
可复用的拍照组件，支持不同的照片保存目录
"""

import os
import time
import logging
import cv2
from typing import Optional, List
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from camera_handler import CameraHandler
from embedded_camera_widget import EmbeddedCameraWidget
from config import CAMERA_CONFIG

logger = logging.getLogger(__name__)


class CommonPhotoHandler(QThread):
    """通用拍照处理器"""
    
    # 信号定义
    photo_captured = pyqtSignal(str)  # 拍照完成信号，传递照片路径
    error_occurred = pyqtSignal(str)  # 错误信号
    process_completed = pyqtSignal(list)  # 处理完成信号，传递所有照片路径
    
    def __init__(self, photo_folder: str = "photos", parent=None):
        super().__init__(parent)
        self.photo_folder = photo_folder
        self.camera_handler = None
        self.photo_paths = []  # 存储拍摄的照片路径
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
                logger.info("初始化摄像头处理器...")
                self.camera_handler = CameraHandler()
                # 设置照片保存文件夹
                self.camera_handler.photo_folder = self.photo_folder
                logger.info(f"摄像头处理器初始化成功，照片保存到: {self.photo_folder}")
                return True
        except Exception as e:
            error_msg = f"初始化摄像头失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def get_photo_camera(self):
        """获取拍照摄像头"""
        if self.camera_handler:
            return self.camera_handler.get_photo_camera()
        return None
    
    def capture_photo(self) -> bool:
        """拍摄单张照片"""
        if not self.camera_handler:
            error_msg = "摄像头处理器未初始化"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        try:
            logger.info("开始拍照...")
            self.is_processing = True
            
            # 使用摄像头处理器拍照
            success = self.camera_handler.capture_photos_for_homework(photo_count=1)
            
            if success:
                # 获取最新拍摄的照片路径
                photo_paths = self.camera_handler.get_latest_photo_paths()
                if photo_paths:
                    photo_path = photo_paths[0]
                    self.photo_paths.append(photo_path)
                    logger.info(f"拍照成功: {photo_path}")
                    self.photo_captured.emit(photo_path)
                    return True
                else:
                    error_msg = "拍照成功但无法获取照片路径"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    return False
            else:
                error_msg = "拍照失败"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"拍照过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        finally:
            self.is_processing = False
    
    def get_all_photos(self) -> List[str]:
        """获取所有拍摄的照片路径"""
        return self.photo_paths.copy()
    
    def clear_photos(self):
        """清空照片记录"""
        self.photo_paths.clear()
        logger.info("已清空照片记录")
    
    def complete_process(self):
        """完成拍照流程"""
        logger.info(f"拍照流程完成，共拍摄 {len(self.photo_paths)} 张照片")
        self.process_completed.emit(self.photo_paths.copy())
    
    def stop(self):
        """停止处理器"""
        try:
            self.is_processing = False
            
            if self.camera_handler:
                self.camera_handler.close_cameras()
                self.camera_handler = None
                logger.info("摄像头处理器已释放")
            
            logger.info("通用拍照处理器已停止")
            
        except Exception as e:
            logger.error(f"停止处理器失败: {e}")


class CommonPhotoPage(QWidget):
    """通用拍照页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    photo_captured = pyqtSignal(str)  # 拍照完成信号
    process_completed = pyqtSignal(list)  # 流程完成信号
    
    def __init__(self, title: str = "拍照页面", photo_folder: str = "photos", parent=None):
        super().__init__(parent)
        self.title = title
        self.photo_folder = photo_folder
        self.photo_handler = None
        self.camera_widget = None
        
        self.setup_ui()
        self.init_photo_handler()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("微软雅黑", 24, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 15px;
                border-left: 6px solid #3498db;
            }
        """)
        layout.addWidget(title_label)
        
        # 摄像头预览
        self.camera_widget = EmbeddedCameraWidget(
            title="拍照摄像头", 
            preview_size=(720, 540)
        )
        layout.addWidget(self.camera_widget)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("拍照 (6-0-1)")
        self.capture_btn.setFont(QFont("微软雅黑", 14, QFont.Bold))
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        self.capture_btn.clicked.connect(self.capture_photo)
        button_layout.addWidget(self.capture_btn)
        
        self.complete_btn = QPushButton("完成 (6-0-3)")
        self.complete_btn.setFont(QFont("微软雅黑", 14, QFont.Bold))
        self.complete_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """)
        self.complete_btn.clicked.connect(self.complete_process)
        button_layout.addWidget(self.complete_btn)
        
        self.back_btn = QPushButton("返回 (6-0-2)")
        self.back_btn.setFont(QFont("微软雅黑", 14, QFont.Bold))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #ec7063;
            }
            QPushButton:pressed {
                background-color: #c0392b;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(self.back_btn)
        
        layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QLabel("准备就绪，请开始拍照")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("微软雅黑", 12))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def init_photo_handler(self):
        """初始化拍照处理器"""
        try:
            self.photo_handler = CommonPhotoHandler(photo_folder=self.photo_folder)
            
            # 连接信号
            self.photo_handler.photo_captured.connect(self.on_photo_captured)
            self.photo_handler.error_occurred.connect(self.on_error_occurred)
            self.photo_handler.process_completed.connect(self.on_process_completed)
            
            # 初始化摄像头
            if self.photo_handler.init_camera():
                photo_camera = self.photo_handler.get_photo_camera()
                if photo_camera:
                    self.camera_widget.set_camera(photo_camera)
                    self.status_label.setText("摄像头已就绪，可以开始拍照")
                else:
                    self.status_label.setText("摄像头初始化失败")
            else:
                self.status_label.setText("摄像头初始化失败")
                
        except Exception as e:
            logger.error(f"初始化拍照处理器失败: {e}")
            self.status_label.setText(f"初始化失败: {e}")
    
    def capture_photo(self):
        """拍照"""
        if self.photo_handler:
            self.status_label.setText("正在拍照...")
            self.capture_btn.setEnabled(False)
            self.photo_handler.capture_photo()
    
    def complete_process(self):
        """完成流程"""
        if self.photo_handler:
            self.photo_handler.complete_process()
    
    def on_photo_captured(self, photo_path: str):
        """拍照完成"""
        self.capture_btn.setEnabled(True)
        photo_count = len(self.photo_handler.get_all_photos())
        self.status_label.setText(f"拍照成功！已拍摄 {photo_count} 张照片")
        self.photo_captured.emit(photo_path)
    
    def on_error_occurred(self, error_msg: str):
        """错误处理"""
        self.capture_btn.setEnabled(True)
        self.status_label.setText(f"错误: {error_msg}")
        logger.error(error_msg)
    
    def on_process_completed(self, photo_paths: List[str]):
        """流程完成"""
        self.status_label.setText(f"流程完成！共拍摄 {len(photo_paths)} 张照片")
        self.process_completed.emit(photo_paths)
    
    def handle_control_command(self, action: str):
        """处理MQTT控制指令"""
        if action == 'confirm':
            self.capture_photo()
        elif action == 'next':
            self.complete_process()
        elif action == 'back':
            self.back_requested.emit()
    
    def cleanup(self):
        """清理资源"""
        if self.camera_widget:
            self.camera_widget.stop_preview()
        
        if self.photo_handler:
            self.photo_handler.stop()
            self.photo_handler = None
        
        logger.info("通用拍照页面资源已清理")
