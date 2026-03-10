# -*- coding: utf-8 -*-
"""
设置页面模块
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QSlider, QFrame, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QFont
import logging
from config import GESTURE_CONFIG, GESTURE_COMMANDS, SETTINGS_DEFAULT_VALUES

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """设置页面组件"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    send_esp32_control_command = pyqtSignal(str)  # 发送ESP32控制指令信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置初始值（从config文件读取）
        self.volume = SETTINGS_DEFAULT_VALUES['volume']           # 音量初始值
        self.brightness = SETTINGS_DEFAULT_VALUES['brightness']   # 亮度初始值
        self.desk_height = SETTINGS_DEFAULT_VALUES['desk_height'] # 桌子高度初始值
        
        # 状态管理
        self.current_mode = 'normal'  # 当前模式：'normal'（常规模式）
        self.selected_variable = 0    # 当前选中的变量索引：0=音量，1=亮度，2=桌子高度
        self.variables = ['volume', 'brightness', 'desk_height']  # 变量列表
        
        # 桌子高度确认机制
        self.pending_desk_height = None  # 待发送的桌子高度档位
        
        # 控制组件列表
        self.control_widgets = []
        
        self.setup_ui()
        self.update_selection_ui()
        
    def setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(30)
        
        # 标题和状态显示
        title_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #FFF;
            }
        """)
        
        # 模式状态显示
        self.mode_label = QLabel("常规模式")
        self.mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mode_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666;
                padding: 5px 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.mode_label)
        
        # 控制区域
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(40)
        
        # 音量控制
        self.volume_control = self.create_slider_control(
            "音量", "img/volume.png", 0, 100, self.volume, self.on_volume_changed
        )
        
        # 亮度控制
        self.brightness_control = self.create_slider_control(
            "亮度", "img/light.png", 0, 100, self.brightness, self.on_brightness_changed
        )
        
        # 桌子高度控制
        self.desk_height_control = self.create_level_control(
            "桌子高度", "img/height.png", self.desk_height, self.on_desk_height_changed
        )
        
        # 保存控制组件到列表
        self.control_widgets = [
            self.volume_control,
            self.brightness_control,
            self.desk_height_control
        ]
        
        controls_layout.addWidget(self.volume_control)
        controls_layout.addWidget(self.brightness_control)
        controls_layout.addWidget(self.desk_height_control)
        
        # 操作提示
        self.hint_label = QLabel("上下滑动选择变量，左右滑动调节数值，或使用7/8指令增减当前变量")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                color: #666;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
        """)
        
        # 添加到主布局
        main_layout.addLayout(title_layout)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.hint_label)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # 设置页面样式
        self.setStyleSheet("""
            QWidget {
                background-color: #434C5E;
                color: #ECEFF4;
            }
        """)
        
    def create_slider_control(self, name, icon_path, min_val, max_val, current_val, callback):
        """创建滑块控制组件"""
        # 主容器
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                padding: 0px;
                border: 3px solid transparent;
                color: #ECEFF4;
            }
        """)
        
        # 布局
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题行（图标 + 名称 + 数值）
        title_layout = QHBoxLayout()
        title_layout.setSpacing(15)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        try:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                # 根据不同的控制类型设置不同的默认图标
                if "音量" in name:
                    icon_label.setText("🔊")
                elif "亮度" in name:
                    icon_label.setText("💡")
                else:
                    icon_label.setText("🔧")
                icon_label.setStyleSheet("""
                    QLabel {
                        font-size: 24px;
                        background: transparent;
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }
                """)
        except:
            # 根据不同的控制类型设置不同的默认图标
            if "音量" in name:
                icon_label.setText("🔊")
            elif "亮度" in name:
                icon_label.setText("💡")
            else:
                icon_label.setText("🔧")
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 24px;
                    background: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
        
        # 名称
        name_label = QLabel(name)
        name_label.setFixedHeight(40)
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #FFF;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 数值显示
        value_label = QLabel(f"{current_val}%")
        value_label.setFixedHeight(40)
        value_label.setMinimumWidth(60)
        value_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                color: #FFF;
                font-weight: bold;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(name_label)
        title_layout.addStretch()
        title_layout.addWidget(value_label)
        
        # 滑块
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(current_val)
        slider.setStyleSheet("""
            QSlider {
                background: transparent; /* 新增，设置滑块控件自身背景透明 */
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                height: 8px;
                background: #f0f0f0;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007bff;
                border: 1px solid #007bff;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #007bff;
                border-radius: 4px;
            }
        """)
        
        # 连接信号
        slider.valueChanged.connect(lambda val: self.update_value_label(value_label, val, "%"))
        slider.valueChanged.connect(callback)
        
        # 保存引用
        setattr(container, 'slider', slider)
        setattr(container, 'value_label', value_label)
        
        layout.addLayout(title_layout)
        layout.addWidget(slider)
        
        return container
        
    def create_level_control(self, name, icon_path, current_level, callback):
        """创建档位控制组件"""
        # 主容器
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                padding: 0px;
                border: 3px solid transparent;
                color: #ECEFF4;
            }
        """)
        
        # 布局
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题行（图标 + 名称 + 档位）
        title_layout = QHBoxLayout()
        title_layout.setSpacing(15)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        try:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logger.info(f"成功加载图标: {icon_path}")
            else:
                icon_label.setText("📏")
                icon_label.setStyleSheet("""
                    QLabel {
                        font-size: 24px;
                        background: transparent;
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }
                """)
                logger.warning(f"图标加载失败，使用文本图标: {icon_path}")
        except Exception as e:
            icon_label.setText("📏")
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 24px;
                    background: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
            logger.error(f"图标加载异常: {icon_path}, 错误: {e}")
        
        # 名称
        name_label = QLabel(name)
        name_label.setFixedHeight(40)
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #FFF;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 档位显示
        level_label = QLabel(f"{current_level}档")
        level_label.setFixedHeight(40)
        level_label.setMinimumWidth(60)
        level_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        level_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                color: #FFF;
                font-weight: bold;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(name_label)
        title_layout.addStretch()
        title_layout.addWidget(level_label)
        
        # 档位按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(30)
        
        # 添加左侧弹性空间实现居中
        buttons_layout.addStretch()
        
        # 创建3个档位按钮
        buttons = []
        for i in range(1, 4):
            button = QPushButton(f"{i}档")
            # 设置按钮最小宽度和固定高度，让按钮更宽
            button.setMinimumWidth(200)
            button.setFixedHeight(80)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setCheckable(True)
            button.setChecked(i == current_level)
            
            # 设置按钮样式
            if i == current_level:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 24px;
                        font-weight: bold;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #f8f9fa;
                        color: #333;
                        border: 2px solid #ddd;
                        border-radius: 5px;
                        font-size: 24px;
                    }
                    QPushButton:hover {
                        background-color: #e9ecef;
                    }
                """)
            
            # 连接信号
            button.clicked.connect(lambda checked, level=i: self.set_desk_level(level, callback))
            buttons.append(button)
        
        # 添加按钮到布局
        for button in buttons:
            buttons_layout.addWidget(button)
        
        # 添加右侧弹性空间实现居中
        buttons_layout.addStretch()
        
        # 保存引用
        setattr(container, 'buttons', buttons)
        setattr(container, 'level_label', level_label)
        
        layout.addLayout(title_layout)
        layout.addLayout(buttons_layout)
        
        return container
        
    def update_value_label(self, label, value, suffix=""):
        """更新数值标签"""
        label.setText(f"{value}{suffix}")
        
    def set_desk_level(self, level, callback):
        """设置桌子档位"""
        # 更新按钮状态
        buttons = self.desk_height_control.buttons
        for i, button in enumerate(buttons, 1):
            if i == level:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 16px;
                        font-weight: bold;
                    }
                """)
                button.setChecked(True)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #f8f9fa;
                        color: #333;
                        border: 2px solid #ddd;
                        border-radius: 5px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background-color: #e9ecef;
                    }
                """)
                button.setChecked(False)
        
        # 更新档位显示
        self.desk_height_control.level_label.setText(f"{level}档")
        
        # 调用回调
        callback(level)
        
    def on_volume_changed(self, value):
        """音量变化处理"""
        self.volume = value
        logger.info(f"音量设置为: {value}")
        
        # 播放音量调整音效
        self.play_volume_sound()
        
    def on_brightness_changed(self, value):
        """亮度变化处理"""
        self.brightness = value
        logger.info(f"亮度设置为: {value}")
        
    def on_desk_height_changed(self, level):
        """桌子高度变化处理"""
        self.desk_height = level
        logger.info(f"桌子高度设置为: {level}档")
        
    def play_volume_sound(self):
        """播放音量调整音效（异步播放，不阻塞UI）"""
        try:
            import os
            import subprocess
            
            # 检查音效文件是否存在
            sound_file = "yinliang.wav"
            if os.path.exists(sound_file):
                # 使用aplay通过ALSA播放音效文件（异步）
                logger.info(f"播放音量调整音效: {sound_file}")
                try:
                    # 使用ALSA异步播放，不阻塞UI线程
                    cmd = ['aplay', '-D', 'hw:1,0', sound_file]
                    # 使用Popen异步启动进程，立即返回
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info("音量调整音效播放已启动（异步）")
                except Exception as aplay_e:
                    logger.error(f"ALSA播放失败: {aplay_e}")
                    # 备用方案：使用系统默认播放（异步）
                    try:
                        subprocess.Popen(['aplay', sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        logger.info("音量调整音效播放已启动（备用方案）")
                    except:
                        logger.warning("所有音效播放方案均失败")
            else:
                logger.warning(f"音效文件不存在: {sound_file}")
                
        except Exception as e:
            logger.error(f"播放音量调整音效失败: {e}")
        
    def update_selection_ui(self):
        """更新选择状态的UI显示"""
        for i, widget in enumerate(self.control_widgets):
            if i == self.selected_variable:
                # 选中状态：绿色边框
                widget.setStyleSheet("""
                    QFrame {
                        background-color: #3B4252;
                        border-radius: 10px;
                        padding: 0px;
                        border: 3px solid #28a745;
                        color: #ECEFF4;
                    }
                """)
            else:
                # 非选中状态：默认样式
                widget.setStyleSheet("""
                    QFrame {
                        background-color: #3B4252;
                        border-radius: 10px;
                        padding: 0px;
                        border: 3px solid transparent;
                        color: #ECEFF4;
                    }
                """)
        
        # 更新模式显示
        self.mode_label.setText("常规模式")
        self.mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mode_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666;
                padding: 5px 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)
        self.hint_label.setText("上下滑动选择变量，点击左右边缘调节大小")
    
    def select_previous_variable(self):
        """选择上一个变量"""
        self.selected_variable = (self.selected_variable - 1) % len(self.variables)
        self.update_selection_ui()
        logger.info(f"选择变量: {self.variables[self.selected_variable]}")
        
    def select_next_variable(self):
        """选择下一个变量"""
        self.selected_variable = (self.selected_variable + 1) % len(self.variables)
        self.update_selection_ui()
        logger.info(f"选择变量: {self.variables[self.selected_variable]}")
        
    def adjust_current_variable(self, direction):
        """调节当前选中的变量"""
        current_var = self.variables[self.selected_variable]
        
        if current_var == 'volume':
            delta = GESTURE_CONFIG['delta_volume']
            if direction == 'right':
                new_value = min(100, self.volume + delta)
            else:  # left
                new_value = max(0, self.volume - delta)
            self.set_volume(new_value)
            
        elif current_var == 'brightness':
            delta = GESTURE_CONFIG['delta_brightness']
            if direction == 'right':
                new_value = min(100, self.brightness + delta)
            else:  # left
                new_value = max(0, self.brightness - delta)
            self.set_brightness(new_value)
            
        elif current_var == 'desk_height':
            delta = GESTURE_CONFIG['delta_desk_height']
            if direction == 'right':
                new_value = min(3, self.desk_height + delta)
            else:  # left
                new_value = max(1, self.desk_height - delta)
            self.set_desk_height(new_value)
    

    
    def set_volume(self, value):
        """设置音量"""
        value = max(0, min(100, value))
        self.volume = value
        self.volume_control.slider.setValue(value)
        logger.info(f"音量已设置为: {value}")
        
        # 不在这里播放音效，让slider的valueChanged信号处理
        
        # 发送ESP32控制指令
        self.send_esp32_control_command.emit(f"4-0-{value}")
        
    def set_brightness(self, value):
        """设置亮度"""
        value = max(0, min(100, value))
        self.brightness = value
        self.brightness_control.slider.setValue(value)
        logger.info(f"亮度已设置为: {value}")
        
        # 发送ESP32控制指令
        self.send_esp32_control_command.emit(f"7-0-{value}")
        
    def set_desk_height(self, level):
        """设置桌子高度"""
        level = max(1, min(3, level))
        self.desk_height = level
        self.set_desk_level(level, self.on_desk_height_changed)
        logger.info(f"桌子高度已设置为: {level}档")
        
        # 保存待发送的桌子高度，等待6-0-1确认后再发送
        self.pending_desk_height = level
        logger.info(f"桌子高度指令已准备，等待确认: 3-{level}-0")
          
    
    @pyqtSlot(str)
    def handle_gesture_command(self, command):
        """处理手势指令"""
        logger.info(f"设置页面接收到手势指令: {command}")
        
        try:
            # 解析指令
            if command == '6-0-1':  # 确认
                # 检查是否有待发送的桌子高度指令
                if self.pending_desk_height is not None:
                    # 发送ESP32桌子高度控制指令
                    self.send_esp32_control_command.emit(f"3-{self.pending_desk_height}-0")
                    logger.info(f"收到确认，发送桌子高度指令: 3-{self.pending_desk_height}-0")
                    self.pending_desk_height = None  # 清除待发送状态
                else:
                    logger.info("确认指令已接收，但没有待发送的桌子高度指令")
                    
            elif command == '6-0-2':  # 返回
                self.back_requested.emit()
                    
            elif command == '6-0-3':  # 右滑
                self.adjust_current_variable('right')
                    
            elif command == '6-0-4':  # 左滑
                self.adjust_current_variable('left')
                    
            elif command == '6-0-5':  # 上滑
                self.select_previous_variable()
                    
            elif command == '6-0-6':  # 下滑
                self.select_next_variable()
                    
            elif command == '6-0-7':  # 增加DELTA
                self.adjust_current_variable('right')
                    
            elif command == '6-0-8':  # 减少DELTA
                self.adjust_current_variable('left')
                        
        except Exception as e:
            logger.error(f"处理手势指令失败: {e}")
    
    @pyqtSlot(str)
    def handle_mqtt_command(self, command):
        """处理MQTT指令（保留兼容性）"""
        logger.info(f"设置页面接收到MQTT指令: {command}")
        
        # 处理普通控制指令
        if command == 'back':
            logger.info("处理返回指令")
            self.back_requested.emit()
            return
        
        try:
            parts = command.split('-')
            if len(parts) != 3:
                return
                
            category = int(parts[0])
            param1 = int(parts[1])
            param2 = int(parts[2])
            
            if category == 4:  # 音量控制
                self.handle_volume_command(param1, param2)
            elif category == 7:  # 亮度控制
                self.handle_brightness_command(param1, param2)
            elif category == 3:  # 桌子高度控制
                self.handle_desk_height_command(param1, param2)
                
        except ValueError:
            logger.warning(f"无效的MQTT指令格式: {command}")
            
    def handle_volume_command(self, param1, param2):
        """处理音量控制指令"""
        if param1 == 0:  # 设置音量为param2
            self.set_volume(param2)
        elif param1 == 2:  # 音量+10
            new_volume = min(100, self.volume + 10)
            self.set_volume(new_volume)
        elif param1 == 3:  # 音量-10
            new_volume = max(0, self.volume - 10)
            self.set_volume(new_volume)
            
    def handle_brightness_command(self, param1, param2):
        """处理亮度控制指令"""
        if param1 == 0 and param2 == 0:  # 关闭
            self.set_brightness(0)
        elif param1 == 0 and param2 == 1:  # 打开（设置为50）
            self.set_brightness(50)
        elif param1 == 1:  # 设置亮度为param2
            self.set_brightness(param2)
            
    def handle_desk_height_command(self, param1, param2):
        """处理桌子高度控制指令"""
        if param1 == 0:  # 1档（最低）
            self.set_desk_height(1)
        elif param1 == 1:  # 2档（中间）
            self.set_desk_height(2)
        elif param1 == 2:  # 3档（最高）
            self.set_desk_height(3) 