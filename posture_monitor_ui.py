#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
姿势检测主界面
提供姿势检测的控制和显示功能
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFrame, QTextEdit, QGroupBox,
                            QGridLayout, QProgressBar, QCheckBox, QSpinBox,
                            QDoubleSpinBox, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtGui import QFont, QPixmap, QImage, QPalette, QColor
import cv2
import numpy as np
import config

from pose_detection_thread import PoseDetectionThread
import config

class PostureMonitorWidget(QWidget):
    """姿势监控主界面"""
    
    def __init__(self):
        super().__init__()
        
        # 检测线程
        self.detection_thread = None
        
        # 界面更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_interface)
        self.update_timer.start(100)  # 每秒更新一次界面
        
        # 警告状态
        self.last_alert_time = None
        
        self.setup_ui()
        self.init_detection_thread()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("智能姿势检测系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧显示面板
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel, 2)
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
    
    def create_control_panel(self):
        """创建控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        panel.setMaximumWidth(350)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("姿势检测控制面板")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; padding: 10px; background-color: white; border-radius: 5px;")
        layout.addWidget(title)
        
        # 控制按钮组
        control_group = QGroupBox("检测控制")
        control_layout = QVBoxLayout()
        
        # 按钮布局
        button_layout = QGridLayout()
        
        self.start_btn = QPushButton("🎯 开始检测")
        self.start_btn.clicked.connect(self.start_detection)
        self.start_btn.setStyleSheet("QPushButton { background-color: #27ae60; }")
        button_layout.addWidget(self.start_btn, 0, 0)
        
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.clicked.connect(self.pause_detection)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("QPushButton { background-color: #f39c12; }")
        button_layout.addWidget(self.pause_btn, 0, 1)
        
        self.stop_btn = QPushButton("⏹️ 停止检测")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #e74c3c; }")
        button_layout.addWidget(self.stop_btn, 1, 0)
        
        self.clear_btn = QPushButton("🗑️ 清除历史")
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.setStyleSheet("QPushButton { background-color: #95a5a6; }")
        button_layout.addWidget(self.clear_btn, 1, 1)
        
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 配置设置组
        settings_group = QGroupBox("检测设置")
        settings_layout = QVBoxLayout()
        
        # 检测间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("检测间隔:"))
        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setRange(1.0, 60.0)
        self.interval_spinbox.setSuffix(" 秒")
        self.interval_spinbox.setValue(config.POSE_DETECTION_CONFIG['detection_interval'])
        self.interval_spinbox.valueChanged.connect(self.update_detection_interval)
        interval_layout.addWidget(self.interval_spinbox)
        settings_layout.addLayout(interval_layout)
        
        # 警告阈值设置
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("警告阈值:"))
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(1, 10)
        self.threshold_spinbox.setSuffix(" 次")
        self.threshold_spinbox.setValue(config.POSE_DETECTION_CONFIG['consecutive_bad_posture_threshold'])
        self.threshold_spinbox.valueChanged.connect(self.update_alert_threshold)
        threshold_layout.addWidget(self.threshold_spinbox)
        settings_layout.addLayout(threshold_layout)
        
        # 近视风险阈值设置
        myopia_threshold_layout = QHBoxLayout()
        myopia_threshold_layout.addWidget(QLabel("近视风险阈值:"))
        self.myopia_threshold_spinbox = QSpinBox()
        self.myopia_threshold_spinbox.setRange(1, 10)
        self.myopia_threshold_spinbox.setSuffix(" 次")
        self.myopia_threshold_spinbox.setValue(config.POSE_DETECTION_CONFIG['consecutive_myopia_risk_threshold'])
        self.myopia_threshold_spinbox.valueChanged.connect(self.update_myopia_threshold)
        myopia_threshold_layout.addWidget(self.myopia_threshold_spinbox)
        settings_layout.addLayout(myopia_threshold_layout)
        
        # 检查框设置
        self.save_images_checkbox = QCheckBox("保存检测图片")
        self.save_images_checkbox.setChecked(config.POSE_DETECTION_CONFIG['save_detection_images'])
        self.save_images_checkbox.toggled.connect(self.toggle_save_images)
        settings_layout.addWidget(self.save_images_checkbox)
        
        self.alert_checkbox = QCheckBox("姿势警告提醒")
        self.alert_checkbox.setChecked(config.POSE_DETECTION_CONFIG['alert_on_bad_posture'])
        self.alert_checkbox.toggled.connect(self.toggle_alerts)
        settings_layout.addWidget(self.alert_checkbox)
        
        self.myopia_alert_checkbox = QCheckBox("近视风险提醒")
        self.myopia_alert_checkbox.setChecked(config.POSE_DETECTION_CONFIG['alert_on_myopia_risk'])
        self.myopia_alert_checkbox.toggled.connect(self.toggle_myopia_alerts)
        settings_layout.addWidget(self.myopia_alert_checkbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 状态信息组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
        status_layout.addWidget(self.status_label)
        
        self.detection_count_label = QLabel("检测次数: 0")
        status_layout.addWidget(self.detection_count_label)
        
        self.bad_posture_label = QLabel("不良姿势: 0 次 (0.0%)")
        status_layout.addWidget(self.bad_posture_label)
        
        self.myopia_risk_label = QLabel("近视风险: 0 次 (0.0%)")
        status_layout.addWidget(self.myopia_risk_label)
        
        self.consecutive_label = QLabel("连续不良: 0 次")
        status_layout.addWidget(self.consecutive_label)
        
        self.consecutive_myopia_label = QLabel("连续近视风险: 0 次")
        status_layout.addWidget(self.consecutive_myopia_label)
        
        # 姿势状态指示器
        posture_indicator_layout = QHBoxLayout()
        posture_indicator_layout.addWidget(QLabel("当前姿势:"))
        self.posture_indicator = QLabel("未知")
        self.posture_indicator.setStyleSheet("""
            padding: 5px 10px; 
            border-radius: 5px; 
            background-color: #95a5a6; 
            color: white; 
            font-weight: bold;
        """)
        posture_indicator_layout.addWidget(self.posture_indicator)
        status_layout.addLayout(posture_indicator_layout)
        
        # 近视风险状态指示器
        myopia_indicator_layout = QHBoxLayout()
        myopia_indicator_layout.addWidget(QLabel("近视风险:"))
        self.myopia_indicator = QLabel("未知")
        self.myopia_indicator.setStyleSheet("""
            padding: 5px 10px; 
            border-radius: 5px; 
            background-color: #95a5a6; 
            color: white; 
            font-weight: bold;
        """)
        myopia_indicator_layout.addWidget(self.myopia_indicator)
        status_layout.addLayout(myopia_indicator_layout)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 日志区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; font-family: 'Consolas', monospace;")
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_display_panel(self):
        """创建显示面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        
        layout = QVBoxLayout()
        
        # 最新照片显示组
        photo_group = QGroupBox("最新检测照片")
        photo_layout = QVBoxLayout()
        
        self.photo_label = QLabel("等待拍照...")
        self.photo_label.setMinimumSize(640, 480)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 2px solid #bdc3c7;
                background-color: #34495e;
                color: #ecf0f1;
                font-size: 18px;
                text-align: center;
                border-radius: 5px;
            }
        """)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setScaledContents(True)
        photo_layout.addWidget(self.photo_label)
        
        # 照片信息
        self.photo_info_label = QLabel("尚未开始检测")
        self.photo_info_label.setStyleSheet("color: #7f8c8d; padding: 5px; text-align: center;")
        self.photo_info_label.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(self.photo_info_label)
        
        photo_group.setLayout(photo_layout)
        layout.addWidget(photo_group)
        
        # 检测结果图片展示组
        result_group = QGroupBox("检测结果分析")
        result_layout = QVBoxLayout()
        
        # 检测结果图片
        self.result_image_label = QLabel("等待检测结果...")
        self.result_image_label.setMinimumSize(640, 480)
        self.result_image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #bdc3c7;
                background-color: #ecf0f1;
                color: #7f8c8d;
                text-align: center;
                border-radius: 3px;
            }
        """)
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setScaledContents(True)
        result_layout.addWidget(self.result_image_label)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 检测结果详情组（独立的文本显示区域）
        result_detail_group = QGroupBox("检测结果详情")
        result_detail_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(200)
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: white; border: 1px solid #bdc3c7; font-family: 'Microsoft YaHei', Arial, sans-serif;")
        result_detail_layout.addWidget(self.result_text)
        
        result_detail_group.setLayout(result_detail_layout)
        layout.addWidget(result_detail_group)
        
        panel.setLayout(layout)
        return panel
    
    def init_detection_thread(self):
        """初始化检测线程"""
        try:
            self.detection_thread = PoseDetectionThread()
            
            # 连接信号
            self.detection_thread.detection_completed.connect(self.on_detection_completed)
            self.detection_thread.posture_alert.connect(self.on_posture_alert)
            self.detection_thread.myopia_risk_alert.connect(self.on_myopia_risk_alert)
            self.detection_thread.error_occurred.connect(self.on_error_occurred)
            self.detection_thread.status_changed.connect(self.on_status_changed)
            self.detection_thread.latest_photo_ready.connect(self.on_latest_photo_ready)
            
            self.add_log("检测系统初始化完成")
            
        except Exception as e:
            self.add_log(f"初始化检测系统失败: {e}")
            QMessageBox.critical(self, "初始化失败", f"无法初始化姿势检测系统:\n{e}")
    
    def start_detection(self):
        """开始检测"""
        if self.detection_thread:
            self.detection_thread.start_detection()
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.add_log("开始姿势检测")
    
    def pause_detection(self):
        """暂停检测"""
        if self.detection_thread:
            if self.pause_btn.text() == "⏸️ 暂停":
                self.detection_thread.pause_detection()
                self.pause_btn.setText("▶️ 继续")
                self.add_log("暂停姿势检测")
            else:
                self.detection_thread.resume_detection()
                self.pause_btn.setText("⏸️ 暂停")
                self.add_log("恢复姿势检测")
    
    def stop_detection(self):
        """停止检测"""
        if self.detection_thread:
            self.detection_thread.stop_detection()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸️ 暂停")
            self.stop_btn.setEnabled(False)
            self.add_log("停止姿势检测")
    
    def clear_history(self):
        """清除历史"""
        if self.detection_thread:
            reply = QMessageBox.question(self, "确认清除", 
                                       "确定要清除所有检测历史吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.detection_thread.clear_detection_history()
                self.result_image_label.setText("等待检测结果...")
                self.result_text.clear()
                self.add_log("已清除检测历史")
    
    def update_detection_interval(self, value):
        """更新检测间隔"""
        config.POSE_DETECTION_CONFIG['detection_interval'] = value
        self.add_log(f"检测间隔设置为 {value} 秒")
    
    def update_alert_threshold(self, value):
        """更新警告阈值"""
        config.POSE_DETECTION_CONFIG['consecutive_bad_posture_threshold'] = value
        self.add_log(f"警告阈值设置为 {value} 次")
    
    def update_myopia_threshold(self, value):
        """更新近视风险警告阈值"""
        config.POSE_DETECTION_CONFIG['consecutive_myopia_risk_threshold'] = value
        self.add_log(f"近视风险阈值设置为 {value} 次")
    
    def toggle_save_images(self, checked):
        """切换保存图片设置"""
        config.POSE_DETECTION_CONFIG['save_detection_images'] = checked
        self.add_log(f"保存检测图片: {'开启' if checked else '关闭'}")
    
    def toggle_alerts(self, checked):
        """切换警告提醒设置"""
        config.POSE_DETECTION_CONFIG['alert_on_bad_posture'] = checked
        self.add_log(f"姿势警告提醒: {'开启' if checked else '关闭'}")
    
    def toggle_myopia_alerts(self, checked):
        """切换近视风险警告提醒设置"""
        config.POSE_DETECTION_CONFIG['alert_on_myopia_risk'] = checked
        self.add_log(f"近视风险提醒: {'开启' if checked else '关闭'}")
    
    def on_detection_completed(self, result_data):
        """处理检测完成信号"""
        try:
            print(f"[DEBUG] UI接收到检测完成信号: {result_data}")
            
            detection_data = result_data.get('detection_data', {})
            print(f"[DEBUG] 检测数据: {detection_data}")
            
            # 更新姿势指示器
            if detection_data.get('valid', False):
                severity = detection_data.get('severity', '未知')
                is_bad = detection_data.get('is_head_down', False)
                
                if is_bad:
                    self.posture_indicator.setText(severity)
                    self.posture_indicator.setStyleSheet("""
                        padding: 5px 10px; 
                        border-radius: 5px; 
                        background-color: #e74c3c; 
                        color: white; 
                        font-weight: bold;
                    """)
                else:
                    self.posture_indicator.setText("正常")
                    self.posture_indicator.setStyleSheet("""
                        padding: 5px 10px; 
                        border-radius: 5px; 
                        background-color: #27ae60; 
                        color: white; 
                        font-weight: bold;
                    """)
                    
                print(f"[DEBUG] 更新姿势指示器: {severity}")
                
                # 更新近视风险指示器
                myopia_risk = detection_data.get('myopia_risk', False)
                myopia_level = detection_data.get('myopia_risk_level', '未知')
                
                if myopia_risk:
                    self.myopia_indicator.setText(myopia_level)
                    # 根据风险等级设置颜色
                    if myopia_level == "高风险":
                        bg_color = "#e74c3c"  # 红色
                    elif myopia_level == "中风险":
                        bg_color = "#f39c12"  # 橙色
                    elif myopia_level == "低风险":
                        bg_color = "#f1c40f"  # 黄色
                    else:
                        bg_color = "#e74c3c"  # 默认红色
                    
                    self.myopia_indicator.setStyleSheet(f"""
                        padding: 5px 10px; 
                        border-radius: 5px; 
                        background-color: {bg_color}; 
                        color: white; 
                        font-weight: bold;
                    """)
                else:
                    self.myopia_indicator.setText("无风险")
                    self.myopia_indicator.setStyleSheet("""
                        padding: 5px 10px; 
                        border-radius: 5px; 
                        background-color: #27ae60; 
                        color: white; 
                        font-weight: bold;
                    """)
                
                print(f"[DEBUG] 更新近视风险指示器: {myopia_level}")
            
            # 更新检测结果文本
            print(f"[DEBUG] 更新结果文本")
            self.update_result_text(detection_data)
            
            # 显示检测结果图片
            result_image = result_data.get('result_image')  # 获取检测结果图像对象
            print(f"[DEBUG] 检测结果图像对象: {result_image is not None}")
            if result_image is not None:
                print(f"[DEBUG] 显示结果图像对象")
                self.display_result_frame(result_image)
            else:
                # 如果仍有文件路径，作为备用方案
                image_path = result_data.get('image_path')
                if image_path and os.path.exists(image_path):
                    print(f"[DEBUG] 显示结果图片文件: {image_path}")
                    self.display_result_image(image_path)
                else:
                    print(f"[DEBUG] 无检测结果图像可显示")
                
            # 更新统计信息
            self.update_interface()
            print(f"[DEBUG] UI更新完成")
            
        except Exception as e:
            print(f"[ERROR] 处理检测完成信号异常: {e}")
            self.add_log(f"处理检测结果失败: {e}")
    
    def on_posture_alert(self, message, consecutive_count):
        """处理姿势警告信号"""
        self.add_log(f"姿势警告: {message}")
        
        # 显示警告对话框（可选）
        if consecutive_count >= 5:  # 连续5次以上时显示警告对话框
            QMessageBox.warning(self, "姿势警告", message)
    
    def on_myopia_risk_alert(self, message, consecutive_count):
        """处理近视风险警告信号"""
        self.add_log(f"近视风险警告: {message}")
        
        # 显示警告对话框（可选）
        if consecutive_count >= 5:  # 连续5次以上时显示警告对话框
            QMessageBox.warning(self, "近视风险警告", message)
    
    def on_error_occurred(self, error_message):
        """处理错误信号"""
        self.add_log(f"错误: {error_message}")
    
    def on_status_changed(self, status):
        """处理状态变化信号"""
        self.status_label.setText(status)
        
        # 根据状态设置颜色
        if status == "检测中...":
            self.status_label.setStyleSheet("padding: 5px; background-color: #2ecc71; color: white; border-radius: 3px; font-weight: bold;")
        elif status == "已暂停":
            self.status_label.setStyleSheet("padding: 5px; background-color: #f39c12; color: white; border-radius: 3px; font-weight: bold;")
        elif status == "已停止":
            self.status_label.setStyleSheet("padding: 5px; background-color: #e74c3c; color: white; border-radius: 3px; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
    
    def on_latest_photo_ready(self, frame, timestamp):
        """处理最新照片准备信号（接收frame对象）"""
        try:
            print(f"[DEBUG] 接收到照片frame对象")
            
            # 检查界面组件是否存在
            if not hasattr(self, 'photo_label') or self.photo_label is None:
                print("[ERROR] photo_label 未初始化")
                return
                
            if not hasattr(self, 'photo_info_label') or self.photo_info_label is None:
                print("[ERROR] photo_info_label 未初始化")
                return
            
            # 检查frame是否有效
            if frame is None:
                print(f"[ERROR] 照片frame为空")
                self.photo_label.setText("照片frame为空")
                self.photo_info_label.setText("数据错误")
                return
            
            print(f"[DEBUG] Frame尺寸: {frame.shape}")
            
            # 将OpenCV frame转换为QPixmap
            try:
                # 转换BGR到RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # 创建QImage
                q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # 创建QPixmap
                pixmap = QPixmap.fromImage(q_image)
                
                if not pixmap.isNull():
                    print(f"[DEBUG] Frame转换成功，QPixmap尺寸: {pixmap.width()}x{pixmap.height()}")
                    
                    # 缩放图片以适应显示区域
                    scaled_pixmap = pixmap.scaled(
                        self.photo_label.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.photo_label.setPixmap(scaled_pixmap)
                    
                    # 更新照片信息
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    self.photo_info_label.setText(f"最新照片时间: {time_str}")
                    
                    print(f"[DEBUG] Frame显示成功")
                    self.add_log(f"显示最新照片frame")
                else:
                    print(f"[ERROR] QPixmap转换失败")
                    self.photo_label.setText("Frame转换失败")
                    self.photo_info_label.setText("转换错误")
                    
            except Exception as conversion_error:
                print(f"[ERROR] Frame转换异常: {conversion_error}")
                self.photo_label.setText("Frame转换异常")
                self.photo_info_label.setText("转换失败")
                
        except Exception as e:
            print(f"[ERROR] 显示照片frame异常: {e}")
            self.add_log(f"显示照片失败: {e}")
            self.photo_label.setText("照片显示错误")
            self.photo_info_label.setText("显示异常")
    
    def update_result_text(self, detection_data):
        """更新检测结果文本"""
        try:
            print(f"[DEBUG] 开始更新结果文本")
            
            if not detection_data.get('valid', False):
                result_text = f"检测失败: {detection_data.get('message', '未知错误')}"
            else:
                severity = detection_data.get('severity', '未知')
                is_head_down = detection_data.get('is_head_down', False)
                vertical_distance = detection_data.get('vertical_distance', 0)
                head_down_ratio = detection_data.get('head_down_ratio', 0)
                myopia_risk_level = detection_data.get('myopia_risk_level', '未知')
                myopia_risk = detection_data.get('myopia_risk', False)
                nose_to_bottom = detection_data.get('nose_to_bottom', 0)
                
                result_text = f"""检测时间: {datetime.now().strftime('%H:%M:%S')}
姿势状态: {severity}
低头状态: {'是' if is_head_down else '否'}
垂直距离: {vertical_distance:.1f} 像素
低头程度: {head_down_ratio:.3f}

近视风险评估:
风险等级: {myopia_risk_level}
有风险: {'是' if myopia_risk else '否'}
眼部距离: {nose_to_bottom:.1f} 像素

建议: {self.get_health_suggestion(is_head_down, myopia_risk, myopia_risk_level)}

{detection_data.get('message', '')}"""

            print(f"[DEBUG] 设置结果文本: {result_text[:100]}...")
            self.result_text.setPlainText(result_text)
            print(f"[DEBUG] 结果文本更新完成")
            
        except Exception as e:
            print(f"[ERROR] 更新结果文本异常: {e}")
    
    def get_health_suggestion(self, is_head_down, myopia_risk, myopia_risk_level):
        """根据检测结果提供健康建议"""
        suggestions = []
        
        if is_head_down:
            suggestions.append("请抬起头部，保持正确坐姿")
            
        if myopia_risk:
            if myopia_risk_level == "高风险":
                suggestions.append("眼部距离屏幕过近，请立即调整座椅位置")
            elif myopia_risk_level == "中风险":
                suggestions.append("请适当增加与屏幕的距离")
            elif myopia_risk_level == "低风险":
                suggestions.append("建议稍微远离屏幕一些")
                
        if not suggestions:
            suggestions.append("当前姿势良好，请继续保持")
            
        return " | ".join(suggestions)
    
    def display_result_frame(self, result_frame):
        """显示检测结果图像（frame对象）"""
        try:
            print(f"[DEBUG] 开始显示结果frame: {result_frame.shape}")
            
            # 将OpenCV frame转换为QPixmap
            try:
                # 转换BGR到RGB
                rgb_frame = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # 创建QImage
                q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # 创建QPixmap
                pixmap = QPixmap.fromImage(q_image)
                
                if not pixmap.isNull():
                    print(f"[DEBUG] 结果frame转换成功，尺寸: {pixmap.width()}x{pixmap.height()}")
                    scaled_pixmap = pixmap.scaled(self.result_image_label.size(), 
                                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.result_image_label.setPixmap(scaled_pixmap)
                    print(f"[DEBUG] 结果frame显示成功")
                else:
                    print(f"[ERROR] 结果frame转换为QPixmap失败")
                    
            except Exception as conversion_error:
                print(f"[ERROR] 结果frame转换异常: {conversion_error}")
                
        except Exception as e:
            print(f"[ERROR] 显示结果frame异常: {e}")
            self.add_log(f"显示结果图像失败: {e}")
    
    def display_result_image(self, image_path):
        """显示检测结果图像"""
        try:
            print(f"[DEBUG] 开始显示结果图像: {image_path}")
            
            # 检查文件是否存在
            if not os.path.exists(image_path):
                print(f"[ERROR] 结果图像文件不存在: {image_path}")
                return
                
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                print(f"[DEBUG] 图像加载成功，尺寸: {pixmap.width()}x{pixmap.height()}")
                scaled_pixmap = pixmap.scaled(self.result_image_label.size(), 
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.result_image_label.setPixmap(scaled_pixmap)
                print(f"[DEBUG] 结果图像显示成功")
            else:
                print(f"[ERROR] 图像加载失败: {image_path}")
                
        except Exception as e:
            print(f"[ERROR] 显示结果图像异常: {e}")
            self.add_log(f"显示结果图像失败: {e}")
    
    def update_interface(self):
        """更新界面信息"""
        if self.detection_thread:
            stats = self.detection_thread.get_detection_statistics()
            
            total = stats.get('total_detections', 0)
            bad_count = stats.get('bad_posture_count', 0)
            bad_rate = stats.get('bad_posture_rate', 0.0)
            consecutive = stats.get('consecutive_bad_posture', 0)
            
            myopia_count = stats.get('myopia_risk_count', 0)
            myopia_rate = stats.get('myopia_risk_rate', 0.0)
            consecutive_myopia = stats.get('consecutive_myopia_risk', 0)
            
            self.detection_count_label.setText(f"检测次数: {total}")
            self.bad_posture_label.setText(f"不良姿势: {bad_count} 次 ({bad_rate:.1f}%)")
            self.myopia_risk_label.setText(f"近视风险: {myopia_count} 次 ({myopia_rate:.1f}%)")
            self.consecutive_label.setText(f"连续不良: {consecutive} 次")
            self.consecutive_myopia_label.setText(f"连续近视风险: {consecutive_myopia} 次")
    
    def add_log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.detection_thread:
            self.detection_thread.stop_detection()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序图标和名称
    app.setApplicationName("智能姿势检测系统")
    app.setApplicationVersion("1.0.0")
    
    try:
        # 创建主窗口
        main_window = PostureMonitorWidget()
        main_window.show()
        
        # 运行应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        QMessageBox.critical(None, "启动错误", f"应用程序启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
