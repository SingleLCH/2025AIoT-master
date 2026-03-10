# -*- coding: utf-8 -*-
"""
嵌入式摄像头预览组件
用于在主界面中显示摄像头画面
"""

import cv2
import time
import logging
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import Qt

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddedCameraWidget(QWidget):
    """嵌入式摄像头预览组件"""
    
    # 信号定义
    capture_requested = pyqtSignal()  # 请求拍照信号
    
    def __init__(self, title: str = "摄像头预览", preview_size: tuple = (640, 480), clip_mode: int = 0, parent = None):
        super().__init__(parent)
        self.title = title
        self.preview_width, self.preview_height = preview_size
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.clip_mode = clip_mode

        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 摄像头预览区域 - 居中显示
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.preview_width, self.preview_height)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid #88C0D0;
                border-radius: 10px;
                background-color: #2E3440;
                color: #ECEFF4;
                font-size: 16px;
            }
        """)
        self.video_label.setText("摄像头准备中...")
        
        # 居中显示摄像头预览
        video_layout = QHBoxLayout()
        video_layout.addStretch()
        video_layout.addWidget(self.video_label)
        video_layout.addStretch()
        layout.addLayout(video_layout)
        
        self.setLayout(layout)
        
    def set_camera(self, camera):
        """设置摄像头（增强版）"""
        logger.info(f"设置摄像头: {camera}")
        
        # 先停止当前预览
        if self.timer.isActive():
            self.stop_preview()
        
        self.camera = camera
        
        if camera == "SIMULATED_CAMERA":
            logger.info("使用模拟摄像头模式")
            self.start_preview()
        elif camera and hasattr(camera, 'isOpened') and camera.isOpened():
            logger.info("使用真实摄像头")
            self.start_preview()
        else:
            logger.warning(f"摄像头未就绪: {camera}")
            self.video_label.setText("摄像头准备中...")
            
    def start_preview(self):
        """开始预览（增强版）"""
        if self.camera == "SIMULATED_CAMERA":
            logger.info(f"启动模拟摄像头预览: {self.title}")
            self.timer.start(33)  # 约30fps
            return
            
        if self.camera and hasattr(self.camera, 'isOpened') and self.camera.isOpened():
            logger.info(f"启动真实摄像头预览: {self.title}")
            self.timer.start(33)  # 约30fps
        else:
            logger.error(f"无法启动预览，摄像头状态异常: {self.camera}")
            self.video_label.setText("摄像头无法启动")
            
    def stop_preview(self):
        """停止预览"""
        self.timer.stop()
        self.video_label.clear()
        self.video_label.setText("预览已停止")
        logger.info(f"停止预览: {self.title}")
        
    def update_frame(self):
        """更新帧"""
        if self.camera == "SIMULATED_CAMERA":
            # 模拟摄像头模式，显示静态图像
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # 添加渐变背景
            for i in range(480):
                frame[i, :] = [50 + i//3, 80 + i//4, 120 + i//5]
            
            # 转换为RGB格式
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # 创建QImage
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 缩放到预览窗口大小，保持宽高比
            scaled_image = qt_image.scaled(
                self.preview_width, 
                self.preview_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 显示图像
            self.video_label.setPixmap(QPixmap.fromImage(scaled_image))
            
        elif self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if self.clip_mode == 1:  # 指尖识词
                if frame is not None:
                    height, width = frame.shape[:2]
                    
                    # 计算九宫格每格的尺寸
                    grid_height = height // 3
                    grid_width = width // 3
                    
                    # 提取中心格（第2行第2列，索引为1,1）
                    center_y = grid_height
                    center_x = grid_width
                    
                    # 切片获取中心区域
                    frame = frame[center_y:center_y + grid_height, 
                                center_x:center_x + grid_width]
                    
                    # logger.info(f"提取九宫格中心区域，新尺寸: {frame.shape[1]}x{frame.shape[0]}")
            elif self.clip_mode == 2:  # 作业批改
                if frame is not None:
                    height, width = frame.shape[:2]
                    
                    # 计算九宫格每格的尺寸
                    grid_height = height
                    grid_width = width // 3
                    # 提取中心格（第2行第2列，索引为1,1）
                    center_y = grid_height
                    center_x = grid_width
                    
                    # 切片获取中心区域
                    frame = frame[:, 
                                center_x:center_x + grid_width]
                    
                    # logger.info(f"提取九宫格中心区域，新尺寸: {frame.shape[1]}x{frame.shape[0]}")
            elif self.clip_mode == 3:  # 人脸识别
                if frame is not None:
                    height, width = frame.shape[:2]
                    # print(f"原始帧尺寸: {width}x{height}")
                    # 计算九宫格每格的尺寸
                    grid_height = height * 4 // 10
                    grid_width = width // 5
                    # print(f"九宫格尺寸: {grid_width}x{grid_height}")
                    
                    # 提取中心格（第2行第2列，索引为1,1）
                    center_y = (height - grid_height)//2 - height//4
                    center_x = (width - grid_width)//2
                    # print(f"中心区域位置: {center_x}, {center_y}")
                    
                    # 切片获取中心区域
                    frame = frame[center_y:center_y + grid_height, 
                                center_x:center_x + grid_width]
                    # print(f"提取九宫格中心区域，位置: {center_x}-{center_x + grid_width}, {center_y}-{center_y + grid_height}, 新尺寸: {frame.shape[1]}x{frame.shape[0]}")
                    # logger.info(f"提取九宫格中心区域，新尺寸: {frame.shape[1]}x{frame.shape[0]}")
            if ret:
                # 转换为RGB格式
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                # 创建QImage
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # 缩放到预览窗口大小，保持宽高比
                scaled_image = qt_image.scaled(
                    self.preview_width, 
                    self.preview_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                # 显示图像
                self.video_label.setPixmap(QPixmap.fromImage(scaled_image))
            else:
                # 读取失败，显示错误信息
                self.video_label.setText("摄像头连接中...")

                
    def set_hint_text(self, text: str):
        """设置提示文本（已移除提示标签）"""
        # 不再显示提示文本
        pass
        
    def flash_capture(self):
        """拍照闪烁效果"""
        # 简单的闪烁效果
        original_style = self.video_label.styleSheet()
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid #EBCB8B;
                border-radius: 10px;
                background-color: #EBCB8B;
            }
        """)
        
        # 200ms后恢复原样
        QTimer.singleShot(200, lambda: self.video_label.setStyleSheet(original_style))
        
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_preview()
        event.accept() 