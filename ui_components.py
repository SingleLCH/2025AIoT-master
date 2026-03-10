# -*- coding: utf-8 -*-
"""
UI组件模块
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from config import NOTIFICATION_CONFIG, FUNCTION_ICONS, FUNCTION_NAMES
import logging

logger = logging.getLogger(__name__)


class NotificationWidget(QWidget):
    """通知窗口组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        """设置UI"""
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(NOTIFICATION_CONFIG['width'], NOTIFICATION_CONFIG['height'])
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 通知容器（无边框的简洁设计）
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
            }
        """)
        
        # 通知内容布局
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 12, 15, 12)
        container_layout.setSpacing(8)
        
        # 标题标签
        self.title_label = QLabel("通知")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 28px;
                font-weight: bold;
                border: none;
                background: transparent;
            }
        """)
        self.title_label.setAlignment(Qt.AlignLeft)
        
        # 消息标签
        self.message_label = QLabel()
        self.message_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 24px;
                border: none;
                background: transparent;
            }
        """)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft)
        
        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.message_label)
        
        layout.addWidget(self.container)
        self.setLayout(layout)
        
        # 初始隐藏
        self.hide()
        
    def setup_animation(self):
        """设置动画"""
        from PyQt5.QtCore import QEasingCurve
        
        # 滑入动画
        self.slide_in_animation = QPropertyAnimation(self, b"geometry")
        self.slide_in_animation.setDuration(300)  # 更快的动画
        self.slide_in_animation.setEasingCurve(QEasingCurve.OutCubic)  # 更平滑的缓动
        
        # 滑出动画
        self.slide_out_animation = QPropertyAnimation(self, b"geometry")
        self.slide_out_animation.setDuration(300)  # 更快的动画
        self.slide_out_animation.setEasingCurve(QEasingCurve.InCubic)  # 更平滑的缓动
        self.slide_out_animation.finished.connect(self.hide)
        
        # 透明度动画
        self.opacity_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_in_animation.setDuration(300)
        self.opacity_in_animation.setStartValue(0.0)
        self.opacity_in_animation.setEndValue(1.0)
        self.opacity_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # 自动隐藏定时器
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.timeout.connect(self.slide_out)
        
    def show_notification(self, title, message):
        """显示通知"""
        # 停止之前的动画和定时器
        self.slide_in_animation.stop()
        self.slide_out_animation.stop()
        self.opacity_in_animation.stop()
        self.auto_hide_timer.stop()
        
        self.title_label.setText(title)
        self.message_label.setText(message)
        
        # 计算位置
        if self.parent_widget:
            parent_rect = self.parent_widget.geometry()
            # 从右侧滑入，位置更靠近右上角
            start_x = parent_rect.right()
            end_x = parent_rect.right() - self.width() - 15
            y = parent_rect.top() + 15
            
            start_rect = QRect(start_x, y, self.width(), self.height())
            end_rect = QRect(end_x, y, self.width(), self.height())
            
            # 设置起始位置，初始透明
            self.setGeometry(start_rect)
            self.setWindowOpacity(0.0)
            self.show()
            
            # 同时播放滑入和淡入动画
            self.slide_in_animation.setStartValue(start_rect)
            self.slide_in_animation.setEndValue(end_rect)
            self.slide_in_animation.start()
            self.opacity_in_animation.start()
            
            # 设置自动隐藏
            self.auto_hide_timer.start(NOTIFICATION_CONFIG['show_duration'] * 1000)
        else:
            # 如果没有父窗口，居中显示
            self.setWindowOpacity(1.0)
            self.show()
            
    def slide_out(self):
        """滑出隐藏"""
        from PyQt5.QtCore import QEasingCurve
        
        # 停止自动隐藏定时器
        self.auto_hide_timer.stop()
        
        if self.parent_widget:
            current_rect = self.geometry()
            end_rect = QRect(self.parent_widget.geometry().right(), 
                           current_rect.y(), 
                           current_rect.width(), 
                           current_rect.height())
            
            # 创建淡出动画
            self.opacity_out_animation = QPropertyAnimation(self, b"windowOpacity")
            self.opacity_out_animation.setDuration(300)
            self.opacity_out_animation.setStartValue(1.0)
            self.opacity_out_animation.setEndValue(0.0)
            self.opacity_out_animation.setEasingCurve(QEasingCurve.InCubic)
            
            # 同时播放滑出和淡出动画
            self.slide_out_animation.setStartValue(current_rect)
            self.slide_out_animation.setEndValue(end_rect)
            self.slide_out_animation.start()
            self.opacity_out_animation.start()
        else:
            self.hide()





class SelectionWidget(QWidget):
    """选择界面组件（学校/家庭）"""
    
    selection_made = pyqtSignal(str)  # 选择完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_selection = 0  # 0: 学校, 1: 家庭
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # 标题
        title_label = QLabel("请选择使用环境")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-bottom: 30px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 选择按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(50)
        
        # 学校按钮
        self.school_button = self.create_mode_button("公用模式", "🏫")
        
        # 家庭按钮
        self.home_button = self.create_mode_button("个人模式", "🏠")
        
        button_layout.addWidget(self.school_button)
        button_layout.addWidget(self.home_button)
        
        layout.addLayout(button_layout)
        
        # 提示文本
        hint_label = QLabel("使用手势识别操控")
        hint_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                margin-top: 20px;
            }
        """)
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)
        
        self.setLayout(layout)
        
        # 更新选择状态
        self.update_selection()
        
    def create_mode_button(self, text, icon):
        """创建模式选择按钮"""
        button = QPushButton()
        button.setFixedSize(200, 150)
        
        # 创建垂直布局
        layout = QVBoxLayout(button)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        
        # 图标标签
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                margin: 10px;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # 文本标签
        text_label = QLabel(text)
        text_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
        """)
        text_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        
        # 按钮样式
        button.setStyleSheet("""
            QPushButton {
                background-color: #3B4252;
                border: 2px solid #4C566A;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                color: #ECEFF4;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #4CAF50;
            }
        """)
        
        return button
        
    def update_selection(self):
        """更新选择状态"""
        # 重置学校按钮样式
        self.school_button.setStyleSheet("""
            QPushButton {
                background-color: #3B4252;
                border: 2px solid #4C566A;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                color: #ECEFF4;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #4CAF50;
            }
        """)
        
        # 重置家庭按钮样式
        self.home_button.setStyleSheet("""
            QPushButton {
                background-color: #3B4252;
                border: 2px solid #4C566A;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                color: #ECEFF4;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #4CAF50;
            }
        """)
        
        # 高亮当前选择
        if self.current_selection == 0:
            self.school_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 2px solid #45a049;
                    border-radius: 15px;
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                }
            """)
        else:
            self.home_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 2px solid #45a049;
                    border-radius: 15px;
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                }
            """)
    
    def handle_control_command(self, action):
        """处理控制指令"""
        if action == 'prev':  # 左边 - 学校
            self.current_selection = 0
            self.update_selection()
        elif action == 'next':  # 右边 - 家庭
            self.current_selection = 1
            self.update_selection()
        elif action == 'confirm':  # 确认选择
            selection = 'school' if self.current_selection == 0 else 'home'
            self.selection_made.emit(selection)


class FunctionCard(QWidget):
    """单个功能卡片组件"""
    
    def __init__(self, function_key, parent=None):
        super().__init__(parent)
        self.function_key = function_key
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        # 获取图标和名称
        icon_path = FUNCTION_ICONS.get(self.function_key, '')
        function_name = FUNCTION_NAMES.get(self.function_key, self.function_key)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # 图标容器
        icon_container = QFrame()
        icon_container.setFixedSize(200, 200)
        icon_container.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 20px;
                border: 2px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        # 图标布局
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        # 图标标签
        self.icon_label = QLabel()
        if icon_path:
            try:
                from PyQt5.QtGui import QIcon
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
            except Exception as e:
                logger.warning(f"加载图标失败 {icon_path}: {e}")
                self.icon_label.setText("🔧")
                self.icon_label.setStyleSheet("font-size: 60px;")
        else:
            self.icon_label.setText("🔧")
            self.icon_label.setStyleSheet("font-size: 60px;")
            
        self.icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(self.icon_label)
        
        # 功能名称
        name_label = QLabel(function_name)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        name_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_container)
        layout.addWidget(name_label)
        self.setLayout(layout)


class MainFunctionWidget(QWidget):
    """主功能界面组件"""
    
    function_selected = pyqtSignal(str)  # 功能选择信号
    
    def __init__(self, environment, parent=None):
        super().__init__(parent)
        self.environment = environment
        self.current_selection = 0
        self.functions = []
        self.function_cards = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        from config import FEATURES
        
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        
        # 环境标题
        env_name = FEATURES[self.environment]['name']
        title_label = QLabel(f"智能拍照搜题系统 - {env_name}模式")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 卡片容器
        self.card_container = QWidget()
        self.card_container.setFixedSize(400, 300)
        
        # 获取可用功能
        self.functions = FEATURES[self.environment]['enabled_functions']
        
        # 创建功能卡片
        for function_key in self.functions:
            card = FunctionCard(function_key)
            card.setParent(self.card_container)
            card.setGeometry(0, 0, 400, 300)
            card.hide()
            self.function_cards.append(card)
        
        main_layout.addWidget(self.card_container)
        
        # 指示器
        indicator_layout = QHBoxLayout()
        indicator_layout.setAlignment(Qt.AlignCenter)
        
        self.indicators = []
        for i in range(len(self.functions)):
            indicator = QLabel("●")
            indicator.setStyleSheet("""
                QLabel {
                    color: #ccc;
                    font-size: 16px;
                    margin: 0 5px;
                }
            """)
            indicator_layout.addWidget(indicator)
            self.indicators.append(indicator)
        
        main_layout.addLayout(indicator_layout)
        
        # 操作提示
        hint_label = QLabel("使用手势识别操控")
        hint_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #999;
                margin-top: 10px;
            }
        """)
        hint_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint_label)
        
        self.setLayout(main_layout)
        
        # 显示第一个卡片
        self.update_display()
        
    def update_display(self):
        """更新显示"""
        # 隐藏所有卡片
        for card in self.function_cards:
            card.hide()
        
        # 显示当前选择的卡片
        if 0 <= self.current_selection < len(self.function_cards):
            self.function_cards[self.current_selection].show()
        
        # 更新指示器
        for i, indicator in enumerate(self.indicators):
            if i == self.current_selection:
                indicator.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 16px;
                        margin: 0 5px;
                    }
                """)
            else:
                indicator.setStyleSheet("""
                    QLabel {
                        color: #ccc;
                        font-size: 16px;
                        margin: 0 5px;
                    }
                """)
    
    def handle_control_command(self, action):
        """处理控制指令"""
        if action == 'next':  # 右移
            self.current_selection = (self.current_selection + 1) % len(self.functions)
            self.update_display()
        elif action == 'prev':  # 左移
            self.current_selection = (self.current_selection - 1) % len(self.functions)
            self.update_display()
        elif action == 'confirm':  # 确认选择
            if 0 <= self.current_selection < len(self.functions):
                selected_function = self.functions[self.current_selection]
                self.function_selected.emit(selected_function)