#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版GIF API客户端
使用threading代替multiprocessing，避免Windows序列化问题
按照用户设计思路：GIF独立运行，通过API控制切换
"""

import os
import sys
import time
import threading
import queue
from PyQt5.QtWidgets import QApplication

# 全局变量
_gif_server = None
_gif_app = None
_gif_thread = None
_command_queue = queue.Queue()
_is_running = False

def start_gif_service():
    """启动GIF服务（使用threading）"""
    global _gif_server, _gif_app, _gif_thread, _is_running
    
    if _is_running:
        print("⚠️ GIF服务已经在运行")
        return True
    
    try:
        print("🚀 启动简化版GIF API服务...")
        
        # 启动GIF服务线程
        _gif_thread = threading.Thread(target=_run_gif_server, daemon=True)
        _gif_thread.start()
        
        # 等待服务启动
        time.sleep(3)
        
        if _is_running:
            print("✅ GIF API服务启动成功")
            return True
        else:
            print("❌ GIF API服务启动超时")
            return False
            
    except Exception as e:
        print(f"❌ 启动GIF服务失败: {e}")
        return False

def _run_gif_server():
    """在独立线程中运行GIF服务器"""
    global _gif_server, _gif_app, _is_running
    
    try:
        # 创建QApplication
        _gif_app = QApplication(sys.argv)
        
        # 导入并创建GIF服务器
        from gif_api_server import GifApiServer
        _gif_server = GifApiServer()
        _gif_server.show()
        
        print("✅ GIF服务器窗口已显示")
        _is_running = True
        
        # 启动命令处理定时器
        from PyQt5.QtCore import QTimer
        command_timer = QTimer()
        command_timer.timeout.connect(_process_commands)
        command_timer.start(100)  # 每100ms检查一次命令队列
        
        print("🔄 GIF服务器事件循环启动")
        # 运行Qt事件循环
        _gif_app.exec_()
        
    except Exception as e:
        print(f"❌ GIF服务器线程异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _is_running = False

def _process_commands():
    """处理命令队列"""
    global _gif_server
    
    try:
        while not _command_queue.empty():
            command = _command_queue.get_nowait()
            if _gif_server:
                cmd_type = command.get('type')
                cmd_data = command.get('data')
                
                if cmd_type == 'set_state':
                    _gif_server.api_signals.change_state.emit(cmd_data)
                elif cmd_type == 'set_emotion':
                    _gif_server.api_signals.change_emotion.emit(cmd_data)
                    
    except queue.Empty:
        pass
    except Exception as e:
        print(f"❌ 处理命令失败: {e}")

def _send_command(cmd_type, data):
    """发送命令到GIF服务器"""
    if not _is_running:
        print("⚠️ GIF服务器未运行")
        return False
        
    try:
        command = {'type': cmd_type, 'data': data}
        _command_queue.put(command)
        return True
    except Exception as e:
        print(f"❌ 发送命令失败: {e}")
        return False

def stop_gif_service():
    """停止GIF服务"""
    global _gif_app, _is_running
    
    print("🛑 停止GIF服务...")
    _is_running = False
    
    if _gif_app:
        _gif_app.quit()
    
    print("✅ GIF服务已停止")

# ==================
# 简化API接口
# ==================

def gif_set_state(state):
    """设置GIF状态
    
    Args:
        state: 状态名称
            - idle/待机: 待机状态
            - listening/聆听: 聆听状态
            - thinking/思考: 思考状态  
            - speaking/说话: 说话状态
            - sleeping/休眠: 休眠状态
    """
    if _send_command('set_state', state):
        print(f"📡 设置GIF状态: {state}")
    else:
        print(f"❌ 设置GIF状态失败: {state}")

def gif_set_emotion(emotion):
    """设置GIF情感
    
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
    if _send_command('set_emotion', emotion):
        print(f"📡 设置GIF情感: {emotion}")
    else:
        print(f"❌ 设置GIF情感失败: {emotion}")

def gif_get_state():
    """获取当前GIF状态"""
    global _gif_server
    if _gif_server:
        return {
            "current_gif": _gif_server.current_gif,
            "current_state": _gif_server.current_state
        }
    return None

# ==================
# 情感分析函数
# ==================

def analyze_emotion_from_text(text):
    """从文本分析情感"""
    if not text:
        return None
        
    text_lower = text.lower()
    
    # 情感关键词映射
    emotion_keywords = {
        "happy": ["开心", "高兴", "快乐", "愉快", "兴奋", "哈哈", "太好了", "棒", "赞", "笑", "乐"],
        "angry": ["生气", "愤怒", "气愤", "恼火", "暴躁", "讨厌", "可恶", "火大", "怒", "恨"],
        "sad": ["难过", "痛苦", "难受", "不舒服", "苦恼", "郁闷", "沮丧", "失落", "伤心", "心痛", "悲伤"],
        "shy": ["害羞", "脸红", "不好意思", "羞涩", "腼腆", "羞怯", "羞羞", "羞人"],
        "surprised": ["惊讶", "意外", "没想到", "调皮", "淘气", "嘻嘻", "嘿嘿"],
        "confused": ["迷茫", "困惑", "不知道", "搞不懂", "茫然", "疑惑", "不明白", "懵"],
        "bored": ["无聊", "闲着", "没事做", "乏味", "单调", "枯燥", "无趣"]
    }
    
    # 计算各情感得分
    emotion_scores = {}
    for emotion, keywords in emotion_keywords.items():
        score = sum(text_lower.count(keyword) for keyword in keywords)
        if score > 0:
            emotion_scores[emotion] = score
    
    if emotion_scores:
        # 返回得分最高的情感
        best_emotion = max(emotion_scores, key=emotion_scores.get)
        print(f"🎭 文本情感分析: {best_emotion} (得分: {emotion_scores[best_emotion]})")
        return best_emotion
        
    return None

def gif_set_emotion_from_text(text):
    """根据文本内容设置情感GIF"""
    emotion = analyze_emotion_from_text(text)
    if emotion:
        gif_set_emotion(emotion)
    else:
        print("⚠️ 未检测到明显情感，保持当前状态")

# ==================
# 测试函数
# ==================

def test_gif_simple():
    """测试简化版GIF客户端"""
    print("🧪 测试简化版GIF API客户端")
    print("=" * 50)
    
    # 启动服务
    if not start_gif_service():
        print("❌ 服务启动失败")
        return
    
    print("✅ 服务启动成功，开始测试...")
    time.sleep(2)
    
    # 测试API调用
    test_commands = [
        ("设置待机状态", lambda: gif_set_state("idle")),
        ("设置聆听状态", lambda: gif_set_state("listening")),
        ("设置思考状态", lambda: gif_set_state("thinking")),
        ("表达开心情感", lambda: gif_set_emotion("happy")),
        ("根据文本设置情感", lambda: gif_set_emotion_from_text("我今天很生气")),
        ("返回待机", lambda: gif_set_state("idle"))
    ]
    
    for desc, cmd in test_commands:
        print(f"🎭 {desc}")
        cmd()
        time.sleep(3)
    
    print("🎉 测试完成！")
    print("💡 按Ctrl+C停止服务")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        stop_gif_service()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_gif_simple()
    else:
        print("💡 使用方法:")
        print("python gif_api_client_simple.py --test  # 运行测试")
        print("或在其他程序中导入使用API函数") 