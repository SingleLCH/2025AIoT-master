# -*- coding: utf-8 -*-
"""
会议页面
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class MeetingPage(QWidget):
    """会议页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 请求返回
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_room_id = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                color: #D8DEE9;
            }
            QLabel {
                color: #D8DEE9;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # 标题
        title_label = QLabel("视频会议")
        title_label.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #88C0D0; margin-bottom: 20px;")
        layout.addWidget(title_label)
        
        # 状态显示区域
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border: 2px solid #5E81AC;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        self.status_frame.setFixedSize(600, 300)
        
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignCenter)
        status_layout.setSpacing(20)
        
        # 房间号显示
        self.room_label = QLabel("房间号: ")
        self.room_label.setFont(QFont("Microsoft YaHei", 16))
        self.room_label.setAlignment(Qt.AlignCenter)
        self.room_label.setStyleSheet("color: #81A1C1;")
        status_layout.addWidget(self.room_label)
        
        # 状态显示
        self.status_label = QLabel("准备中...")
        self.status_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #EBCB8B;")
        status_layout.addWidget(self.status_label)
        
        # 提示信息
        self.hint_label = QLabel("")
        self.hint_label.setFont(QFont("Microsoft YaHei", 14))
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #A3BE8C;")
        self.hint_label.setWordWrap(True)
        status_layout.addWidget(self.hint_label)
        
        self.status_frame.setLayout(status_layout)
        layout.addWidget(self.status_frame)
        
        # 控制提示
        control_label = QLabel("使用手势 6-0-2 退出会议")
        control_label.setFont(QFont("Microsoft YaHei", 12))
        control_label.setAlignment(Qt.AlignCenter)
        control_label.setStyleSheet("color: #D08770; margin-top: 20px;")
        layout.addWidget(control_label)
        
        self.setLayout(layout)
        
    def start_meeting(self, room_id):
        """开始会议"""
        logger.info(f"开始会议，房间号: {room_id}")
        self.current_room_id = room_id
        self.room_label.setText(f"房间号: {room_id}")
        self.status_label.setText("正在进入会议...")
        self.hint_label.setText("正在启动浏览器并加入会议房间\n请稍候...")
        
        # 设置定时器，3秒后显示会议中状态
        QTimer.singleShot(3000, self.show_meeting_active)
        
    def show_meeting_active(self):
        """显示会议活跃状态"""
        self.status_label.setText("会议进行中")
        self.hint_label.setText("您已成功加入会议\n请在浏览器中进行视频通话")
        self.status_label.setStyleSheet("color: #A3BE8C;")
        
    def exit_meeting(self):
        """退出会议"""
        logger.info("退出会议")
        self.status_label.setText("正在退出会议...")
        self.hint_label.setText("正在关闭会议连接...")
        self.status_label.setStyleSheet("color: #D08770;")
        
        # 设置定时器，2秒后发送返回信号
        QTimer.singleShot(2000, self.back_requested.emit)
        
    def handle_control_command(self, action):
        """处理控制指令"""
        logger.info(f"会议页面收到控制指令: {action}")
        
        if action == "exit" or action == "back":
            # 6-0-2 退出会议
            self.exit_meeting()
        else:
            logger.info(f"会议页面不处理指令: {action}")
            
    def get_current_room_id(self):
        """获取当前房间号"""
        return self.current_room_id
        
    def cleanup(self):
        """清理资源"""
        logger.info("清理会议页面资源")
        self.current_room_id = None 