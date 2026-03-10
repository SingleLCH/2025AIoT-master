# -*- coding: utf-8 -*-
"""
TODO步骤组件
可复用的操作流程展示组件
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class TodoStepWidget(QWidget):
    """单个TODO步骤组件"""
    
    def __init__(self, step_number: int, title: str, description: str, parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_completed = False
        self.is_current = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # 步骤图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                color: white;
            }
        """)
        layout.addWidget(self.icon_label)
        
        # 步骤内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #000000;")
        content_layout.addWidget(self.title_label)
        
        self.desc_label = QLabel(self.description)
        self.desc_label.setFont(QFont("微软雅黑", 14))
        self.desc_label.setStyleSheet("color: #000000;")
        content_layout.addWidget(self.desc_label)
        
        layout.addLayout(content_layout, 1)
        
        self.setLayout(layout)
        self.update_status()
    
    def set_completed(self):
        """设置为已完成状态"""
        self.is_completed = True
        self.is_current = False
        self.update_status()
    
    def set_current(self):
        """设置为当前步骤"""
        self.is_current = True
        self.is_completed = False
        self.update_status()
    
    def set_pending(self):
        """设置为待执行状态"""
        self.is_current = False
        self.is_completed = False
        self.update_status()
    
    def update_status(self):
        """更新状态显示"""
        if self.is_completed:
            # 已完成：绿色背景，对号图标
            self.icon_label.setText("✓")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #27ae60;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                }
            """)
            self.title_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.setStyleSheet("QWidget { background-color: #f8fff8; border-left: 4px solid #27ae60; }")
            
        elif self.is_current:
            # 当前步骤：蓝色背景，数字图标
            self.icon_label.setText(str(self.step_number))
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                }
            """)
            self.title_label.setStyleSheet("color: #3498db; font-weight: bold;")
            self.setStyleSheet("QWidget { background-color: #f8fbff; border-left: 4px solid #3498db; }")
            
        else:
            # 待执行：灰色背景，空心圆图标
            self.icon_label.setText("○")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #95a5a6;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                }
            """)
            self.title_label.setStyleSheet("color: #95a5a6;")
            self.setStyleSheet("QWidget { background-color: #f8f9fa; border-left: 4px solid #95a5a6; }")


class TodoFlowPanel(QWidget):
    """TODO流程面板 - 包含标题和步骤列表"""
    
    def __init__(self, title: str, steps_data: list, parent=None):
        super().__init__(parent)
        self.title = title
        self.steps_data = steps_data
        self.step_widgets = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #dee2e6;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 8px;
                border-left: 6px solid #9b59b6;
            }
        """)
        layout.addWidget(title_label)
        
        # TODO步骤
        for step_num, title, desc in self.steps_data:
            step_widget = TodoStepWidget(step_num, title, desc)
            step_widget.set_pending()  # 初始状态为待执行
            self.step_widgets.append(step_widget)
            layout.addWidget(step_widget)
        
        # 状态显示
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #27ae60;
                padding: 20px;
                background-color: #d5f4e6;
                border-radius: 8px;
                border: 2px solid #27ae60;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_status(self, message: str, color: str = "#27ae60"):  
        """更新状态显示"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                padding: 20px;
                background-color: #d5f4e6;
                border-radius: 8px;
                border: 2px solid {color};
            }}
        """)
    
    def set_step_completed(self, step_number: int):
        """设置步骤为已完成"""
        if 1 <= step_number <= len(self.step_widgets):
            self.step_widgets[step_number - 1].set_completed()
            
            # 设置下一步为当前步骤
            if step_number < len(self.step_widgets):
                self.step_widgets[step_number].set_current()
    
    def set_step_current(self, step_number: int):
        """设置当前步骤"""
        if 1 <= step_number <= len(self.step_widgets):
            self.step_widgets[step_number - 1].set_current()
    
    def reset_all_steps(self):
        """重置所有步骤"""
        for step_widget in self.step_widgets:
            step_widget.set_pending() 