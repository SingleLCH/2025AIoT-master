#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全新三线程语音助手架构 - 解决TTS阻塞音乐播放问题

线程架构：
- 线程A: 唤醒词监听（纯监听，不做其他处理）
- 线程B: 用户语音识别（播放短音 + ASR录音，支持中断）
- 线程C: AI回复处理（生成回复 + TTS播放，支持中断）

核心逻辑：
1. A检测到唤醒词 → 设置interrupt_flag=True → 放入wake_queue → 进入冷却期
2. B等待wake_queue → 播放短音 → ASR录音（定期检查interrupt_flag） → 放入input_queue
3. C等待input_queue → AI处理 → TTS播放（定期检查interrupt_flag） → 清理状态

中断机制：
- 统一使用interrupt_flag控制所有线程
- 每个线程定期检查interrupt_flag，发现为True立即停止当前操作
- A线程设置interrupt_flag后，B和C线程会停止并回到等待状态
"""

import os
import time
import threading
import queue
import logging
import subprocess
from enum import Enum
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI
import dashscope
import json

# 项目模块导入
from xiaoxin2_skill import *
from xiaoxin2_wakefromnetwork import *
from audio_player import play_audio_blocking
from alsa_speech_recognizer import get_alsa_recognizer
from alsa_cosyvoice_tts import get_alsa_tts, text_to_speech_alsa
from continuous_wakeword_detector import start_continuous_detection, stop_continuous_detection
from audio_priority_manager import AudioPriority, request_audio_access, release_audio_access

# 🎭 表情功能导入
from emotion_manager import get_emotion_manager, send_wake_emotion, send_end_emotion, EMOTION_SYSTEM_PROMPT
from mqtt_emotion_sender import send_emotion_code

# 配置
load_dotenv("xiaoxin.env")
# 确保能找到环境变量文件
if not os.path.exists("xiaoxin.env"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "xiaoxin.env"))
logging.getLogger("httpx").setLevel(logging.WARNING)

# API配置
API_KEY = os.environ["DASHSCOPE_API_KEY"]
BASE_URL = os.environ["DASHSCOPE_BASE_URL"]
MODEL_NAME = os.environ["DASHSCOPE_MODEL"]
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
dashscope.api_key = API_KEY

# Azure配置
speech_key = os.environ["Azure_speech_key"]
service_region = os.environ["Azure_speech_region"]
keyword = os.environ["WakeupWord"]

# ==================== TTS恢复缓存机制 ====================

class TTSResumeCache:
    """TTS恢复缓存管理器"""
    
    def __init__(self):
        self.cached_text = None
        self.is_interrupted = False
        self.was_playing = False
        self.interrupt_time = None
        self.lock = threading.Lock()
        # 🔧 修复：预先创建恢复队列
        from queue import Queue
        self.resume_queue = Queue()
    
    def cache_tts_text(self, text):
        """缓存TTS文本"""
        with self.lock:
            self.cached_text = text
            self.was_playing = True
            self.is_interrupted = False
            print(f"💾 [TTS缓存] 已缓存文本: {text[:50]}...")
    
    def mark_interrupted(self):
        """标记TTS被中断"""
        with self.lock:
            if self.was_playing and self.cached_text:
                self.is_interrupted = True
                self.interrupt_time = time.time()
                print(f"⏸️ [TTS缓存] TTS被中断，已标记恢复点")
                return True
            return False
    
    def get_resume_text(self):
        """获取需要恢复的TTS文本"""
        with self.lock:
            if self.is_interrupted and self.cached_text:
                resume_text = self.cached_text
                print(f"🔄 [TTS缓存] 准备恢复播放: {resume_text[:50]}...")
                return resume_text
            return None
    
    def clear_cache(self):
        """清除缓存"""
        with self.lock:
            self.cached_text = None
            self.is_interrupted = False
            self.was_playing = False
            self.interrupt_time = None
            print("🗑️ [TTS缓存] 缓存已清除")
    
    def has_interrupted_tts(self):
        """检查是否有被中断的TTS"""
        with self.lock:
            return self.is_interrupted and self.cached_text is not None

# 全局TTS缓存实例
tts_cache = TTSResumeCache()

# ==================== 全局状态管理 ====================

# 线程间通信队列
wake_queue = queue.Queue()      # A → B: 唤醒事件
input_queue = queue.Queue()     # B → C: 用户输入

# 统一中断控制
interrupt_flag = threading.Event()  # 全局中断标志
system_running = threading.Event()  # 系统运行标志
system_running.set()  # 初始设置为运行状态

# 线程状态跟踪
threads_status = {
    'thread_a': 'stopped',  # stopped, running, listening
    'thread_b': 'stopped',  # stopped, waiting, playing_wake, recording
    'thread_c': 'stopped'   # stopped, waiting, processing, playing_tts
}
status_lock = threading.Lock()

# 对话状态
messages = []
current_conversation_id = None

# 音频设备管理器
class AudioDeviceManager:
    """音频设备管理器"""
    
    def __init__(self):
        self.alsa_recognizer = None
        self.alsa_tts = None
        self.azure_recognizer = None
        
    def init_devices(self):
        """初始化音频设备"""
        print("🔧 初始化音频设备...")
        
        # ALSA设备 (语音唤醒和TTS)
        self.alsa_recognizer = get_alsa_recognizer()
        if self.alsa_recognizer and self.alsa_recognizer.initialize():
            print("✅ ALSA语音识别设备初始化成功")
        else:
            print("❌ ALSA语音识别设备初始化失败")
            return False
        
        self.alsa_tts = get_alsa_tts()
        if self.alsa_tts and self.alsa_tts.initialize():
            print("✅ ALSA TTS设备初始化成功")
        else:
            print("❌ ALSA TTS设备初始化失败")
            return False
            
        # Azure PulseAudio设备 (用户语音识别)
        try:
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            speech_config.speech_recognition_language = "zh-CN"
            
            # 优化语音识别配置
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "2000")
            speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "1000")
            
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            self.azure_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            print("✅ Azure语音识别器初始化成功")
        except Exception as e:
            print(f"❌ Azure语音识别器初始化失败: {e}")
            return False

        return True

def update_thread_status(thread_name, status):
    """更新线程状态"""
    with status_lock:
        threads_status[thread_name] = status
        print(f"📊 {thread_name} -> {status}")

def check_interrupt():
    """检查中断标志"""
    return interrupt_flag.is_set()

def set_interrupt():
    """设置中断标志并立即停止所有音频播放和录音"""
    interrupt_flag.set()
    print("🛑 设置全局中断标志")

    # 🔧 立即停止所有音频播放
    try:
        # 1. 停止ALSA TTS播放
        from alsa_cosyvoice_tts import get_alsa_tts
        alsa_tts = get_alsa_tts()
        if alsa_tts:
            alsa_tts.interrupt_playback()
            print("🛑 已停止ALSA TTS播放")
    except Exception as e:
        print(f"⚠️ 停止ALSA TTS失败: {e}")

    try:
        # 2. 停止流式TTS播放器
        from streaming_tts_player import get_streaming_player
        streaming_player = get_streaming_player()
        if streaming_player and streaming_player.is_playing:
            streaming_player.interrupt()
            print("🛑 已停止流式TTS播放")
    except Exception as e:
        print(f"⚠️ 停止流式TTS失败: {e}")

    try:
        # 3. 停止所有音频播放
        from audio_player import stop_all_audio
        stop_all_audio()
        print("🛑 已停止所有音频播放")
    except Exception as e:
        print(f"⚠️ 停止音频播放失败: {e}")

    try:
        # 4. 🔧 关键修复：强制停止所有录音进程（包括arecord）
        import subprocess
        subprocess.run(['pkill', '-f', 'aplay'], check=False)
        print("🛑 已强制停止aplay进程")

        # 🔧 新增：停止所有arecord录音进程
        subprocess.run(['pkill', '-f', 'arecord'], check=False)
        print("🛑 已强制停止arecord录音进程")

        # 🔧 新增：停止Azure语音识别相关进程
        subprocess.run(['pkill', '-f', 'speechsdk'], check=False)
        print("🛑 已强制停止speechsdk进程")

        # 🔧 关键修复：暂停PulseAudio对USB麦克风的使用
        try:
            # 暂停所有PulseAudio音频源
            result = subprocess.run(['pactl', 'suspend-source', '@DEFAULT_SOURCE@', '1'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("🛑 已暂停PulseAudio默认音频源")
            else:
                print(f"⚠️ 暂停PulseAudio默认音频源失败: {result.stderr}")

            # 暂停USB麦克风源
            result = subprocess.run(['pactl', 'suspend-source', 'alsa_input.usb-CF-IC_HK_USB_REF_2023-0630-1200-00.analog-stereo', '1'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("🛑 已暂停PulseAudio USB麦克风源")
            else:
                print(f"⚠️ 暂停PulseAudio USB麦克风源失败: {result.stderr}")

        except Exception as pulse_e:
            print(f"⚠️ 暂停PulseAudio失败: {pulse_e}")

    except Exception as e:
        print(f"⚠️ 停止音频进程失败: {e}")

    # 🔧 新增：等待进程完全停止
    try:
        import time
        time.sleep(1.0)  # 增加等待时间确保PulseAudio暂停生效
        print("✅ 等待音频进程和PulseAudio完全停止")
    except Exception as e:
        print(f"⚠️ 等待进程停止失败: {e}")

def clear_interrupt():
    """清除中断标志并恢复PulseAudio"""
    interrupt_flag.clear()
    print("🔄 清除全局中断标志")

    # 🔧 新增：恢复PulseAudio对USB麦克风的使用
    try:
        import subprocess

        # 恢复USB麦克风源
        result = subprocess.run(['pactl', 'suspend-source', 'alsa_input.usb-CF-IC_HK_USB_REF_2023-0630-1200-00.analog-stereo', '0'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("🔄 已恢复PulseAudio USB麦克风源")
        else:
            print(f"⚠️ 恢复PulseAudio USB麦克风源失败: {result.stderr}")

        # 恢复默认音频源
        result = subprocess.run(['pactl', 'suspend-source', '@DEFAULT_SOURCE@', '0'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("🔄 已恢复PulseAudio默认音频源")
        else:
            print(f"⚠️ 恢复PulseAudio默认音频源失败: {result.stderr}")

    except Exception as pulse_e:
        print(f"⚠️ 恢复PulseAudio失败: {pulse_e}")

# ==================== 线程A: 唤醒词监听 ====================

class ThreadA:
    """线程A: 纯唤醒词监听"""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        self.detector = None
        self.last_wake_time = 0
        self.wake_cooldown = 2.0  # 2秒冷却时间
        
    def wake_callback(self, wake_event):
        """唤醒词检测回调"""
        current_time = time.time()
        
        # 🔧 关键修复：更强的重复检测机制
        time_since_last = current_time - self.last_wake_time
        if time_since_last < self.wake_cooldown:
            print(f"🚫 [线程A] 唤醒词重复检测，忽略 (冷却中: {time_since_last:.1f}s < {self.wake_cooldown}s)")
            return
        
        # 🔧 修复：检查当前是否已经在处理唤醒事件
        with status_lock:
            current_b_status = threads_status.get('thread_b', 'waiting')
            if current_b_status != 'waiting':
                print(f"🚫 [线程A] 线程B正在工作 ({current_b_status})，忽略重复唤醒")
                return
        
        # 🔧 修复：检查唤醒队列是否已经有事件
        if not wake_queue.empty():
            print(f"🚫 [线程A] 唤醒队列已有事件，忽略重复唤醒")
            return
            
        # 更新最后唤醒时间
        self.last_wake_time = current_time
        
        print(f"🎯 [线程A] 检测到唤醒词: {wake_event.get('text', keyword)}")
        
        # 🔧 简化中断机制：唤醒词一旦被说出就立即停止所有播放
        try:
            with status_lock:
                current_status = threads_status.get('thread_c', 'waiting')
            
            print(f"🛑 [线程A] 唤醒词检测，立即停止所有播放 (当前状态: {current_status})")
            
            # 1. 清除TTS缓存（不再需要恢复）
            tts_cache.clear_cache()
            print("🗑️ [线程A] 已清除TTS缓存，不再恢复播放")
            
            # 2. 立即设置中断标志（停止所有正在进行的操作）
            set_interrupt()
            print("🛑 [线程A] 已设置中断标志，停止所有音频播放")
            
            # 🔧 关键修复：强力停止流式TTS合成
            try:
                from streaming_tts_player import get_streaming_player
                streaming_player = get_streaming_player()
                if streaming_player and streaming_player.is_playing:
                    streaming_player.interrupt()
                    print("🛑 [线程A] 已强力中断流式TTS合成")
                    
                    # 等待合成线程完全停止
                    import threading
                    if hasattr(streaming_player, 'synthesis_thread') and streaming_player.synthesis_thread and streaming_player.synthesis_thread.is_alive():
                        streaming_player.synthesis_thread.join(timeout=0.5)
                        if streaming_player.synthesis_thread.is_alive():
                            print("⚠️ [线程A] 合成线程未能及时停止")
                        else:
                            print("✅ [线程A] 合成线程已停止")
            except Exception as e:
                print(f"⚠️ [线程A] 强力停止流式TTS失败: {e}")
            
            # 3. 放入唤醒队列（通知线程B开始工作）
            wake_queue.put(wake_event)
            print("📤 [线程A] 唤醒事件已放入队列")
            
            # 4. 进入冷却期（避免被自己的提示音重复唤醒）
            print(f"❄️ [线程A] 进入冷却期 ({self.wake_cooldown}秒)")
            
        except Exception as e:
            print(f"❌ [线程A] 唤醒处理异常: {e}")
            # 异常情况下也要更新冷却时间，避免重复触发
            self.last_wake_time = current_time
    
    def run(self):
        """运行线程A"""
        print("🎤 [线程A] 开始唤醒词监听...")
        update_thread_status('thread_a', 'listening')
        
        try:
            # 启动持续唤醒词检测
            self.detector = start_continuous_detection(
                wake_callback=self.wake_callback
            )
            
            if self.detector:
                print("✅ [线程A] 唤醒词检测器启动成功")
                # 保持运行直到系统关闭
                while system_running.is_set():
                    time.sleep(0.1)
            else:
                print("❌ [线程A] 唤醒词检测器启动失败")
                
        except Exception as e:
            print(f"❌ [线程A] 异常: {e}")
        finally:
            update_thread_status('thread_a', 'stopped')
            if self.detector:
                stop_continuous_detection()
            print("🛑 [线程A] 唤醒词监听已停止")

# ==================== 线程B: 用户语音识别 ====================

class ThreadB:
    """线程B: 用户交互（播放短音 + ASR录音）"""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        
    def play_wake_audio(self):
        """播放唤醒提示音"""
        
        # 🔧 关键修复：确保音频设备完全释放
        print("🔄 [线程B] 确保音频设备完全释放...")
        try:
            import subprocess
            import time
            
            # 1. 强制杀死所有可能占用音频设备的进程
            subprocess.run(['pkill', '-f', 'aplay'], check=False, capture_output=True)
            subprocess.run(['pkill', '-f', 'alsa'], check=False, capture_output=True)
            print("🛑 [线程B] 已强制停止所有音频进程")
            
            # 2. 等待设备完全释放
            # time.sleep(0.3)
            
            # 3. 确保流式TTS完全停止
            try:
                from streaming_tts_player import get_streaming_player
                streaming_player = get_streaming_player()
                if streaming_player and streaming_player.is_playing:
                    streaming_player.interrupt()
                    print("🛑 [线程B] 确保流式TTS完全停止")
                    # time.sleep(0.2)  # 给更多时间让设备释放
            except Exception as e:
                print(f"⚠️ [线程B] 停止流式TTS失败: {e}")
            
        except Exception as e:
            print(f"⚠️ [线程B] 释放音频设备失败: {e}")
        
        wake_wav = "wake.wav"  
        tts_permission_acquired = False
        
        try:
            # 🔧 关键修复：释放continuous_wakeword_detector申请的WAKE_WORD权限
            try:
                release_audio_access(AudioPriority.WAKE_WORD, "持续唤醒词检测")
                wake_word_released = True
                print("🔄 [线程B] 释放continuous_wakeword_detector的WAKE_WORD权限")
            except Exception as e:
                print(f"⚠️ [线程B] 释放WAKE_WORD权限失败: {e}")
            
            # 🔧 优化：立即申请TTS权限并播放
            if request_audio_access(AudioPriority.TTS, "唤醒提示音播放"):
                tts_permission_acquired = True
                print("✅ [线程B] 获得音频播放权限")
                
                # 🔧 关键修复：多次重试播放wake.wav，确保成功
                max_retries = 1
                for retry in range(max_retries):
                    try:
                        cmd = ['aplay', '-D', 'hw:1,0', wake_wav]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            print("✅ [线程B] 唤醒提示音播放完成 (aplay hw:2,0)")
                            break
                        else:
                            print(f"❌ [线程B] aplay播放失败 (重试{retry+1}/{max_retries}): {result.stderr}")
                            if retry < max_retries - 1:
                                # 重试前再次清理音频设备
                                subprocess.run(['pkill', '-f', 'aplay'], check=False, capture_output=True)
                                time.sleep(0.2)
                    except subprocess.TimeoutExpired:
                        print(f"❌ [线程B] aplay播放超时 (重试{retry+1}/{max_retries})")
                        if retry < max_retries - 1:
                            subprocess.run(['pkill', '-f', 'aplay'], check=False, capture_output=True)
                            time.sleep(0.2)
                    except Exception as aplay_e:
                        print(f"❌ [线程B] aplay异常 (重试{retry+1}/{max_retries}): {aplay_e}")
                        if retry < max_retries - 1:
                            time.sleep(0.2)
            else:
                print("❌ [线程B] 无法获得音频播放权限")
                
        except Exception as e:
            print(f"❌ [线程B] 播放唤醒提示音异常: {e}")
            
        finally:
            # 🔧 关键修复：确保TTS权限被释放
            if tts_permission_acquired:
                try:
                    release_audio_access(AudioPriority.TTS, "唤醒提示音播放")
                    print("✅ [线程B] TTS权限已释放")
                    print("🔄 [线程B] WAKE_WORD权限已释放，等待线程C申请TTS权限")
                except Exception as release_e:
                    print(f"⚠️ [线程B] TTS权限释放失败: {release_e}")
        
        print("🔄 [线程B] 唤醒提示音播放完成")
        
        # 🔧 发送wake.wav播放完成表情 (2-1-3)
        try:
            from mqtt_emotion_sender import send_emotion_code
            send_emotion_code("2-1-3")
            print("🎭 [线程B] 已发送wake.wav播放完成表情: 2-1-3")
        except Exception as emotion_e:
            print(f"⚠️ [线程B] 发送wake.wav播放完成表情失败: {emotion_e}")
    
    def convert_mp3_to_wav(self, mp3_file, wav_file):
        """转换MP3为WAV"""
        try:
            cmd = ['ffmpeg', '-i', mp3_file, '-ar', '48000', '-ac', '2', '-sample_fmt', 's16', '-f', 'wav', '-y', wav_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def listen_user_input(self):
        """监听用户输入（支持中断）"""
        print("🎤 [线程B] 开始监听用户输入...")
        update_thread_status('thread_b', 'recording')
        
        try:
            recognizer = self.audio_manager.azure_recognizer
            if not recognizer:
                print("❌ [线程B] Azure语音识别器未初始化")
                return None
            
            user_input = None
            
            def speech_recognized(evt):
                nonlocal user_input
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    user_input = evt.result.text.strip()
                    print(f"🎯 [线程B] 识别到用户输入: '{user_input}'")
                elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                    print("🤔 [线程B] 未识别到有效语音")
                else:
                    print(f"⚠️ [线程B] 识别结果: {evt.result.reason}")
            
            # 设置识别事件
            recognizer.recognized.connect(speech_recognized)
            
            # 🔧 确保识别器状态正确，先停止可能存在的识别
            try:
                recognizer.stop_continuous_recognition()
                time.sleep(0.1)  # 短暂等待状态重置
            except Exception:
                pass  # 忽略停止失败的错误
            
            # 开始连续识别
            recognizer.start_continuous_recognition()
            
            # 等待识别结果，同时检查中断
            start_time = time.time()
            timeout = 10.0  # 10秒超时
            
            while time.time() - start_time < timeout:
                # 检查中断标志
                if check_interrupt():
                    print("🛑 [线程B] 检测到中断信号，停止录音")
                    break
                    
                # 检查是否有识别结果
                if user_input is not None:
                    break
                    
                time.sleep(0.1)  # 100ms检查间隔
            
            # 停止识别
            try:
                recognizer.stop_continuous_recognition()
                time.sleep(0.1)  # 等待停止完成

                # 🔧 关键修复：强制停止可能残留的录音进程
                import subprocess
                subprocess.run(['pkill', '-f', 'arecord'], check=False)
                print("🛑 [线程B] 已强制停止残留的arecord进程")

            except Exception as e:
                print(f"⚠️ [线程B] 停止识别异常: {e}")

                # 即使停止识别失败，也要强制清理录音进程
                try:
                    import subprocess
                    subprocess.run(['pkill', '-f', 'arecord'], check=False)
                    print("🛑 [线程B] 异常情况下强制停止arecord进程")
                except:
                    pass
            
            if user_input:
                print(f"✅ [线程B] 用户输入识别完成: '{user_input}'")
                return user_input
            else:
                if check_interrupt():
                    print("🛑 [线程B] 录音被中断")
                else:
                    print("⏰ [线程B] 录音超时，未检测到有效输入")
                    # 🔧 修复问题2：监听超时时发送2-2-0表情
                    try:
                        from mqtt_emotion_sender import send_emotion_code
                        send_emotion_code("2-2-0")
                        print("🎭 [线程B] 已发送监听超时表情: 2-2-0")
                    except Exception as e:
                        print(f"⚠️ [线程B] 发送监听超时表情失败: {e}")
                return None
                
        except Exception as e:
            print(f"❌ [线程B] 用户输入监听异常: {e}")
            return None
    
    def run(self):
        """运行线程B"""
        print("👂 [线程B] 开始用户交互处理...")
        update_thread_status('thread_b', 'waiting')
        
        while system_running.is_set():
            try:
                # 1. 等待唤醒事件
                try:
                    wake_event = wake_queue.get(timeout=1.0)
                    print(f"📥 [线程B] 收到唤醒事件: {wake_event}")
                except queue.Empty:
                    continue
                
                # 🔧 关键修复：清除中断标志，开始新的交互轮次
                clear_interrupt()
                print("🔄 [线程B] 清除中断标志，开始新的交互轮次")
                
                # 2. 播放唤醒提示音
                update_thread_status('thread_b', 'playing_wake')
                print("🔊 [线程B] 开始播放唤醒提示音...")
                self.play_wake_audio()
                print("🔊 [线程B] 唤醒提示音播放完成")
                
                # 3. 发送wake.wav播放完成表情
                try:
                    from mqtt_emotion_sender import send_emotion_code
                    send_emotion_code("2-1-3")
                    print("🎭 [线程B] 已发送wake.wav播放完成表情: 2-1-3")
                except Exception as e:
                    print(f"⚠️ [线程B] 发送表情失败: {e}")
                
                # 等待一小段时间，让提示音播放完
                time.sleep(0.5)
                
                # 4. 监听用户输入
                user_input = self.listen_user_input()
                
                # 5. 如果有用户输入且未被中断，发送给线程C
                if user_input and not check_interrupt():
                    print(f"📤 [线程B] 发送用户输入到处理队列: '{user_input}'")
                    input_queue.put(user_input)
                else:
                    print("💨 [线程B] 本轮交互结束（无输入或被中断）")
                
                # 6. 回到等待状态
                update_thread_status('thread_b', 'waiting')
                
            except Exception as e:
                print(f"❌ [线程B] 运行异常: {e}")
                update_thread_status('thread_b', 'waiting')
                time.sleep(1)
        
        update_thread_status('thread_b', 'stopped')
        print("🛑 [线程B] 用户交互处理已停止")

# ==================== 线程C: AI回复处理 ====================

class ThreadC:
    """线程C: AI回复处理（生成回复 + TTS播放）"""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
    
    def generate_ai_response(self, user_input):
        """生成AI回复"""
        global messages
        
        try:
            print(f"🤖 [线程C] 开始处理用户输入: '{user_input}'")
            
            # 检查中断
            if check_interrupt():
                print("🛑 [线程C] AI处理前检测到中断")
                return None
            
            messages.append({"role": "user", "content": user_input})
            
            # 🔧 优先级1：检查功能命令
            try:
                from function_handlers import handle_voice_function_command
                
                function_success, function_response = handle_voice_function_command(user_input)
                if function_success and function_response:
                    print(f"🎯 [线程C] 识别为功能命令: {user_input}")
                    messages.append({"role": "assistant", "content": function_response})
                    return function_response
                    
            except Exception as func_e:
                print(f"⚠️ [线程C] 功能命令处理异常: {func_e}")
            
            # 🔧 优先级2：检查用户信息收集
            try:
                from user_memory import get_user_info_status, extract_user_info_from_response, update_user_info
                
                info_complete, missing_fields = get_user_info_status()
                if not info_complete:
                    extracted_info = extract_user_info_from_response(user_input)
                    if extracted_info:
                        update_user_info(extracted_info)
                        
                        # 重新检查信息完整性
                        info_complete, remaining_fields = get_user_info_status()
                        if info_complete:
                            user_name = extracted_info.get('name', '')
                            user_grade = extracted_info.get('grade', '')
                            response = f"好的，{user_name}！我记住了你在读{user_grade}。现在我可以更好地为你服务了！"
                            messages.append({"role": "assistant", "content": response})
                            return response
                        else:
                            # 还需要更多信息
                            if 'name' in remaining_fields:
                                response = "好的！请问我应该怎么称呼你呢？"
                            elif 'grade' in remaining_fields:
                                response = "请问你现在读几年级呢？"
                            else:
                                response = "请问你的名字和年级是什么呢？"
                            messages.append({"role": "assistant", "content": response})
                            return response
                    else:
                        # 询问缺失信息
                        if 'name' in missing_fields and 'grade' in missing_fields:
                            response = "你好！请问我该怎么称呼你？你现在读几年级？"
                        elif 'name' in missing_fields:
                            response = "请问我应该怎么称呼你呢？"
                        elif 'grade' in missing_fields:
                            response = "请问你现在读几年级呢？"
                        else:
                            response = "请告诉我你的名字和年级吧！"
                        messages.append({"role": "assistant", "content": response})
                        return response
                        
            except Exception as info_e:
                print(f"⚠️ [线程C] 用户信息处理异常: {info_e}")
            
            # 🔧 优先级3：普通AI对话
            from xiaoxin2_skill import getTools, getSystemPrompt
            available_tools = getTools()
            
            # 检查用户信息完整性决定系统提示词
            # 🔧 修复：统一使用正常的系统提示词，避免JSON格式回复
            system_content = getSystemPrompt()
            
            sysmesg = {"role": "system", "content": system_content}
            
            # 检查中断
            if check_interrupt():
                print("🛑 [线程C] AI调用前检测到中断")
                return None
            
            # 调用AI
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[sysmesg] + messages[-10:],
                tools=available_tools,
                temperature=0.6,
                max_tokens=500,
                timeout=30
            )
            
            choice = response.choices[0]
            
            # 处理函数调用
            if choice.message.tool_calls:
                print(f"🔧 [线程C] 检测到函数调用")
                
                messages.append({
                    "role": "assistant", 
                    "content": choice.message.content,
                    "tool_calls": choice.message.tool_calls
                })
                
                has_playmusic_call = False
                
                for tool_call in choice.message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name == "playmusic":
                        has_playmusic_call = True
                    
                    # 检查中断
                    if check_interrupt():
                        print("🛑 [线程C] 函数执行前检测到中断")
                        return None
                    
                    try:
                        import xiaoxin2_skill
                        if hasattr(xiaoxin2_skill, function_name):
                            function_result = getattr(xiaoxin2_skill, function_name)(**function_args)
                        else:
                            function_result = f"函数 {function_name} 不存在"
                    except Exception as e:
                        function_result = f"函数执行失败: {str(e)}"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_result
                    })
                
                # 音乐播放特殊处理
                if has_playmusic_call:
                    for msg in reversed(messages):
                        if msg.get("role") == "tool" and "正在为您播放" in msg.get("content", ""):
                            ai_reply = msg["content"]
                            print(f"🎵 [线程C] 找到音乐播放结果: {ai_reply}")
                            
                            # 🔧 重要修复：替换掉AI的长回复，只保留简洁的播放提示
                            # 移除之前添加的包含长回复的assistant消息
                            if messages and messages[-1].get("role") == "assistant" and messages[-1].get("tool_calls"):
                                print(f"🗑️ [线程C] 移除AI的长回复，只保留简洁播放提示")
                                messages.pop()  # 移除包含长回复的消息
                            
                            messages.append({"role": "assistant", "content": ai_reply})
                            return ai_reply
                
                # 🔧 特殊处理：教案生成和PPT总结功能直接返回工具结果，不再进行第二次AI调用
                has_teaching_plan_call = False
                has_ppt_summary_call = False
                tool_result = None
                
                for tool_call in choice.message.tool_calls:
                    function_name = tool_call.function.name
                    if function_name == "generate_teaching_plan":
                        has_teaching_plan_call = True
                    elif function_name == "summarize_ppt_content":
                        has_ppt_summary_call = True
                
                # 查找工具执行结果
                for msg in reversed(messages):
                    if msg.get("role") == "tool":
                        tool_result = msg.get("content", "")
                        break
                
                # 如果是教案生成或PPT总结，直接返回工具结果
                if (has_teaching_plan_call or has_ppt_summary_call) and tool_result:
                    print(f"🎯 [线程C] 教案生成/PPT总结完成，直接返回工具结果")
                    
                    # 🔧 关键修复：完全清理相关的tool_calls和tool消息，避免干扰后续调用
                    # 1. 移除刚添加的带有tool_calls的assistant消息和所有tool消息
                    messages_to_remove = []
                    for i in range(len(messages) - 1, -1, -1):
                        msg = messages[i]
                        # 找到最近添加的带有tool_calls的assistant消息
                        if msg.get("role") == "assistant" and msg.get("tool_calls"):
                            messages_to_remove.append(i)
                            print(f"🗑️ [线程C] 标记移除assistant消息(位置{i})")
                            break
                    
                    # 2. 移除所有与此次调用相关的tool消息（从最近的assistant消息之后的所有tool消息）
                    start_remove_index = messages_to_remove[0] if messages_to_remove else len(messages)
                    for i in range(len(messages) - 1, start_remove_index, -1):
                        msg = messages[i]
                        if msg.get("role") == "tool":
                            messages_to_remove.append(i)
                            print(f"🗑️ [线程C] 标记移除tool消息(位置{i}): {msg.get('content', '')[:30]}...")
                    
                    # 3. 按逆序移除消息（避免索引变化）
                    for i in sorted(messages_to_remove, reverse=True):
                        messages.pop(i)
                        print(f"✂️ [线程C] 已移除位置{i}的消息")
                    
                    # 4. 添加简洁的assistant回复
                    messages.append({"role": "assistant", "content": tool_result})
                    print(f"✅ [线程C] 添加干净的assistant回复")
                    
                    return tool_result
                
                # 第二次调用获取最终回复（其他功能）
                if check_interrupt():
                    print("🛑 [线程C] 第二次AI调用前检测到中断")
                    return None
                
                # 🔧 修复：确保tool消息有对应的tool_calls前置消息
                # 构建正确的消息序列，避免孤立的tool消息
                safe_messages = []
                recent_messages = messages[-10:]  # 获取最近10条消息
                
                for i, msg in enumerate(recent_messages):
                    if msg.get("role") == "tool":
                        # 确保tool消息前面有对应的assistant消息
                        if i > 0 and recent_messages[i-1].get("role") == "assistant" and recent_messages[i-1].get("tool_calls"):
                            safe_messages.append(msg)
                        # 如果没有对应的tool_calls消息，跳过这个tool消息
                        else:
                            print(f"⚠️ [线程C] 跳过孤立的tool消息: {msg.get('content', '')[:50]}...")
                    else:
                        safe_messages.append(msg)
                
                final_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[sysmesg] + safe_messages,
                    temperature=0.6,
                    max_tokens=500,
                    timeout=30
                )
                
                ai_reply = final_response.choices[0].message.content
                messages.append({"role": "assistant", "content": ai_reply})
                return ai_reply
            else:
                # 直接回复
                ai_reply = choice.message.content
                messages.append({"role": "assistant", "content": ai_reply})
                return ai_reply
                
        except Exception as e:
            print(f"❌ [线程C] AI回复生成异常: {e}")
            return "抱歉，我现在无法处理您的请求。"
    
    def play_tts_response(self, response):
        """播放TTS回复（流式播放）"""
        print(f"🎤 [线程C] 开始播放TTS回复: {response[:50]}...")
        
        # 更新线程状态
        update_thread_status('thread_c', 'playing_tts')
        
        # 🔧 关键修复：确保能够获取TTS权限
        # 1. 先尝试释放可能残留的WAKE_WORD权限
        try:
            from audio_priority_manager import release_audio_access
            release_audio_access(AudioPriority.WAKE_WORD, "线程C-为TTS让路")
            print("🔄 [线程C] 已释放WAKE_WORD权限为TTS让路")
        except Exception as e:
            print(f"⚠️ [线程C] 释放WAKE_WORD权限失败: {e}")
        
        # 2. 申请TTS权限
        if not request_audio_access(AudioPriority.TTS, "线程C-TTS播放"):
            print("❌ [线程C] 无法获取TTS播放权限")
            # 🔧 强制释放所有权限后重试
            try:
                from audio_priority_manager import get_audio_manager
                audio_manager = get_audio_manager()
                audio_manager.force_stop_all()
                print("🔄 [线程C] 已强制释放所有权限")
                
                # 重新申请TTS权限
                if not request_audio_access(AudioPriority.TTS, "线程C-TTS播放-重试"):
                    print("❌ [线程C] 重试申请TTS权限仍然失败")
                    return False
                else:
                    print("✅ [线程C] 重试申请TTS权限成功")
            except Exception as force_e:
                print(f"❌ [线程C] 强制释放权限失败: {force_e}")
                return False
        
        try:
            # 🔧 使用正确的流式TTS播放：将完整文本分句进行流式播放
            from streaming_tts_player import get_streaming_player
            streaming_player = get_streaming_player()
            
            if streaming_player:
                # 将完整文本分句进行流式播放
                sentences = streaming_player.split_text_by_sentences(response)
                print(f"🎵 [线程C] 将文本分为 {len(sentences)} 个句子进行流式播放")
                
                def text_generator():
                    for sentence in sentences:
                        if sentence.strip():
                            print(f"🎤 [线程C] 播放句子: {sentence[:30]}...")
                            yield sentence.strip()
                
                success = streaming_player.play_streaming_text(text_generator())
                
                if success:
                    print("✅ [线程C] 流式TTS播放完成")
                    return True
                else:
                    print("❌ [线程C] 流式TTS播放失败")
                    return False
            else:
                print("❌ [线程C] 流式TTS播放器未初始化")
                return False
                
        except Exception as e:
            print(f"❌ [线程C] 流式TTS播放异常: {e}")
            return False
                
        finally:
            # 🔧 关键修复：无论成功失败都要释放TTS权限
            try:
                release_audio_access(AudioPriority.TTS, "线程C-TTS播放")
                print("✅ [线程C] TTS权限已释放")
            except Exception as e:
                print(f"⚠️ [线程C] 释放TTS权限失败: {e}")
    
    def check_and_resume_tts(self):
        """检查并处理TTS恢复"""
        try:
            # 🔧 修复：检查是否有需要恢复的TTS
            if not tts_cache.resume_queue.empty():
                resume_text = tts_cache.resume_queue.get_nowait()
                print(f"🔄 [线程C] 恢复播放被中断的TTS: {resume_text[:50]}...")
                
                # 🔧 重要：恢复播放时不能再次缓存，避免无限循环
                # 直接播放，不通过play_tts_response避免重复缓存
                try:
                    # 申请TTS权限
                    if not request_audio_access(AudioPriority.TTS, "线程C-TTS恢复播放"):
                        print("❌ [线程C] 恢复播放无法获取TTS权限")
                        return False
                    
                    # 发送表情
                    try:
                        from emotion_library import send_emotion_for_text
                        send_emotion_for_text(resume_text)
                    except Exception as e:
                        print(f"⚠️ [线程C] 恢复播放表情发送失败: {e}")
                    
                    # 使用流式TTS播放
                    from streaming_tts_player import get_streaming_player
                    streaming_player = get_streaming_player()
                    
                    if streaming_player:
                        def text_generator():
                            yield resume_text
                        
                        success = streaming_player.play_streaming_text(text_generator())
                        
                        if success:
                            print("✅ [线程C] TTS恢复播放完成")
                            # 清除缓存，因为播放成功
                            tts_cache.clear_cache()
                        else:
                            print("❌ [线程C] TTS恢复播放失败")
                        
                        return True
                    else:
                        print("❌ [线程C] 流式TTS播放器未初始化")
                        return False
                        
                finally:
                    # 释放TTS权限
                    try:
                        release_audio_access(AudioPriority.TTS, "线程C-TTS恢复播放")
                    except Exception as e:
                        print(f"⚠️ [线程C] 恢复播放释放TTS权限失败: {e}")
                
        except Exception as e:
            print(f"⚠️ [线程C] 检查TTS恢复异常: {e}")
            
        return False  # 没有恢复任务
    
    def run(self):
        """运行线程C"""
        print("🧠 [线程C] 开始AI回复处理...")
        update_thread_status('thread_c', 'waiting')
        
        while system_running.is_set():
            try:
                # 🔧 取消TTS恢复检查：不再需要恢复播放功能
                # 1. 等待用户输入
                try:
                    user_input = input_queue.get(timeout=1.0)
                    print(f"📥 [线程C] 收到用户输入: '{user_input}'")
                except queue.Empty:
                    continue
                
                # 2. 检查中断
                if check_interrupt():
                    print("🛑 [线程C] 处理前检测到中断，跳过本次处理")
                    continue
                
                # 3. 发送进入线程C表情
                try:
                    from mqtt_emotion_sender import send_emotion_code
                    send_emotion_code("2-2-0")
                    print("🎭 [线程C] 已发送进入AI处理表情: 2-2-0")
                except Exception as e:
                    print(f"⚠️ [线程C] 发送表情失败: {e}")
                
                # 4. 生成AI回复
                update_thread_status('thread_c', 'processing')
                ai_response = self.generate_ai_response(user_input)
                
                if not ai_response or check_interrupt():
                    print("🛑 [线程C] AI处理被中断或失败")
                    update_thread_status('thread_c', 'waiting')
                    continue
                
                # 5. 播放TTS回复
                update_thread_status('thread_c', 'playing_tts')
                self.play_tts_response(ai_response)
                
                # 🔧 关键修复：TTS播放完成后才释放WAKE_WORD权限，让音乐播放器可以工作
                # 注意：这里释放的是continuous_wakeword_detector的权限，但不使用相同标识
                # 因为我们想让音乐播放器能获取到权限
                try:
                    # 这里暂时不释放WAKE_WORD权限，让音乐播放器可以使用MUSIC权限
                    print("🔄 [线程C] TTS播放完成，音乐播放器可以使用MUSIC权限")
                except Exception as e:
                    print(f"⚠️ [线程C] 权限管理异常: {e}")
                
                # 6. 清理状态，准备下一轮
                print("✅ [线程C] 本轮对话处理完成")
                clear_interrupt()  # 清除中断标志，准备下一轮
                
                # 🔧 重新获取WAKE_WORD权限给continuous_wakeword_detector，让线程A可以继续监听
                try:
                    if request_audio_access(AudioPriority.WAKE_WORD, "持续唤醒词检测"):
                        print("🔄 [线程C] 重新获取WAKE_WORD权限成功，continuous_wakeword_detector可以继续监听")
                    else:
                        print("⚠️ [线程C] 重新获取WAKE_WORD权限失败")
                except Exception as e:
                    print(f"⚠️ [线程C] 重新获取WAKE_WORD权限异常: {e}")
                
                update_thread_status('thread_c', 'waiting')
                
            except Exception as e:
                print(f"❌ [线程C] 运行异常: {e}")
                update_thread_status('thread_c', 'waiting')
                time.sleep(1)
        
        update_thread_status('thread_c', 'stopped')
        print("🛑 [线程C] AI回复处理已停止")

# ==================== 主函数 ====================

def main():
    """主函数：启动三线程架构"""
    global system_running
    
    print("🚀 启动全新三线程语音助手架构")
    print("📋 线程分工：")
    print("   线程A: 唤醒词监听 → 设置中断 → 通知线程B")
    print("   线程B: 播放短音 → ASR录音 → 通知线程C") 
    print("   线程C: AI处理 → TTS播放 → 清理状态")
    print("🛑 中断机制：统一interrupt_flag控制所有线程")
    
    # 初始化音频设备
    audio_manager = AudioDeviceManager()
    if not audio_manager.init_devices():
        print("❌ 音频设备初始化失败")
        return
    
    # 播放启动提示音
    try:
        if os.path.exists("wakeup_word.mp3"):
            print("🎵 播放启动欢迎音频...")
            # 这里可以播放启动音频，但要注意不要阻塞
        print(f"🎤 语音助手已启动，说'{keyword}'来唤醒")
    except Exception as e:
        print(f"⚠️ 启动音频播放失败: {e}")
    
    # 创建三个线程
    thread_a = ThreadA(audio_manager)
    thread_b = ThreadB(audio_manager)
    thread_c = ThreadC(audio_manager)
    
    # 启动三个线程
    threads = []
    
    # 启动线程A（唤醒词监听）
    thread_a_handle = threading.Thread(target=thread_a.run, daemon=True, name="ThreadA-WakeWord")
    thread_a_handle.start()
    threads.append(thread_a_handle)
    
    # 启动线程B（用户交互）
    thread_b_handle = threading.Thread(target=thread_b.run, daemon=True, name="ThreadB-UserInput")
    thread_b_handle.start()
    threads.append(thread_b_handle)
    
    # 启动线程C（AI回复）
    thread_c_handle = threading.Thread(target=thread_c.run, daemon=True, name="ThreadC-AIResponse")
    thread_c_handle.start()
    threads.append(thread_c_handle)
    
    print("✅ 所有线程已启动，进入监控模式...")
    
    try:
        # 主线程只做监控，不处理业务逻辑
        while system_running.is_set():
            # 定期打印线程状态
            with status_lock:
                print(f"📊 线程状态 - A:{threads_status['thread_a']} | B:{threads_status['thread_b']} | C:{threads_status['thread_c']}")
            
            # 检查线程是否还活跃
            for i, t in enumerate(threads):
                if not t.is_alive():
                    print(f"⚠️ 线程{i+1}已停止，可能需要重启")
            
            time.sleep(10)  # 每10秒检查一次
            
    except KeyboardInterrupt:
        print("\n🛑 收到退出信号，开始关闭系统...")
    except Exception as e:
        print(f"❌ 主监控异常: {e}")
    finally:
        # 优雅关闭
        print("🧹 开始系统清理...")
        system_running.clear()
        set_interrupt()  # 设置中断标志，让所有线程退出
        
        # 等待线程退出
        for i, t in enumerate(threads):
            try:
                t.join(timeout=3)
                if t.is_alive():
                    print(f"⚠️ 线程{i+1}未能在3秒内退出")
                else:
                    print(f"✅ 线程{i+1}已安全退出")
            except:
                pass
        
        # 清理音频资源
        try:
            stop_continuous_detection()
        except:
            pass
        
        print("✅ 语音助手已安全关闭")

if __name__ == "__main__":
    main() 