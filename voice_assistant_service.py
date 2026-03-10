#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音助手服务类 - 集成新三线程架构
管理switchrole语音助手的生命周期，避免线程冲突
支持学校模式和家庭模式的不同行为

新架构特点：
- 线程A: 纯唤醒词监听，设置interrupt_flag，放入wake_queue，进入冷却期
- 线程B: 等待wake_queue，播放短音，ASR录音（支持中断），放入input_queue  
- 线程C: 等待input_queue，AI处理，TTS播放（支持中断），清理状态
"""

import os
import sys
import time
import logging
import threading
import queue
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer

# 配置日志
logger = logging.getLogger(__name__)

class VoiceAssistantService(QObject):
    """语音助手服务类 - 新三线程架构版本"""
    
    # 信号定义
    assistant_ready = pyqtSignal()  # 语音助手准备就绪
    wake_detected = pyqtSignal(dict)  # 检测到唤醒词
    user_speaking = pyqtSignal(str)  # 用户说话内容
    assistant_responding = pyqtSignal(str)  # 助手回复内容
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, environment='home'):
        super().__init__()
        self.environment = environment  # 'school' 或 'home'
        self.is_running = False
        self.is_initialized = False
        
        # 新架构相关
        self.audio_manager = None
        self.thread_a = None  # 唤醒词监听线程
        self.thread_b = None  # 用户交互线程
        self.thread_c = None  # AI回复线程
        
        # 监控线程
        self.monitor_thread = None
        
        logger.info(f"语音助手服务初始化 - 环境: {environment} (新三线程架构)")
    
    def initialize(self) -> bool:
        """初始化语音助手"""
        try:
            if self.is_initialized:
                logger.warning("语音助手已经初始化")
                return True
            
            logger.info("开始初始化语音助手 (新三线程架构)...")
            
            # 添加switchrole目录到路径并切换工作目录
            switchrole_path = os.path.join(os.getcwd(), 'switchrole')
            if switchrole_path not in sys.path:
                sys.path.insert(0, switchrole_path)
            
            # 检查必要文件
            wakeword_file = os.path.join(switchrole_path, 'wakeword.table')
            env_file = os.path.join(switchrole_path, 'xiaoxin.env')
            
            logger.info(f"🔍 检查必要文件...")
            logger.info(f"   wakeword.table: {'✅' if os.path.exists(wakeword_file) else '❌'}")
            logger.info(f"   xiaoxin.env: {'✅' if os.path.exists(env_file) else '❌'}")
            
            # 临时切换到switchrole目录（用于确保相对路径正确）
            original_cwd = os.getcwd()
            os.chdir(switchrole_path)
            logger.info(f"🔧 临时切换工作目录到: {switchrole_path}")
            
            try:
                # 加载环境变量
                if os.path.exists('xiaoxin.env'):
                    self._load_env_file('xiaoxin.env')
                
                # 导入新的三线程架构模块
                import switchrole.xiaoxin2_zh_new as xiaoxin2_zh_new
                self.xiaoxin_module = xiaoxin2_zh_new
                logger.info("✅ 新三线程架构模块导入成功")
                
                # 初始化音频设备管理器
                self.audio_manager = xiaoxin2_zh_new.AudioDeviceManager()
                if not self.audio_manager.init_devices():
                    logger.error("❌ 音频设备初始化失败")
                    return False
                
                logger.info("✅ 语音助手初始化成功 (新三线程架构)")
                self.is_initialized = True
                return True
                
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
                logger.info(f"🔧 恢复工作目录到: {original_cwd}")
            
        except ImportError as e:
            logger.error(f"❌ 导入新三线程架构模块失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 语音助手初始化失败: {e}")
            return False
    
    def _load_env_file(self, env_file_path: str):
        """加载环境变量配置文件"""
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if line.startswith('#') or not line or '=' not in line:
                        continue
                    
                    # 解析键值对
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 设置环境变量
                    os.environ[key] = value
                    logger.debug(f"设置环境变量: {key}")
            
            logger.info(f"✅ 环境变量配置加载成功")
                    
        except Exception as e:
            logger.error(f"❌ 加载环境变量配置失败: {e}")
    
    def start(self) -> bool:
        """启动语音助手"""
        try:
            if not self.is_initialized:
                if not self.initialize():
                    return False
            
            if self.is_running:
                logger.warning("语音助手已经在运行")
                return True
            
            logger.info(f"🚀 启动新三线程语音助手 - 环境: {self.environment}")
            
            # 设置系统运行标志
            self.xiaoxin_module.system_running.set()
            
            # 创建并启动线程A (唤醒词监听)
            self.thread_a = VoiceAssistantThreadA_New(self.audio_manager, self.xiaoxin_module)
            self.thread_a.wake_detected.connect(self._on_wake_detected)
            self.thread_a.start()
            
            # 创建并启动线程B (用户交互)
            self.thread_b = VoiceAssistantThreadB_New(self.audio_manager, self.xiaoxin_module)
            self.thread_b.user_input_received.connect(self._on_user_input)
            self.thread_b.start()
            
            # 创建并启动线程C (AI回复)
            self.thread_c = VoiceAssistantThreadC_New(self.audio_manager, self.xiaoxin_module)
            self.thread_c.response_ready.connect(self._on_ai_response)
            self.thread_c.start()
            
            # 启动状态监控线程
            self.monitor_thread = VoiceAssistantMonitor(self.xiaoxin_module)
            self.monitor_thread.start()
            
            self.is_running = True
            logger.info("✅ 新三线程语音助手启动成功")
            self.assistant_ready.emit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 语音助手启动失败: {e}")
            return False
    
    def stop(self):
        """停止语音助手"""
        try:
            if not self.is_running:
                return
            
            logger.info("⏹️ 停止新三线程语音助手...")
            
            # 停止系统运行
            if hasattr(self, 'xiaoxin_module'):
                self.xiaoxin_module.system_running.clear()
                # 设置中断标志确保所有线程能够及时退出
                self.xiaoxin_module.set_interrupt()
            
            # 停止所有线程
            for thread_name, thread in [('A', self.thread_a), ('B', self.thread_b), ('C', self.thread_c), ('监控', self.monitor_thread)]:
                if thread and thread.isRunning():
                    logger.info(f"⏹️ 停止线程{thread_name}...")
                    thread.stop()
                    if not thread.wait(3000):  # 等待3秒
                        logger.warning(f"⚠️ 线程{thread_name}未能在3秒内正常退出")
                        thread.terminate()
                        if not thread.wait(1000):  # 再等待1秒
                            logger.error(f"❌ 强制终止线程{thread_name}失败")
            
            self.is_running = False
            logger.info("✅ 语音助手已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止语音助手时出错: {e}")
    
    def set_environment(self, environment: str):
        """设置环境模式"""
        logger.info(f"设置环境模式: {environment}")
        self.environment = environment
        
        # 如果线程正在运行，需要通知它们环境变化
        if self.is_running and hasattr(self, 'xiaoxin_module'):
            # 可以通过全局变量或其他方式通知线程环境变化
            pass
    
    def pause_for_external_audio(self):
        """为外部音频播放暂停语音功能"""
        if self.is_running and hasattr(self, 'xiaoxin_module'):
            logger.info("⏸️ 为外部音频暂停语音功能")
            # 设置中断标志，但不清除系统运行标志
            self.xiaoxin_module.set_interrupt()
    
    def resume_after_external_audio(self):
        """外部音频播放结束后恢复语音功能"""
        if self.is_running and hasattr(self, 'xiaoxin_module'):
            logger.info("▶️ 外部音频结束，恢复语音功能")
            # 清除中断标志，允许继续运行
            self.xiaoxin_module.clear_interrupt()
    
    def _on_wake_detected(self, wake_event):
        """唤醒词检测回调"""
        logger.info(f"👋 检测到唤醒词: {wake_event}")
        self.wake_detected.emit(wake_event)
    
    def _on_user_input(self, user_input):
        """用户输入回调"""
        logger.info(f"🗣️ 用户说话: {user_input}")
        self.user_speaking.emit(user_input)
    
    def _on_ai_response(self, response):
        """AI回复回调"""
        logger.info(f"🤖 AI回复: {response[:50]}...")
        self.assistant_responding.emit(response)


class VoiceAssistantThreadA_New(QThread):
    """线程A封装：唤醒词检测（基于新三线程架构）"""
    
    wake_detected = pyqtSignal(dict)
    
    def __init__(self, audio_manager, xiaoxin_module):
        super().__init__()
        self.audio_manager = audio_manager
        self.xiaoxin_module = xiaoxin_module
        self.thread_a_instance = None
        self._running = True
        
    def run(self):
        """运行线程A"""
        try:
            # 创建线程A实例
            self.thread_a_instance = self.xiaoxin_module.ThreadA(self.audio_manager)
            
            # 🔧 修复重复播放wake.wav：添加额外的重复检测
            original_callback = self.thread_a_instance.wake_callback
            
            # 用于防止重复处理的时间戳
            self.last_wake_signal_time = 0
            self.wake_signal_cooldown = 1.0  # 1秒冷却时间
            
            def pyqt_wake_callback(wake_event):
                import time
                current_time = time.time()
                time_since_last = current_time - self.last_wake_signal_time
                
                # 🔧 防止重复处理：如果距离上次处理时间太短，只发送信号不调用原始回调
                if time_since_last < self.wake_signal_cooldown:
                    logger.info(f"🚫 [ThreadA封装] 唤醒事件冷却中 ({time_since_last:.1f}s < {self.wake_signal_cooldown}s)，只发送信号")
                    self.wake_detected.emit(wake_event)
                    return
                
                # 更新时间戳
                self.last_wake_signal_time = current_time
                
                # 正常处理：调用原始回调（播放wake.wav）并发送信号
                logger.info(f"🎯 [ThreadA封装] 检测到唤醒词，调用原始处理并发送信号: {wake_event}")
                original_callback(wake_event)
                self.wake_detected.emit(wake_event)
            
            self.thread_a_instance.wake_callback = pyqt_wake_callback
            
            # 运行线程A
            self.thread_a_instance.run()
            
        except Exception as e:
            logger.error(f"❌ [线程A] 运行异常: {e}")
    
    def stop(self):
        """停止线程A"""
        self._running = False
        if self.thread_a_instance:
            # 线程A会自己检查system_running标志并退出
            pass


class VoiceAssistantThreadB_New(QThread):
    """线程B封装：用户交互（基于新三线程架构）"""
    
    user_input_received = pyqtSignal(str)
    
    def __init__(self, audio_manager, xiaoxin_module):
        super().__init__()
        self.audio_manager = audio_manager
        self.xiaoxin_module = xiaoxin_module
        self.thread_b_instance = None
        self._running = True
        
    def run(self):
        """运行线程B"""
        try:
            # 创建线程B实例
            self.thread_b_instance = self.xiaoxin_module.ThreadB(self.audio_manager)
            
            # 🔧 修复：包装线程B的run方法，在发送到队列时同时发送PyQt信号
            original_run = self.thread_b_instance.run
            def wrapped_run():
                # 包装input_queue.put方法
                original_put = self.xiaoxin_module.input_queue.put
                def wrapped_put(user_input, *args, **kwargs):
                    # 先发送PyQt信号
                    if user_input and user_input != "restart":
                        self.user_input_received.emit(user_input)
                        logger.info(f"🔄 [线程B] 用户输入已发送到界面: {user_input}")
                    # 再放入队列
                    return original_put(user_input, *args, **kwargs)
                
                # 替换put方法
                self.xiaoxin_module.input_queue.put = wrapped_put
                
                # 运行原始线程B
                return original_run()
            
            # 替换run方法
            self.thread_b_instance.run = wrapped_run
            
            # 运行线程B
            self.thread_b_instance.run()
            
        except Exception as e:
            logger.error(f"❌ [线程B] 运行异常: {e}")
    
    def stop(self):
        """停止线程B"""
        self._running = False


class VoiceAssistantThreadC_New(QThread):
    """线程C封装：AI回复（基于新三线程架构）"""
    
    response_ready = pyqtSignal(str)
    
    def __init__(self, audio_manager, xiaoxin_module):
        super().__init__()
        self.audio_manager = audio_manager
        self.xiaoxin_module = xiaoxin_module
        self.thread_c_instance = None
        self._running = True
        
    def run(self):
        """运行线程C"""
        try:
            # 创建线程C实例
            self.thread_c_instance = self.xiaoxin_module.ThreadC(self.audio_manager)
            
            # 🔧 修复：包装AI回复生成方法，确保信号正确发送
            original_generate_ai = self.thread_c_instance.generate_ai_response
            def pyqt_generate_ai(user_input):
                ai_response = original_generate_ai(user_input)
                if ai_response:
                    # 发送AI回复信号到界面显示
                    self.response_ready.emit(ai_response)
                    logger.info(f"🔄 [线程C] AI回复已发送到界面: {ai_response[:50]}...")
                return ai_response
            
            self.thread_c_instance.generate_ai_response = pyqt_generate_ai
            
            # 运行线程C
            self.thread_c_instance.run()
            
        except Exception as e:
            logger.error(f"❌ [线程C] 运行异常: {e}")
    
    def stop(self):
        """停止线程C"""
        self._running = False


class VoiceAssistantMonitor(QThread):
    """状态监控线程"""
    
    def __init__(self, xiaoxin_module):
        super().__init__()
        self.xiaoxin_module = xiaoxin_module
        self._running = True
        
    def run(self):
        """运行监控"""
        while self._running and self.xiaoxin_module.system_running.is_set():
            try:
                # 每5秒显示一次状态
                with self.xiaoxin_module.status_lock:
                    status = self.xiaoxin_module.threads_status.copy()
                
                logger.info(f"📊 线程状态 - A:{status['thread_a']} | B:{status['thread_b']} | C:{status['thread_c']}")
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"❌ [监控线程] 异常: {e}")
                time.sleep(1)
    
    def stop(self):
        """停止监控"""
        self._running = False 