# -*- coding: utf-8 -*-
import sys
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout)
from config import FEATURES, FUNCTION_ICONS, FUNCTION_NAMES

class ModeButton(QPushButton):
    """模式选择按钮"""
    def __init__(self, text, icon_path=""):
        super().__init__()
        self.setFixedSize(400, 240)  # 放大2倍：200*2=400, 120*2=240
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)  # 放大2倍：10*2=20
        
        # 图标标签
        if icon_path:
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # 缩放图标到合适大小 - 放大2倍：48*2=96
                scaled_pixmap = pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("📱")  # 备用图标
                icon_label.setStyleSheet("font-size: 64px;")  # 放大2倍：32*2=64
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)
        
        # 文字标签
        text_label = QLabel(text)
        text_label.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))  # 放大2倍：12*2=24
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)
        
        self.setStyleSheet("""
            ModeButton{
                background: #2E3440;
                border: 4px solid #4C566A;
                border-radius: 30px;
                color: #ECEFF4;
                font-weight: bold;
            }
            ModeButton:hover{
                background: #3B4252;
                border-color: #88C0D0;
            }
            ModeButton:checked{
                background: #5E81AC;
                border-color: #88C0D0;
                color: #ECEFF4;
            }
        """)

class FunctionButton(QPushButton):
    """功能选择按钮（仿照模式选择风格）"""
    def __init__(self, text, icon_path=""):
        super().__init__()
        self.setFixedSize(160, 100)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # 图标标签
        if icon_path:
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                # 缩放图标到合适大小
                scaled_pixmap = pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("⚙️")  # 备用图标
                icon_label.setStyleSheet("font-size: 24px;")
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)
        
        # 文字标签
        text_label = QLabel(text)
        text_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        self.setCheckable(True)
        self.setStyleSheet("""
            FunctionButton{
                background: #2E3440;
                border: 2px solid #4C566A;
                border-radius: 12px;
                color: #ECEFF4;
                font-weight: bold;
            }
            FunctionButton:hover{
                background: #3B4252;
                border-color: #88C0D0;
            }
            FunctionButton:checked{
                background: #5E81AC;
                border-color: #88C0D0;
                color: #ECEFF4;
                font-size: 11px;
                border: 3px solid #88C0D0;
            }
        """)

class SideButton(QPushButton):
    """带图标+文字的导航按钮"""
    def __init__(self, icon_path, text):
        super().__init__()
        self.setFixedSize(240, 70)  # 增大按钮尺寸
        self.icon_path = icon_path
        self.text = text
        
        # 设置为可选中状态
        self.setCheckable(True)
        
        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)  # 增大内边距
        layout.setSpacing(15)  # 增大间距
        
        # 图标标签
        self.icon_label = QLabel()
        self.update_icon()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(53, 53)  # 放大1.5倍：35*1.5≈53
        
        # 文字标签
        self.text_label = QLabel(text)
        self.text_label.setFont(QFont("Microsoft YaHei", 20))  # 放大1.5倍：13*1.5≈20
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # 移除手动样式设置，让CSS控制
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label, 1)
        
        # 设置完整的CSS样式，包括选中状态的所有效果
        self.setStyleSheet("""
            SideButton{
                text-align:left;
                border:3px solid transparent;
                border-radius:15px;
                color: #ECEFF4;
                background: transparent;
                padding: 10px 15px;
                margin: 3px;
            }
            SideButton:hover{
                background:#3B4252;
                border-color: #4C566A;
            }
            SideButton:checked{
                background:#5E81AC;
                color:#ECEFF4;
                border: 4px solid #88C0D0;
                border-radius: 15px;
                padding: 12px 18px;
                margin: 0px;
            }
        """)
        
        # 连接状态变化信号
        self.toggled.connect(self.on_toggled)
    
    def update_icon(self, is_selected=False):
        """更新图标显示"""
        if self.icon_path:
            pixmap = QPixmap(self.icon_path)
            if not pixmap.isNull():
                # 根据选中状态调整图标大小 - 放大1.5倍：30->45, 40->60
                size = 60 if is_selected else 45  # 放大1.5倍图标尺寸
                scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(scaled_pixmap)
            else:
                self.icon_label.setText("●")
                self.icon_label.setStyleSheet(f"font-size: {'33px' if is_selected else '27px'}; color: {'#88C0D0' if is_selected else '#ECEFF4'};")

    def on_toggled(self, checked):
        """状态切换时的处理"""
        # 更新图标显示状态
        self.update_icon(checked)
        
        if checked:
            # 选中状态：有颜色变化但字体不高亮
            self.icon_label.setFixedSize(45, 45)  # 🔧 取消放大效果：与未选中状态保持一致
            
            # 保持一致的字体大小，不加粗
            font = self.text_label.font()
            font.setPointSize(20)  # 放大1.5倍：13*1.5≈20
            font.setBold(False)  # 不加粗
            self.text_label.setFont(font)
            
            # 🔧 设置最小宽度确保文字完整显示
            font_metrics = self.text_label.fontMetrics()
            text_width = font_metrics.width(self.text_label.text())
            self.text_label.setMinimumWidth(text_width + 50)  # 增加50px确保完整显示
            
            # 选中时的颜色变化（但不改变字体样式）
            self.text_label.setStyleSheet("""
                color: #88C0D0;
                border-top: 2px solid #88C0D0;
                border-bottom: 2px solid #88C0D0;
                border-left: none;
                border-right: none;
                padding-top: 2px;
                padding-bottom: 2px;
                padding-left: 4px;
                padding-right: 30px;
                background-color: rgba(136, 192, 208, 0.1);
            """)  # 选中时文字变蓝色 + 上下蓝色边框，增加右边padding解决显示不完全
            self.icon_label.setStyleSheet("color: #88C0D0;")  # 图标也变蓝色
            
            # 🔧 修复边框显示问题：直接设置QPushButton的样式
            self.setStyleSheet("""
                QPushButton {
                    border: 2px solid #88C0D0;
                    border-radius: 8px;
                    background-color: rgba(136, 192, 208, 0.1);
                }
                QPushButton:hover {
                    background-color: rgba(136, 192, 208, 0.2);
                }
            """)
        else:
            # 未选中状态：恢复默认外观
            self.icon_label.setFixedSize(45, 45)  # 放大1.5倍：30*1.5=45
            
            # 恢复默认字体
            font = self.text_label.font()
            font.setPointSize(20)  # 放大1.5倍：13*1.5≈20
            font.setBold(False)
            self.text_label.setFont(font)
            
            # 清除最小宽度限制
            self.text_label.setMinimumWidth(0)
            
            # 清除颜色和样式
            self.text_label.setStyleSheet("color: #ECEFF4;")
            self.icon_label.setStyleSheet("")
            self.setStyleSheet("")  # 清除按钮边框

class ModeSelectionPage(QFrame):
    """模式选择页面"""
    
    mode_selected = pyqtSignal(str)  # 模式选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_selection = 0  # 0: 学校, 1: 家庭
        self.setStyleSheet("background: transparent;")
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(60)  # 放大2倍：30*2=60
        
        # 标题
        title = QLabel("请选择使用模式")
        title.setFont(QFont("Microsoft YaHei", 56, QFont.Bold))  # 放大2倍：28*2=56
        title.setStyleSheet("color: #88C0D0; margin-bottom: 40px;")  # 放大2倍：20*2=40
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 按钮容器
        button_layout = QHBoxLayout()
        button_layout.setSpacing(100)  # 放大2倍：50*2=100
        
        # 学校模式按钮
        self.school_btn = ModeButton("公用模式", "img/school.png")
        self.school_btn.clicked.connect(lambda: self.select_mode("school"))
        button_layout.addWidget(self.school_btn)
        
        # 家庭模式按钮
        self.home_btn = ModeButton("个人模式", "img/home.png")
        self.home_btn.clicked.connect(lambda: self.select_mode("home"))
        button_layout.addWidget(self.home_btn)
        
        layout.addLayout(button_layout)
        
        # 描述文字
        desc = QLabel("选择适合您使用场景的模式")
        desc.setFont(QFont("Microsoft YaHei", 24))  # 放大2倍：12*2=24
        desc.setStyleSheet("color: #D8DEE9; margin-top: 40px;")  # 放大2倍：20*2=40
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # 更新选择状态
        self.update_selection()
    
    def update_selection(self):
        """更新选择状态"""
        # 重置按钮样式
        self.school_btn.setStyleSheet("""
            ModeButton{
                background: #2E3440;
                border: 4px solid #4C566A;
                border-radius: 30px;
                color: #ECEFF4;
                font-weight: bold;
            }
            ModeButton:hover{
                background: #3B4252;
                border-color: #88C0D0;
            }
            ModeButton:pressed{
                background: #434C5E;
            }
        """)
        
        self.home_btn.setStyleSheet("""
            ModeButton{
                background: #2E3440;
                border: 4px solid #4C566A;
                border-radius: 30px;
                color: #ECEFF4;
                font-weight: bold;
            }
            ModeButton:hover{
                background: #3B4252;
                border-color: #88C0D0;
            }
            ModeButton:pressed{
                background: #434C5E;
            }
        """)
        
        # 高亮当前选择
        if self.current_selection == 0:  # 学校模式
            self.school_btn.setStyleSheet("""
                ModeButton{
                    background: #5E81AC;
                    border: 6px solid #88C0D0;
                    border-radius: 30px;
                    color: #ECEFF4;
                    font-weight: bold;
                }
            """)
        else:  # 家庭模式
            self.home_btn.setStyleSheet("""
                ModeButton{
                    background: #5E81AC;
                    border: 6px solid #88C0D0;
                    border-radius: 30px;
                    color: #ECEFF4;
                    font-weight: bold;
                }
            """)
    
    def handle_control_command(self, action):
        """处理控制指令"""
        if action == 'next' or action == 'prev':  # 左右切换模式
            self.current_selection = (self.current_selection + 1) % 2
            self.update_selection()
        elif action == 'confirm':  # 确认选择
            if self.current_selection == 0:
                self.select_mode("school")
            else:
                self.select_mode("home")
    
    def select_mode(self, mode):
        """选择模式并切换到功能页面"""
        self.mode_selected.emit(mode)
        if self.parent_window:
            self.parent_window.switch_to_function_page(mode)

class FunctionPage(QFrame):
    """右侧功能页模板"""
    def __init__(self, title, function_key, color="#88C0D0"):
        super().__init__()
        self.function_key = function_key
        self.setStyleSheet("background: #434C5E; border: none;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # 功能图标
        icon_label = QLabel()
        if function_key == 'about':
            # 关于页面特殊处理
            pixmap = QPixmap("img/about.png")
        elif function_key in FUNCTION_ICONS:
            pixmap = QPixmap(FUNCTION_ICONS[function_key])
        else:
            pixmap = QPixmap()
        
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
        else:
            icon_label.setText("📱")
            icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # 标题
        label = QLabel(title, alignment=Qt.AlignCenter)
        label.setFont(QFont("Microsoft YaHei", 36, QFont.Bold))
        label.setStyleSheet(f"color:{color}; margin: 20px;")
        layout.addWidget(label)
        
        # 内容
        if function_key == 'about':
            # 关于页面内容
            self.create_about_content(layout)
        else:
            # 其他功能页面内容
            content = QLabel(f"当前选中的是{title}的功能界面\n\n点击确认进入功能")
            content.setFont(QFont("Microsoft YaHei", 20))
            content.setStyleSheet("color: #D8DEE9; margin: 20px;")
            content.setAlignment(Qt.AlignCenter)
            layout.addWidget(content)
    
    def create_about_content(self, layout):
        """创建关于页面内容"""
        # AI图标
        ai_icon = QLabel()
        ai_pixmap = QPixmap("AI.png")
        if not ai_pixmap.isNull():
            scaled_ai = ai_pixmap.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ai_icon.setPixmap(scaled_ai)
        else:
            ai_icon.setText("🤖")
            ai_icon.setStyleSheet("font-size: 80px;")
        ai_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(ai_icon)
        
        # 版权信息
        copyright_label = QLabel("Copyright © 19372团队")
        copyright_label.setFont(QFont("Microsoft YaHei", 14))
        copyright_label.setStyleSheet("color: #D8DEE9; margin: 20px;")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 版本信息
        version_label = QLabel("智能学习助手 v1.0")
        version_label.setFont(QFont("Microsoft YaHei", 12))
        version_label.setStyleSheet("color: #81A1C1; margin: 10px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

class FunctionSelectionWidget(QWidget):
    """功能选择界面"""
    
    function_selected = pyqtSignal(str)  # 功能选择信号
    back_requested = pyqtSignal()  # 返回请求信号
    notification_requested = pyqtSignal(str, str)  # 通知请求信号(title, message)
    
    def __init__(self, mode="school"):
        super().__init__()
        self.mode = mode
        self.current_index = 0
        self.buttons = []
        
        # 设置统一的背景样式
        self.setStyleSheet("""
            QWidget {
                background: #434C5E;
                color: #ECEFF4;
            }
        """)
        
        self.init_ui()
    
    def init_ui(self):
        # ---- 左侧导航 ----
        nav = QFrame()
        nav.setFixedWidth(320)  # 增加左边框宽度，从280改为320
        nav.setStyleSheet("background:#2E3440; border: none;")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(15, 20, 15, 20)  # 也增加内边距
        nav_layout.setSpacing(18)  # 增加按钮间距
        
        # 模式标题
        mode_title = QLabel(f"当前模式: {self.mode_name()}")
        mode_title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))  # 放大1.5倍：12*1.5=18
        mode_title.setStyleSheet("color: #88C0D0; margin-bottom: 10px;")
        mode_title.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(mode_title)
        
        # 功能按钮
        self.buttons = []
        functions = self.get_functions_by_mode()
        
        for idx, (function_key, text) in enumerate(functions):
            icon_path = FUNCTION_ICONS.get(function_key, "")
            if function_key == 'about':
                icon_path = "img/about.png"
            
            btn = SideButton(icon_path, text)
            btn.clicked.connect(lambda _, i=idx: self.switch_page(i))
            nav_layout.addWidget(btn)
            self.buttons.append(btn)
        
        nav_layout.addStretch()
        
        if self.buttons:
            self.buttons[0].setChecked(True)
        
        # ---- 右侧功能页 ----
        self.stack = QStackedWidget()
        colors = ["#A3BE8C", "#EBCB8B", "#B48EAD", "#81A1C1", "#D08770", "#BF616A", "#88C0D0"]
        functions = self.get_functions_by_mode()
        
        for idx, (function_key, text) in enumerate(functions):
            color = colors[idx % len(colors)]
            self.stack.addWidget(FunctionPage(text, function_key, color))
        
        # ---- 主布局 ----
        root = QHBoxLayout(self)
        root.addWidget(nav)
        root.addWidget(self.stack, 1)
        root.setContentsMargins(0, 0, 0, 0)
    
    def mode_name(self):
        # return "学校模式" if self.mode == "school" else "家庭模式"
        return "公用模式" if self.mode == "school" else "个人模式"
    
    def get_functions_by_mode(self):
        """根据模式返回不同的功能列表"""
        if self.mode == "school":
            functions = FEATURES['school']['enabled_functions']
            function_list = []
            for func_key in functions:
                func_name = FUNCTION_NAMES.get(func_key, func_key)
                function_list.append((func_key, func_name))
            # 添加关于页面
            function_list.append(('about', '关于'))
            return function_list
        else:  # home mode
            functions = FEATURES['home']['enabled_functions']
            function_list = []
            for func_key in functions:
                func_name = FUNCTION_NAMES.get(func_key, func_key)
                function_list.append((func_key, func_name))
            # 添加关于页面
            function_list.append(('about', '关于'))
            return function_list
    
    def switch_page(self, idx):
        """切换页面"""
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)
        self.current_index = idx
    
    def go_back(self):
        """返回模式选择页面"""
        self.back_requested.emit()
    
    def handle_control_command(self, action):
        """处理控制指令"""
        if action == 'down':  # 下一个（6-0-6）
            new_index = (self.current_index + 1) % len(self.buttons)
            self.switch_page(new_index)
        elif action == 'up':  # 上一个（6-0-5）
            new_index = (self.current_index - 1) % len(self.buttons)
            self.switch_page(new_index)
        elif action == 'confirm':  # 确认选择
            functions = self.get_functions_by_mode()
            if 0 <= self.current_index < len(functions):
                function_key, function_name = functions[self.current_index]
                if function_key != 'about':  # 关于页面不触发功能选择
                    # 🔧 修复：先发送通知提示用户选择了什么功能
                    self.notification_requested.emit("系统通知", f"正在进入{function_name}功能...")
                    
                    # 🔧 修复：使用QTimer延迟发送功能选择信号，确保通知先显示
                    QTimer.singleShot(100, lambda: self.function_selected.emit(function_key))
        elif action == 'back':  # 返回
            self.go_back()

class ModernMainWindow(QWidget):
    """现代化主窗口"""
    
    function_selected = pyqtSignal(str)  # 功能选择信号
    mode_selected = pyqtSignal(str)      # 模式选择信号
    back_to_mode_selection = pyqtSignal()  # 返回模式选择信号
    notification_requested = pyqtSignal(str, str)  # 通知请求信号(title, message)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能学习管理系统")
        
        # 设置窗口为全屏
        from config import WINDOW_CONFIG
        self.setFixedSize(WINDOW_CONFIG['width'], WINDOW_CONFIG['height'])
        
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                background: #434C5E;
                color: #ECEFF4;
            }
        """)
        
        # 主布局（不添加边距）
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建模式选择页面
        self.mode_page = ModeSelectionPage(self)
        self.mode_page.mode_selected.connect(self.mode_selected.emit)
        main_layout.addWidget(self.mode_page)
        
        # 功能选择页面（初始隐藏）
        self.function_widget = None
        
        # ---- 淡入动画 ----
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()
    
    def switch_to_function_page(self, mode):
        """切换到功能选择页面，根据模式选择不同的滑动方向"""
        # 创建功能选择界面
        self.function_widget = FunctionSelectionWidget(mode)
        self.function_widget.function_selected.connect(self.function_selected.emit)
        self.function_widget.back_requested.connect(self.switch_to_mode_selection)
        self.function_widget.notification_requested.connect(self.notification_requested)
        
        # 设置功能选择界面的父组件并定位
        self.function_widget.setParent(self)
        
        # 根据模式选择不同的滑动方向
        if mode == "school":
            # 学校模式：从左向右滑动（功能页面从左边滑入，模式选择页面向右滑出）
            self.function_widget.setGeometry(-self.width(), 0, self.width(), self.height())
            self.function_widget.show()
            
            # 创建动画
            self.slide_anim = QPropertyAnimation(self.mode_page, b"geometry")
            self.slide_anim.setDuration(600)
            self.slide_anim.setStartValue(QRect(0, 0, self.width(), self.height()))
            self.slide_anim.setEndValue(QRect(self.width(), 0, self.width(), self.height()))
            self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)
            
            self.slide_anim2 = QPropertyAnimation(self.function_widget, b"geometry")
            self.slide_anim2.setDuration(600)
            self.slide_anim2.setStartValue(QRect(-self.width(), 0, self.width(), self.height()))
            self.slide_anim2.setEndValue(QRect(0, 0, self.width(), self.height()))
            self.slide_anim2.setEasingCurve(QEasingCurve.OutCubic)
            
        else:
            # 家庭模式：从右向左滑动（功能页面从右边滑入，模式选择页面向左滑出）
            self.function_widget.setGeometry(self.width(), 0, self.width(), self.height())
            self.function_widget.show()
            
            # 创建动画
            self.slide_anim = QPropertyAnimation(self.mode_page, b"geometry")
            self.slide_anim.setDuration(600)
            self.slide_anim.setStartValue(QRect(0, 0, self.width(), self.height()))
            self.slide_anim.setEndValue(QRect(-self.width(), 0, self.width(), self.height()))
            self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)
            
            self.slide_anim2 = QPropertyAnimation(self.function_widget, b"geometry")
            self.slide_anim2.setDuration(600)
            self.slide_anim2.setStartValue(QRect(self.width(), 0, self.width(), self.height()))
            self.slide_anim2.setEndValue(QRect(0, 0, self.width(), self.height()))
            self.slide_anim2.setEasingCurve(QEasingCurve.OutCubic)
        
        # 动画完成后隐藏模式选择页面
        self.slide_anim.finished.connect(lambda: self.mode_page.hide())
        
        # 开始动画
        self.slide_anim.start()
        self.slide_anim2.start()
    
    def switch_to_mode_selection(self):
        """返回模式选择页面，根据模式使用不同的返回动画方向"""
        if not self.function_widget:
            return
        
        # 显示模式选择页面
        self.mode_page.show()
        
        # 根据模式选择不同的返回动画方向
        if self.function_widget.mode == "school":
            # 学校模式：从右向左返回（功能页面向左滑出，模式选择页面从右边滑入）
            self.return_anim = QPropertyAnimation(self.mode_page, b"geometry")
            self.return_anim.setDuration(600)
            self.return_anim.setStartValue(QRect(self.width(), 0, self.width(), self.height()))
            self.return_anim.setEndValue(QRect(0, 0, self.width(), self.height()))
            self.return_anim.setEasingCurve(QEasingCurve.OutCubic)
            
            self.return_anim2 = QPropertyAnimation(self.function_widget, b"geometry")
            self.return_anim2.setDuration(600)
            self.return_anim2.setStartValue(QRect(0, 0, self.width(), self.height()))
            self.return_anim2.setEndValue(QRect(-self.width(), 0, self.width(), self.height()))
            self.return_anim2.setEasingCurve(QEasingCurve.OutCubic)
            
        else:
            # 家庭模式：从左向右返回（功能页面向右滑出，模式选择页面从左边滑入）
            self.return_anim = QPropertyAnimation(self.mode_page, b"geometry")
            self.return_anim.setDuration(600)
            self.return_anim.setStartValue(QRect(-self.width(), 0, self.width(), self.height()))
            self.return_anim.setEndValue(QRect(0, 0, self.width(), self.height()))
            self.return_anim.setEasingCurve(QEasingCurve.OutCubic)
            
            self.return_anim2 = QPropertyAnimation(self.function_widget, b"geometry")
            self.return_anim2.setDuration(600)
            self.return_anim2.setStartValue(QRect(0, 0, self.width(), self.height()))
            self.return_anim2.setEndValue(QRect(self.width(), 0, self.width(), self.height()))
            self.return_anim2.setEasingCurve(QEasingCurve.OutCubic)
        
        # 动画完成后移除功能页面
        self.return_anim2.finished.connect(self.remove_function_widget)
        
        # 发射返回信号
        self.back_to_mode_selection.emit()
        
        # 开始动画
        self.return_anim.start()
        self.return_anim2.start()
    
    def remove_function_widget(self):
        """移除功能选择界面"""
        if self.function_widget:
            self.function_widget.deleteLater()
            self.function_widget = None
    
    def handle_control_command(self, action):
        """处理控制指令"""
        if self.function_widget and self.function_widget.isVisible():
            # 如果功能选择界面可见，传递给功能选择界面处理
            self.function_widget.handle_control_command(action)
        else:
            # 模式选择界面的控制逻辑
            self.mode_page.handle_control_command(action) 