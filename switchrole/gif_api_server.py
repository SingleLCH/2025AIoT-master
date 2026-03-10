#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立GIF播放器API服务
按照用户设计思路：GIF一直播放，通过API接口切换状态
"""

import sys
import os
import time
import threading
import json
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QMovie

class GifApiSignals(QObject):
    """GIF API信号"""
    change_state = pyqtSignal(str)
    change_emotion = pyqtSignal(str)

class GifApiServer(QWidget):
    """独立GIF播放器API服务"""
    
    def __init__(self):
        super().__init__()
        self.current_gif = "daiji.gif"
        self.current_state = "待机"
        self.movie = None
        self.api_signals = GifApiSignals()
        
        # GIF状态映射
        self.state_gif_map = {
            "idle": "daiji.gif",        # 待机
            "listening": "lingting.gif", # 聆听
            "thinking": "mimang.gif",    # 思考
            "speaking": "kaixin.gif",    # 说话（默认开心）
            "sleeping": "shuijiao.gif"   # 休眠
        }
        
        # 情感GIF映射
        self.emotion_gif_map = {
            "happy": "kaixin.gif",      # 开心
            "angry": "shengqi.gif",     # 生气
            "sad": "nanguo.gif",        # 难过
            "shy": "haixiu.gif",        # 害羞
            "surprised": "tiaopi.gif",  # 惊讶/调皮
            "confused": "mimang.gif",   # 困惑
            "bored": "wuliao.gif"       # 无聊
        }
        
        # 中文状态映射
        self.chinese_state_map = {
            "待机": "idle",
            "聆听": "listening", 
            "思考": "thinking",
            "说话": "speaking",
            "休眠": "sleeping"
        }
        
        # 中文情感映射
        self.chinese_emotion_map = {
            "开心": "happy",
            "生气": "angry",
            "难过": "sad", 
            "害羞": "shy",
            "惊讶": "surprised",
            "困惑": "confused",
            "无聊": "bored"
        }
        
        self.initUI()
        self.connectSignals()
        self.startGif()
        
    def initUI(self):
        """初始化界面"""
        # 设置窗口
        self.setWindowTitle("小新GIF表情 - 800x480")
        self.setFixedSize(800, 480)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # GIF显示区域
        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #333;
                border-radius: 10px;
            }
        """)
        self.gif_label.setFixedSize(760, 400)
        
        # 状态显示
        self.status_label = QLabel("小新待机中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #333;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.status_label.setFixedHeight(40)
        
        layout.addWidget(self.gif_label)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        
        # 窗口居中
        self.centerWindow()
        
    def centerWindow(self):
        """窗口居中"""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def connectSignals(self):
        """连接信号"""
        self.api_signals.change_state.connect(self.handleStateChange)
        self.api_signals.change_emotion.connect(self.handleEmotionChange)
        
    def startGif(self):
        """开始播放GIF（默认待机状态）"""
        self.loadGif("daiji.gif")
        
    def loadGif(self, gif_filename):
        """加载并播放GIF"""
        gif_path = os.path.join("gif", gif_filename)
        
        if not os.path.exists(gif_path):
            print(f"⚠️ GIF文件不存在: {gif_path}")
            self.gif_label.setText(f"GIF文件不存在:\n{gif_filename}")
            return False
            
        try:
            if self.movie:
                self.movie.stop()
                
            self.movie = QMovie(gif_path)
            self.gif_label.setMovie(self.movie)
            self.movie.start()
            
            self.current_gif = gif_filename
            print(f"🎬 播放GIF: {gif_filename}")
            return True
            
        except Exception as e:
            print(f"❌ 加载GIF失败: {e}")
            return False
    
    def handleStateChange(self, state):
        """处理状态切换"""
        print(f"🔄 状态切换: {state}")
        
        # 支持中文和英文状态
        if state in self.chinese_state_map:
            state = self.chinese_state_map[state]
            
        if state in self.state_gif_map:
            gif_file = self.state_gif_map[state]
            if self.loadGif(gif_file):
                self.current_state = state
                self.updateStatusText()
        else:
            print(f"⚠️ 未知状态: {state}")
    
    def handleEmotionChange(self, emotion):
        """处理情感切换"""
        print(f"🎭 情感切换: {emotion}")
        
        # 支持中文和英文情感
        if emotion in self.chinese_emotion_map:
            emotion = self.chinese_emotion_map[emotion]
            
        if emotion in self.emotion_gif_map:
            gif_file = self.emotion_gif_map[emotion]
            if self.loadGif(gif_file):
                self.updateStatusText(f"表达{emotion}情感")
        else:
            print(f"⚠️ 未知情感: {emotion}")
    
    def updateStatusText(self, custom_text=None):
        """更新状态文本"""
        if custom_text:
            self.status_label.setText(f"小新正在{custom_text}")
        else:
            state_texts = {
                "idle": "待机中...",
                "listening": "认真聆听 👂",
                "thinking": "努力思考 🤔", 
                "speaking": "开心回答 💬",
                "sleeping": "休息中 😴"
            }
            text = state_texts.get(self.current_state, f"{self.current_state}中...")
            self.status_label.setText(f"小新{text}")

# 全局API服务实例
_gif_api_server = None

def start_gif_api_server():
    """启动GIF API服务"""
    global _gif_api_server
    
    try:
        app = QApplication(sys.argv)
        
        _gif_api_server = GifApiServer()
        _gif_api_server.show()
        
        print("✅ GIF API服务启动成功")
        print(f"📏 窗口大小: {_gif_api_server.size()}")
        print(f"📍 窗口位置: {_gif_api_server.pos()}")
        
        return _gif_api_server, app
        
    except Exception as e:
        print(f"❌ GIF API服务启动失败: {e}")
        return None, None

def get_gif_api_server():
    """获取GIF API服务实例"""
    return _gif_api_server

# =================
# API接口函数
# =================

def api_set_state(state):
    """API: 设置状态
    
    Args:
        state: 状态名称
            - idle/待机: 待机状态
            - listening/聆听: 聆听状态  
            - thinking/思考: 思考状态
            - speaking/说话: 说话状态
            - sleeping/休眠: 休眠状态
    """
    server = get_gif_api_server()
    if server:
        server.api_signals.change_state.emit(state)
        print(f"📡 API调用 - 设置状态: {state}")
    else:
        print("⚠️ GIF服务未启动")

def api_set_emotion(emotion):
    """API: 设置情感
    
    Args:
        emotion: 情感名称
            - happy/开心: 开心表情
            - angry/生气: 生气表情
            - sad/难过: 难过表情
            - shy/害羞: 害羞表情
            - surprised/惊讶: 惊讶表情
            - confused/困惑: 困惑表情
            - bored/无聊: 无聊表情
    """
    server = get_gif_api_server()
    if server:
        server.api_signals.change_emotion.emit(emotion)
        print(f"📡 API调用 - 设置情感: {emotion}")
    else:
        print("⚠️ GIF服务未启动")

def api_get_current_state():
    """API: 获取当前状态"""
    server = get_gif_api_server()
    if server:
        return {
            "current_gif": server.current_gif,
            "current_state": server.current_state
        }
    return None

# =================
# 测试函数
# =================

def test_api_calls():
    """测试API调用"""
    print("🧪 开始测试API调用...")
    
    test_sequence = [
        ("设置待机状态", lambda: api_set_state("idle"), 2),
        ("设置聆听状态", lambda: api_set_state("listening"), 2),
        ("设置思考状态", lambda: api_set_state("thinking"), 2),
        ("表达开心情感", lambda: api_set_emotion("happy"), 2),
        ("表达生气情感", lambda: api_set_emotion("angry"), 2),
        ("表达害羞情感", lambda: api_set_emotion("shy"), 2),
        ("返回待机状态", lambda: api_set_state("idle"), 2),
    ]
    
    current_index = 0
    
    def run_next_test():
        nonlocal current_index
        
        if current_index >= len(test_sequence):
            print("🎉 API测试完成!")
            return
            
        desc, action, duration = test_sequence[current_index]
        print(f"🎭 执行: {desc}")
        
        try:
            action()
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            
        current_index += 1
        QTimer.singleShot(duration * 1000, run_next_test)
    
    # 延迟开始测试
    QTimer.singleShot(2000, run_next_test)

def main():
    """主函数"""
    print("🎬 启动独立GIF播放器API服务")
    print("=" * 50)
    
    # 启动服务
    server, app = start_gif_api_server()
    
    if not server:
        print("❌ 服务启动失败")
        return
    
    # 如果是直接运行，启动测试
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_api_calls()
    
    # 运行Qt事件循环
    print("🔄 GIF服务运行中...")
    print("💡 现在可以通过API调用来控制GIF切换")
    app.exec_()

if __name__ == "__main__":
    main() 