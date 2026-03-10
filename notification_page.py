# -*- coding: utf-8 -*-
"""
通知页面模块
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QScrollArea, QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QFont
import logging
import json

logger = logging.getLogger(__name__)


class NotificationItem(QFrame):
    """单个通知项组件"""
    
    def __init__(self, notification_data, parent=None):
        super().__init__(parent)
        self.notification_data = notification_data
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        # 设置框架样式
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border: 1px solid #4C566A;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        # 标题和时间
        header_layout = QHBoxLayout()
        
        # 通知类型/发送者
        sender = self.notification_data.get('from', '系统')
        type_label = QLabel(f"来自: {sender}")
        type_label.setFont(QFont("Microsoft YaHei", 30, QFont.Bold))  # 15 → 30 (再放大2倍) + 加粗
        type_label.setStyleSheet("color: #88C0D0; font-size: 30px; font-weight: bold; background: transparent; border: none;")
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        # 时间戳
        timestamp = self.notification_data.get('timestamp', '')
        time_label = QLabel(timestamp)
        time_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))  # 14 → 28 (再放大2倍) + 加粗
        time_label.setStyleSheet("color: #D8DEE9; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # 通知内容
        message = self.notification_data.get('message', '无消息内容')
        content_label = QLabel(message)
        content_label.setFont(QFont("Microsoft YaHei", 34, QFont.Bold))  # 17 → 34 (再放大2倍) + 加粗
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #ECEFF4; font-size: 34px; font-weight: bold; line-height: 1.4; background: transparent; border: none;")
        layout.addWidget(content_label)
        
        # 如果是视频邀请，显示房间号
        if 'room_id' in self.notification_data:
            room_id = self.notification_data['room_id']
            room_label = QLabel(f"房间号: {room_id}")
            room_label.setFont(QFont("Microsoft YaHei", 30, QFont.Bold))  # 15 → 30 (再放大2倍) + 加粗
            room_label.setStyleSheet("color: #A3BE8C; font-size: 30px; font-weight: bold; background: transparent; border: none;")
            layout.addWidget(room_label)
        
        self.setLayout(layout)


class NotificationPage(QWidget):
    """通知页面组件"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 通知数据存储
        self.notifications = []
        self.current_scroll_position = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("通知中心")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 96px;
                font-weight: bold;
                color: #ECEFF4;
                margin-bottom: 10px;
            }
        """)
        title_layout.addWidget(title_label)
        
        main_layout.addLayout(title_layout)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #434C5E;
            }
            QScrollBar:vertical {
                background: #2E3440;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4C566A;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5E81AC;
            }
        """)
        
        # 通知容器
        self.notification_container = QWidget()
        self.notification_layout = QVBoxLayout(self.notification_container)
        self.notification_layout.setContentsMargins(0, 0, 0, 0)
        self.notification_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.notification_container)
        main_layout.addWidget(self.scroll_area)
        
        # 操作提示
        self.hint_label = QLabel("上下滑动浏览通知，按6-0-2返回功能选择")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("""
            QLabel {
                font-size: 42px;
                font-weight: bold;
                color: #D8DEE9;
                padding: 10px;
                background-color: #3B4252;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.hint_label)
        
        self.setLayout(main_layout)
        
        # 设置页面样式
        self.setStyleSheet("""
            QWidget {
                background-color: #434C5E;
                color: #ECEFF4;
            }
        """)
        
        # 初始化显示
        self.refresh_notifications()
        
    def refresh_notifications(self):
        """刷新通知显示"""
        # 清空现有通知显示
        for i in reversed(range(self.notification_layout.count())):
            item = self.notification_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        if not self.notifications:
            # 没有通知时显示提示
            no_notification_label = QLabel("暂无通知")
            no_notification_label.setAlignment(Qt.AlignCenter)
            no_notification_label.setStyleSheet("""
                QLabel {
                    font-size: 36px;
                    font-weight: bold;
                    color: #D8DEE9;
                    padding: 50px;
                    background-color: #3B4252;
                    border-radius: 10px;
                    border: 2px dashed #4C566A;
                }
            """)
            self.notification_layout.addWidget(no_notification_label)
        else:
            # 显示所有通知（按时间倒序）
            sorted_notifications = sorted(self.notifications, 
                                        key=lambda x: x.get('timestamp', ''), 
                                        reverse=True)
            
            for notification in sorted_notifications:
                notification_item = NotificationItem(notification)
                self.notification_layout.addWidget(notification_item)
        
        # 添加弹性空间
        self.notification_layout.addStretch()
        
        # 更新提示文本
        count = len(self.notifications)
        if count > 0:
            self.hint_label.setText(f"共{count}条通知 | 上下滑动浏览通知，双击返回功能选择")
        else:
            self.hint_label.setText("暂无通知 | 双击返回功能选择")
    
    def add_notification(self, notification_data):
        """添加新通知"""
        self.notifications.append(notification_data)
        self.refresh_notifications()
        logger.info(f"添加新通知: {notification_data.get('message', '')}")
    
    def clear_notifications(self):
        """清空所有通知"""
        self.notifications.clear()
        self.refresh_notifications()
        logger.info("清空所有通知")
    
    def scroll_up(self):
        """向上滚动"""
        scroll_bar = self.scroll_area.verticalScrollBar()
        current_value = scroll_bar.value()
        scroll_bar.setValue(current_value - 100)
        
    def scroll_down(self):
        """向下滚动"""
        scroll_bar = self.scroll_area.verticalScrollBar()
        current_value = scroll_bar.value()
        scroll_bar.setValue(current_value + 100)
    
    @pyqtSlot(str)
    def handle_control_command(self, command):
        """处理控制指令"""
        logger.info(f"通知页面接收到控制指令: {command}")
        
        if command == '6-0-2' or command == 'back':
            # 返回功能选择页面
            self.back_requested.emit()
        elif command == '6-0-5' or command == 'up':
            # 上滑
            self.scroll_up()
        elif command == '6-0-6' or command == 'down':
            # 下滑
            self.scroll_down()
    
    def get_notification_count(self):
        """获取通知数量"""
        return len(self.notifications)
    
    def get_latest_notification(self):
        """获取最新通知"""
        if self.notifications:
            return max(self.notifications, key=lambda x: x.get('timestamp', ''))
        return None 