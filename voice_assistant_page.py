# -*- coding: utf-8 -*-
"""
语音助手界面
"""

import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QStackedWidget, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor
from config import CONTROL_COMMANDS

# 设置日志
logger = logging.getLogger(__name__)

class MessageBubble(QWidget):
    """消息气泡组件"""
    
    def __init__(self, message, is_user=True, status=None, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_user = is_user
        self.status = status
        self.setup_ui()
    
    def setup_ui(self):
        """设置消息气泡UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 消息容器
        message_container = QHBoxLayout()
        
        if self.is_user:
            # 用户消息 - 右边
            message_container.addStretch()
            bubble = self.create_user_bubble()
            message_container.addWidget(bubble)
        else:
            # AI消息 - 左边红色区域
            bubble = self.create_ai_bubble()
            message_container.addWidget(bubble)
            message_container.addStretch()
        
        layout.addLayout(message_container)
        self.setLayout(layout)
    
    def create_user_bubble(self):
        """创建用户消息气泡"""
        frame = QFrame()
        frame.setMaximumWidth(500)
        frame.setStyleSheet("""
            QFrame {
                background-color: #007bff;
                border-radius: 15px;
                padding: 10px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: normal;
                background-color: transparent;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # 消息文本
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(message_label)
        
        return frame
    
    def create_ai_bubble(self):
        """创建AI消息气泡"""
        frame = QFrame()
        frame.setMaximumWidth(500)
        frame.setStyleSheet("""
            QFrame {
                background-color: #d73027;
                border-radius: 15px;
                padding: 10px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: normal;
                background-color: transparent;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # 状态标签（如果有）
        if self.status:
            status_label = QLabel(self.status)
            status_label.setStyleSheet("""
                QLabel {
                    color: #ffcccc;
                    font-size: 12px;
                    font-style: italic;
                }
            """)
            layout.addWidget(status_label)
        
        # 消息文本
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(message_label)
        
        return frame

class VoiceAssistantPage(QWidget):
    """语音助手页面"""
    
    back_requested = pyqtSignal()  # 返回信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_history = []  # 对话历史
        self.current_status = None  # 当前状态
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建堆叠组件
        self.stacked_widget = QStackedWidget()
        
        # 欢迎界面
        welcome_page = self.create_welcome_page()
        self.stacked_widget.addWidget(welcome_page)
        
        # 对话界面
        self.chat_page = self.create_chat_page()
        self.stacked_widget.addWidget(self.chat_page)
        
        # 默认显示欢迎界面
        self.stacked_widget.setCurrentIndex(0)
        
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)
        
        # 设置页面样式
        self.setStyleSheet("""
            QWidget {
                background-color: #434C5E;
                color: #ECEFF4;
            }
        """)
    
    def create_welcome_page(self):
        """创建欢迎界面"""
        widget = QWidget()
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # AI图标
        ai_icon_label = QLabel()
        if os.path.exists("AI.png"):
            pixmap = QPixmap("AI.png")
            if not pixmap.isNull():
                # 缩放到合适大小
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ai_icon_label.setPixmap(scaled_pixmap)
        else:
            ai_icon_label.setText("🤖")
            ai_icon_label.setStyleSheet("font-size: 100px;")
        
        ai_icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(ai_icon_label)
        
        # 欢迎文字
        welcome_label = QLabel("我是你的专属语音助手，广和通\n请问今天有什么问题吗？")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #FFF;
                line-height: 1.5;
                padding: 20px;
            }
        """)
        layout.addWidget(welcome_label)
        
        # 提示文字
        hint_label = QLabel('说出"你好广和通"开始对话')
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #FFF;
                margin-top: 20px;
            }
        """)
        layout.addWidget(hint_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_chat_page(self):
        """创建对话界面"""
        widget = QWidget()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部标题栏
        header = self.create_header()
        layout.addWidget(header)
        
        # 对话区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f8f9fa;
            }
        """)
        
        # 对话内容容器
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(0)
        self.chat_layout.addStretch()  # 在底部添加弹性空间
        
        self.scroll_area.setWidget(self.chat_content)
        layout.addWidget(self.scroll_area)
        
        # 底部提示
        self.bottom_hint = QLabel("使用手势识别操控，6-0-2 返回")
        self.bottom_hint.setAlignment(Qt.AlignCenter)
        self.bottom_hint.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #999;
                padding: 10px;
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.bottom_hint)
        
        widget.setLayout(layout)
        return widget
    
    def create_header(self):
        """创建标题栏"""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-bottom: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        
        # 左侧AI图标
        ai_icon = QLabel()
        if os.path.exists("AI.png"):
            pixmap = QPixmap("AI.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ai_icon.setPixmap(scaled_pixmap)
        else:
            ai_icon.setText("🤖")
            ai_icon.setStyleSheet("font-size: 30px;")
        
        # 标题
        title_label = QLabel("广和通语音助手")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #333;
                margin-left: 10px;
            }
        """)
        
        # 状态指示器
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                font-style: italic;
            }
        """)
        
        layout.addWidget(ai_icon)
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
        
        header.setLayout(layout)
        return header
    
    def switch_to_chat(self):
        """切换到对话界面"""
        self.stacked_widget.setCurrentIndex(1)
        logger.info("切换到对话界面")
    
    def add_user_message(self, message):
        """添加用户消息"""
        bubble = MessageBubble(message, is_user=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        
        # 保存到历史记录
        self.conversation_history.append({"type": "user", "message": message})
        logger.info(f"添加用户消息: {message}")
    
    def add_ai_message(self, message, status=None):
        """添加AI消息"""
        bubble = MessageBubble(message, is_user=False, status=status)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        
        # 保存到历史记录
        self.conversation_history.append({"type": "ai", "message": message, "status": status})
        logger.info(f"添加AI消息: {message}")
    
    def update_status(self, status):
        """更新状态"""
        self.current_status = status
        self.status_label.setText(status)
        logger.info(f"更新状态: {status}")
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))
    
    def scroll_up(self):
        """向上滚动"""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        scrollbar.setValue(current_value - 100)
        logger.info("向上滚动")
    
    def scroll_down(self):
        """向下滚动"""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        scrollbar.setValue(current_value + 100)
        logger.info("向下滚动")
    
    def handle_control_command(self, command):
        """处理控制指令"""
        if command == 'back':
            # 返回功能选择界面
            self.back_requested.emit()
        elif command == 'up':
            # 上滑
            self.scroll_up()
        elif command == 'down':
            # 下滑
            self.scroll_down()
        else:
            logger.info(f"未处理的控制指令: {command}")
    
    def clear_conversation(self):
        """清空对话"""
        # 清除所有消息气泡
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                item.widget().deleteLater()
        
        # 清空历史记录
        self.conversation_history = []
        logger.info("清空对话历史")
    
    def get_conversation_history(self):
        """获取对话历史"""
        return self.conversation_history
    
    def is_in_chat_mode(self):
        """是否在对话模式"""
        return self.stacked_widget.currentIndex() == 1 