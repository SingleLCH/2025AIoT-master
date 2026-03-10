#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
三线程语音助手架构

线程A: ALSA + m麦克风 → 持续监听唤醒词 "你好广和通"
线程B: PulseAudio + HK麦克风 → 用户交互（播放wake.mp3 + 监听用户输入）
线程C: AI对话处理 → 可中断/恢复的对话和播放
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

# 🎭 表情功能导入
from emotion_manager import get_emotion_manager, send_wake_emotion, send_end_emotion, EMOTION_SYSTEM_PROMPT
from mqtt_emotion_sender import send_emotion_code

# 配置
load_dotenv("xiaoxin.env")
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

# 系统状态
class SystemState(Enum):
    WAKE_LISTENING = "wake_listening"      # A线程监听中
    USER_INTERACTION = "user_interaction"  # B线程交互中
    AI_PROCESSING = "ai_processing"        # C线程处理中
    AUDIO_PLAYING = "audio_playing"        # C线程播放中

# 全局状态
current_state = SystemState.WAKE_LISTENING
messages = []

# 🔧 音乐播放状态
music_playing = False
music_paused = False

# 🔧 新增：动态音频设备切换状态
audio_playback_active = False  # ALSA播放是否活跃
wake_audio_mode = "azure_default"  # 当前唤醒音频模式：azure_default 或 pulseaudio

# 线程间通信
wake_queue = queue.Queue()      # A → B: 唤醒事件
input_queue = queue.Queue()     # B → C: 用户输入
interrupt_queue = queue.Queue() # A → C: 中断信号

# 线程控制
thread_a_running = True
thread_b_running = True
current_c_thread = None
current_audio_state = None  # 用于恢复播放

# 🔧 全局TTS中断标志
tts_interrupt_flag = False

# GIF API - 已禁用PyQt5页面展示
GIF_AVAILABLE = False
# try:
#     from gif_api_client_simple import start_gif_service, stop_gif_service, gif_set_state, gif_set_emotion_from_text
#     GIF_AVAILABLE = True
# except ImportError:
#     GIF_AVAILABLE = False

def convert_mp3_to_wav(mp3_file, wav_file):
    """转换MP3为WAV格式 - 🔧 增强版本，处理损坏的MP3文件"""
    try:
        # 🔧 首先检查MP3文件是否有效
        if not os.path.exists(mp3_file):
            print(f"❌ MP3文件不存在: {mp3_file}")
            return False
        
        file_size = os.path.getsize(mp3_file)
        if file_size < 1000:  # 文件太小，可能损坏
            print(f"❌ MP3文件太小，可能损坏: {mp3_file} ({file_size} bytes)")
            return False
        
        print(f"🔍 检查MP3文件: {mp3_file} ({file_size} bytes)")
        
        # 🔧 使用更强的ffmpeg参数，增加容错性
        cmd = [
            'ffmpeg', '-i', mp3_file,
            '-analyzeduration', '10000000',  # 增加分析时长
            '-probesize', '10000000',        # 增加探测大小
            '-ar', '48000',                  # 采样率
            '-ac', '2',                      # 双声道
            '-sample_fmt', 's16',            # 16位有符号整数
            '-f', 'wav',                     # WAV格式
            '-y',                            # 覆盖输出文件
            wav_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # 检查输出WAV文件是否有效
            if os.path.exists(wav_file) and os.path.getsize(wav_file) > 1000:
                print(f"✅ MP3转WAV成功: {wav_file} ({os.path.getsize(wav_file)} bytes)")
                return True
            else:
                print(f"❌ WAV文件生成失败或太小: {wav_file}")
                return False
        else:
            print(f"❌ MP3转WAV失败: {result.stderr}")
            
            # 🔧 如果常规转换失败，尝试强制转换（忽略错误）
            print("🔄 尝试强制转换MP3...")
            force_cmd = [
                'ffmpeg', '-i', mp3_file,
                '-analyzeduration', '100000000',
                '-probesize', '100000000', 
                '-ar', '48000',              # 保持48000Hz采样率
                '-ac', '2',                  # 双声道
                '-sample_fmt', 's16',        # 16位有符号整数
                '-acodec', 'pcm_s16le',      # 指定编码器
                '-f', 'wav',
                '-err_detect', 'ignore_err', # 忽略错误
                '-y',
                wav_file
            ]
            
            force_result = subprocess.run(force_cmd, capture_output=True, text=True, timeout=30)
            
            if force_result.returncode == 0 and os.path.exists(wav_file) and os.path.getsize(wav_file) > 1000:
                print(f"✅ 强制转换成功: {wav_file}")
                return True
            else:
                print(f"❌ 强制转换也失败: {force_result.stderr}")
                return False
    except subprocess.TimeoutExpired:
        print(f"❌ MP3转WAV超时: {mp3_file}")
        return False
    except Exception as e:
        print(f"❌ MP3转WAV异常: {e}")
        return False

class AudioDeviceManager:
    """音频设备管理器 - 🔧 最终架构：ALSA唤醒词 + PulseAudio语音识别"""
    
    def __init__(self):
        self.alsa_recognizer = None
        self.alsa_tts = None
        self.azure_recognizer = None  # PulseAudio+HK麦克风语音识别
        
    def init_devices(self):
        """初始化音频设备 - 按用户最终要求"""
        print("🔧 初始化音频设备...")
        print("📋 最终架构:")
        print("   - 语音唤醒: ALSA + m麦克风")
        print("   - 语音识别: PulseAudio + HK麦克风")
        
        # ALSA设备 (m麦克风 - 语音唤醒)
        self.alsa_recognizer = get_alsa_recognizer()
        if self.alsa_recognizer and self.alsa_recognizer.initialize():
            print("✅ ALSA设备初始化成功 (m麦克风 - 语音唤醒)")
        else:
            print("❌ ALSA设备初始化失败")
            return False
        
        # ALSA TTS
        self.alsa_tts = get_alsa_tts()
        if self.alsa_tts and self.alsa_tts.initialize():
            print("✅ ALSA TTS初始化成功")
        else:
            print("❌ ALSA TTS初始化失败")
            return False
            
        # Azure PulseAudio设备 (HK麦克风 - 语音识别)
        try:
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            speech_config.speech_recognition_language = "zh-CN"
            
            # 🔧 优化语音识别配置
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "2000")
            speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "1000")
            
            # 使用默认麦克风(HK麦克风通过PulseAudio)
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            self.azure_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            print("✅ Azure PulseAudio语音识别器初始化成功 (HK麦克风)")
        except Exception as e:
            print(f"❌ Azure PulseAudio语音识别器初始化失败: {e}")
            return False

        return True

class ThreadA:
    """线程A: 唤醒词监听线程 - 🔧 PulseAudio + HK麦克风 + Azure KeywordRecognizer"""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        self.detector = None
        self.last_wake_time = 0  # 防重复检测
        self.wake_cooldown = 2.0  # 2秒冷却时间
        
    def wake_callback(self, wake_event):
        """唤醒词检测回调"""
        global tts_interrupt_flag
        
        if thread_a_running:
            current_time = time.time()
            
            # 🔧 关键修复：更强的重复检测机制
            time_since_last = current_time - self.last_wake_time
            if time_since_last < self.wake_cooldown:
                print(f"🚫 [线程A] 唤醒词重复检测，忽略 (冷却中: {time_since_last:.1f}s < {self.wake_cooldown}s)")
                return
            
            # 🔧 修复：检查当前是否已经在处理唤醒事件
            global current_state
            if current_state == SystemState.USER_INTERACTION:
                print(f"🚫 [线程A] 系统正在用户交互状态，忽略重复唤醒")
                return
            
            # 🔧 修复：检查唤醒队列是否已经有事件
            if not wake_queue.empty():
                print(f"🚫 [线程A] 唤醒队列已有事件，忽略重复唤醒")
                return
                
            # 更新最后唤醒时间
            self.last_wake_time = current_time
            print(f"🎯 [线程A] 检测到唤醒词: {wake_event.get('text', keyword)}")
            
            # 🔧 关键修复：快速设置中断标志，异步清理音频
            print("🛑 [线程A] 快速设置中断标志")
            
            # 1. 立即设置TTS中断标志
            tts_interrupt_flag = True
            
            # 2. 立即停止音乐播放状态
            global music_playing
            if music_playing:
                music_playing = False
                print("✅ [线程A] 已停止音乐播放状态")
            
            # 🔧 立即放入唤醒队列，不等待清理完成
            wake_queue.put(wake_event)
            print("📤 [线程A] 唤醒事件已立即放入队列")
            
            # 3. 异步执行清理操作，不阻塞唤醒流程
            def async_cleanup():
                try:
                    # 强制释放所有音频权限
                    from audio_priority_manager import get_audio_manager
                    audio_manager = get_audio_manager()
                    audio_manager.force_stop_all()
                    print("✅ [线程A] 异步释放音频权限完成")
                except Exception as e:
                    print(f"⚠️ [线程A] 异步释放权限失败: {e}")
                
                try:
                    # 强制停止音频进程
                    import subprocess
                    subprocess.run(['pkill', '-f', 'aplay'], check=False, capture_output=True)
                    print("✅ [线程A] 异步停止aplay进程完成")
                except Exception as e:
                    print(f"⚠️ [线程A] 异步停止aplay失败: {e}")
                
                try:
                    # 中断流式TTS
                    from streaming_tts_player import get_global_streaming_player
                    streaming_player = get_global_streaming_player()
                    if streaming_player and streaming_player.is_playing:
                        streaming_player.interrupt()
                        print("✅ [线程A] 异步中断流式TTS完成")
                except Exception as e:
                    print(f"⚠️ [线程A] 异步中断流式TTS失败: {e}")
            
            # 启动异步清理线程
            import threading
            cleanup_thread = threading.Thread(target=async_cleanup, daemon=True)
            cleanup_thread.start()
            
            # 🔧 进入冷却期
            print(f"❄️ [线程A] 进入冷却期 ({self.wake_cooldown}秒)")
        else:
            print("🚫 [线程A] 线程A未运行，忽略唤醒")

    def run(self):
        """运行线程A - PulseAudio + HK麦克风 + Azure KeywordRecognizer + wakeword.table"""
        print("🎤 [线程A] 启动PulseAudio + HK麦克风唤醒词检测")
        
        try:
            print("🎤 [线程A] 使用PulseAudio + HK麦克风 + Azure KeywordRecognizer + wakeword.table")
            
            # 创建Azure关键词识别器 - 使用PulseAudio + HK麦克风
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            speech_config.speech_recognition_language = "zh-CN"
            
            # 优化音频配置
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "1000")
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000")
            
            # 🔧 使用PulseAudio + HK麦克风（默认麦克风）
            print("🔧 [线程A] 使用PulseAudio + HK麦克风作为唤醒词输入")
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            keyword_recognizer = speechsdk.KeywordRecognizer(audio_config=audio_config)
            
            # 加载唤醒词模型
            model_file = os.environ.get("WakeupModelFile", "wakeword.table")
            if not os.path.exists(model_file):
                print(f"❌ [线程A] 唤醒词模型文件不存在: {model_file}")
                return
                
            model = speechsdk.KeywordRecognitionModel(model_file)
            print(f"🎤 [线程A] 加载唤醒词模型: {model_file}")
            print(f"🎤 [线程A] 开始持续监听唤醒词: '{keyword}' (PulseAudio + HK麦克风)")
            
            last_recognition_time = 0
            recognition_cooldown = 0.5  # 0.5秒冷却时间
            
            while thread_a_running:
                try:
                    current_time = time.time()
                    
                    # 避免过频繁的识别调用
                    if current_time - last_recognition_time < recognition_cooldown:
                        time.sleep(0.1)
                        continue
                    
                    print(f"🔍 [线程A] 开始唤醒词识别 (PulseAudio + HK麦克风)...")
                    last_recognition_time = current_time
                    
                    try:
                        result_future = keyword_recognizer.recognize_once_async(model)
                        result = result_future.get()
                        
                        if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                            wake_event = {
                                'text': result.text,
                                'timestamp': time.time(),
                                'confidence': 1.0,
                                'source': 'Azure KeywordRecognizer (PulseAudio + HK麦克风)'
                            }
                            print(f"🎯 [线程A] PulseAudio识别到唤醒词: '{result.text}'")
                            self.wake_callback(wake_event)
                            
                            # 唤醒后等待更长时间再继续监听
                            time.sleep(2.0)
                            
                        elif result.reason == speechsdk.ResultReason.Canceled:
                            cancellation_details = result.cancellation_details
                            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                                print(f"⚠️ [线程A] 识别错误: {cancellation_details.error_details}")
                                time.sleep(1.0)
                            else:
                                print("⚠️ [线程A] 识别被取消，继续监听...")
                                time.sleep(0.5)
                        else:
                            # 没有检测到唤醒词，短暂休息后继续
                            time.sleep(0.2)
                            
                    except Exception as timeout_error:
                        print(f"⚠️ [线程A] 识别异常: {timeout_error}")
                        time.sleep(0.5)
                
                except Exception as e:
                    if thread_a_running:
                        print(f"⚠️ [线程A] 唤醒词检测异常: {e}")
                    time.sleep(1.0)
                    
        except Exception as e:
            print(f"❌ [线程A] PulseAudio + HK麦克风初始化失败: {e}")
            print("💡 请检查Azure配置和wakeword.table文件")
        finally:
            print("🛑 [线程A] PulseAudio + HK麦克风线程结束")

class ThreadB:
    """线程B: 用户交互线程 (PulseAudio + HK麦克风)"""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        self.direct_listen_mode = False  # 🔧 新增：直接监听模式标志
        
    def set_direct_listen_mode(self, enabled=True):
        """设置直接监听模式（首次引导时使用）"""
        self.direct_listen_mode = enabled
        print(f"🔧 [线程B] 直接监听模式: {'开启' if enabled else '关闭'}")
    
    def direct_listen_for_first_time(self):
        """首次启动的直接监听模式"""
        print("🎤 [线程B] 首次启动：直接监听用户输入，无需唤醒词")
        
        # 播放wake.mp3提示音
        if not self.play_wake_audio():
            print("⚠️ [线程B] 提示音播放失败")
            return None
            
        # 直接监听用户输入
        user_input = self.listen_user_input()
        
        if user_input and user_input != "restart":
            print(f"📤 [线程B] 首次引导收到用户输入: '{user_input}'")
            input_queue.put(user_input)
            return user_input
        else:
            print("⚠️ [线程B] 首次引导未收到有效输入")
            return None
    
    def play_wake_audio(self):
        """播放唤醒提示音 - 🔧 极速版本"""
        
        wake_wav = "wake.wav"  
        tts_permission_acquired = False
        
        try:
            print("⚡ [线程B] 立即播放wake.wav，无需等待")
            
            # 🔧 关键修复：立即申请TTS权限（线程A已经释放了所有权限）
            from audio_priority_manager import AudioPriority, request_audio_access, release_audio_access
            
            if request_audio_access(AudioPriority.TTS, "唤醒提示音播放"):
                print("✅ [线程B] 立即获得音频播放权限")
                tts_permission_acquired = True
                
                # 🔧 关键修复：立即播放wake.wav，最多重试2次
                max_retries = 2
                for retry in range(max_retries):
                    try:
                        cmd = ['aplay', '-D', 'hw:1,0', wake_wav]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                        if result.returncode == 0:
                            print("✅ [线程B] wake.wav播放完成")
                            break
                        else:
                            print(f"❌ [线程B] wake.wav播放失败 (重试{retry+1}/{max_retries}): {result.stderr}")
                            if retry < max_retries - 1:
                                # 快速重试
                                import time
                                time.sleep(0.1)
                    except Exception as aplay_e:
                        print(f"❌ [线程B] aplay异常 (重试{retry+1}/{max_retries}): {aplay_e}")
                        if retry < max_retries - 1:
                            time.sleep(0.2)
            else:
                print("⚠️ [线程B] 无法获得音频播放权限")
                
        except Exception as e:
            print(f"❌ [线程B] 播放唤醒提示音整体异常: {e}")
        
        finally:
            # 🔧 关键修复：确保TTS权限被释放
            if tts_permission_acquired:
                try:
                    from audio_priority_manager import AudioPriority, release_audio_access
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
        
        # 🔧 关键修复：wake.wav播放完成后，异步清理线程C和流式语音请求
        print("🛑 [线程B] wake.wav播放完成，启动异步清理")
        
        def async_cleanup_after_wake():
            """异步清理操作，不阻塞后续交互"""
            try:
                # 1. 强制杀死当前运行的线程C
                global current_c_thread, tts_interrupt_flag
                if current_c_thread and current_c_thread.is_alive():
                    print(f"🛑 [线程B异步] 强制终止线程C: {current_c_thread.ident}")
                    tts_interrupt_flag = True
                    interrupt_queue.put("interrupt")
                    try:
                        current_c_thread.join(timeout=0.5)  # 减少等待时间
                        if current_c_thread.is_alive():
                            print(f"⚠️ [线程B异步] 线程C未能及时终止: {current_c_thread.ident}")
                        else:
                            print(f"✅ [线程B异步] 线程C已成功终止: {current_c_thread.ident}")
                    except Exception as thread_e:
                        print(f"⚠️ [线程B异步] 终止线程C异常: {thread_e}")
                
                # 2. 强制停止所有流式TTS播放
                try:
                    from streaming_tts_player import get_global_streaming_player
                    streaming_player = get_global_streaming_player()
                    if streaming_player and streaming_player.is_playing:
                        streaming_player.interrupt()
                        print("✅ [线程B异步] 流式TTS播放已中断")
                except Exception as streaming_e:
                    print(f"⚠️ [线程B异步] 中断流式TTS失败: {streaming_e}")
                
                # 3. 强制停止ALSA TTS播放
                try:
                    from alsa_cosyvoice_tts import get_alsa_tts
                    alsa_tts = get_alsa_tts()
                    if alsa_tts:
                        alsa_tts.interrupt_playback()
                        print("✅ [线程B异步] ALSA TTS播放已中断")
                except Exception as alsa_e:
                    print(f"⚠️ [线程B异步] 中断ALSA TTS失败: {alsa_e}")
                
                # 4. 清空interrupt_queue，避免影响新的交互
                cleared_interrupts = 0
                while not interrupt_queue.empty():
                    try:
                        interrupt_queue.get_nowait()
                        cleared_interrupts += 1
                    except queue.Empty:
                        break
                if cleared_interrupts > 0:
                    print(f"🧹 [线程B异步] 已清理{cleared_interrupts}个中断信号")
                
                print("✅ [线程B异步] 清理完成")
                
            except Exception as e:
                print(f"⚠️ [线程B异步] 清理异常: {e}")
        
        # 启动异步清理，不阻塞用户交互
        import threading
        cleanup_thread = threading.Thread(target=async_cleanup_after_wake, daemon=True)
        cleanup_thread.start()
        print("🚀 [线程B] 异步清理已启动，继续用户交互")
        
        return True
    
    def convert_mp3_to_wav(self, mp3_file, wav_file):
        """转换MP3为WAV格式"""
        try:
            cmd = ['ffmpeg', '-i', mp3_file, '-ar', '48000', '-ac', '2', '-sample_fmt', 's16', '-f', 'wav', '-y', wav_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ [线程B] MP3转WAV成功: {wav_file}")
                return True
            else:
                print(f"❌ [线程B] MP3转WAV失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ [线程B] MP3转WAV异常: {e}")
            return False
    
    def listen_user_input(self):
        """监听用户输入 - 🔧 使用PulseAudio + HK麦克风"""
        print("🎤 [线程B] 开始监听用户输入 (PulseAudio + HK麦克风)")
        
        timeout = 8.0
        start_time = time.time()
        check_interval = 0.5  # 每0.5秒检查一次唤醒队列
        last_check_time = start_time
        
        # 🔧 增加重试机制
        max_retries = 3
        retry_count = 0
        
        while time.time() - start_time < timeout:
            current_time = time.time()
            
            # 减少唤醒队列检查频率
            if current_time - last_check_time >= check_interval:
                try:
                    wake_queue.get_nowait()
                    print("🔄 [线程B] 检测到新唤醒事件，重新开始")
                    return "restart"
                except queue.Empty:
                    pass
                last_check_time = current_time
            
            # 🔧 使用Azure PulseAudio语音识别器 (HK麦克风)
            try:
                print(f"🎤 [线程B] 尝试PulseAudio语音识别 (第{retry_count + 1}次)...")
                
                # 🔧 确保识别器状态正确，短暂等待
                time.sleep(0.1)
                
                # 设置较短的超时，避免长时间等待
                result = self.audio_manager.azure_recognizer.recognize_once()
                
                print(f"🔍 [线程B] 识别结果原因: {result.reason}")
                
                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    user_input = result.text.strip()
                    if user_input:  # 确保不是空字符串
                        print(f"🗣️ [线程B] PulseAudio识别到用户输入: '{user_input}'")
                        return user_input
                    else:
                        print("⚠️ [线程B] 识别到空内容，继续监听...")
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    print("🔇 [线程B] 未匹配到语音，继续监听...")
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"⚠️ [线程B] 已重试{max_retries}次，仍无匹配")
                        retry_count = 0  # 重置重试计数
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation = result.cancellation_details
                    print(f"⚠️ [线程B] 识别被取消: {cancellation.reason}")
                    if cancellation.reason == speechsdk.CancellationReason.Error:
                        print(f"❌ [线程B] 识别错误: {cancellation.error_details}")
                else:
                    print(f"⚠️ [线程B] 未知识别结果: {result.reason}")
                    
                # 短暂休息后继续
                time.sleep(0.2)
                    
            except Exception as e:
                print(f"⚠️ [线程B] PulseAudio语音识别异常: {e}")
                retry_count += 1
                time.sleep(0.5)
        
        print(f"🔇 [线程B] 监听超时({timeout}秒)，未检测到用户输入")
        # 🎭 没有监听到用户说话时发送结束表情 (2-2-0)
        try:
            send_end_emotion()
        except Exception as emotion_e:
            print(f"⚠️ [线程B] 监听超时时发送结束表情失败: {emotion_e}")
        return None
    
    def run(self):
        """运行线程B"""
        global current_state, current_audio_state
        
        print("🎧 [线程B] 用户交互线程已启动")
        
        while thread_b_running:
            try:
                # 等待唤醒事件
                wake_event = wake_queue.get(timeout=1)
                current_state = SystemState.USER_INTERACTION
                
                print(f"🔊 [线程B] 收到唤醒事件，开始用户交互: {wake_event}")
                
                # 🔧 清空唤醒队列中可能的重复事件
                queue_cleared = 0
                while True:
                    try:
                        wake_queue.get_nowait()
                        queue_cleared += 1
                    except queue.Empty:
                        break
                if queue_cleared > 0:
                    print(f"🧹 [线程B] 清理了{queue_cleared}个重复唤醒事件")
                
                # 1. 播放wake.mp3 (必须播放完)
                if not self.play_wake_audio():
                    current_state = SystemState.WAKE_LISTENING
                    continue
                
                # 2. 监听用户输入
                print("🎤 [线程B] 开始监听用户输入...")
                user_input = self.listen_user_input()
                
                # 3. 处理结果
                if user_input == "restart":
                    print("🔄 [线程B] 重新开始监听")
                    continue
                elif user_input:
                    # 有用户输入，发送给C线程
                    print(f"📤 [线程B] 发送用户输入给主循环: '{user_input}'")
                    input_queue.put(user_input)
                    print("✅ [线程B] 用户输入已发送到队列")
                else:
                    # 没有用户输入，恢复之前的播放状态
                    if current_audio_state:
                        print("▶️ [线程B] 恢复之前的播放状态")
                        # 这里可以实现恢复逻辑
                    else:
                        print("💤 [线程B] 没有用户输入，返回空闲状态")
                
                current_state = SystemState.WAKE_LISTENING
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ [线程B] 异常: {e}")
                current_state = SystemState.WAKE_LISTENING

class ThreadC:
    """线程C: AI对话线程"""
    
    def __init__(self, audio_manager, user_input):
        self.audio_manager = audio_manager
        self.user_input = user_input
        self.thread_id = threading.current_thread().ident
        
    def check_interrupt(self):
        """检查中断信号"""
        try:
            interrupt_queue.get_nowait()
            return True
        except queue.Empty:
            return False
    
    def generate_ai_response(self):
        """生成AI回复"""
        global messages
        
        try:
            messages.append({"role": "user", "content": self.user_input})
            
            # 🔧 优先级1：检查功能命令（最高优先级）
            try:
                from function_handlers import handle_voice_function_command
                
                function_success, function_response = handle_voice_function_command(self.user_input)
                if function_success and function_response:
                    print(f"🎯 [线程C-{self.thread_id}] 识别为功能命令: {self.user_input}")
                    messages.append({"role": "assistant", "content": function_response})
                    
                    # 记录功能命令对话
                    try:
                        from user_memory import record_conversation
                        record_conversation(self.user_input, function_response, "function")
                    except Exception as record_e:
                        print(f"⚠️ 记录功能命令对话失败: {record_e}")
                    
                    return function_response
                    
            except Exception as func_e:
                print(f"⚠️ [线程C-{self.thread_id}] 功能命令处理异常: {func_e}")
            
            # 🔧 优先级2：检查是否是用户信息收集阶段
            try:
                from user_memory import get_user_info_status, extract_user_info_from_response, update_user_info
                
                info_complete, missing_fields = get_user_info_status()
                if not info_complete:
                    print(f"🔍 [线程C-{self.thread_id}] 用户信息不完整，尝试提取信息")
                    
                    # 从用户输入中提取个人信息
                    extracted_info = extract_user_info_from_response(self.user_input)
                    if extracted_info:
                        print(f"📝 [线程C-{self.thread_id}] 提取到用户信息: {extracted_info}")
                        update_user_info(extracted_info)
                        
                        # 重新检查信息完整性
                        info_complete, remaining_fields = get_user_info_status()
                        if info_complete:
                            # 信息收集完成，生成确认回复
                            user_name = extracted_info.get('name', '')
                            user_grade = extracted_info.get('grade', '')
                            response = f"好的，{user_name}！我记住了你在读{user_grade}。"
                            response += "现在我可以更好地为你服务了！有什么我可以帮助你的吗？"
                            messages.append({"role": "assistant", "content": response})
                            
                            # 记录对话
                            try:
                                from user_memory import record_conversation
                                record_conversation(self.user_input, response, "user_info_collection")
                            except Exception as record_e:
                                print(f"⚠️ 记录用户信息对话失败: {record_e}")
                            
                            return response
                        else:
                            # 还需要更多信息
                            if 'name' in remaining_fields:
                                response = "好的！请问我应该怎么称呼你呢？"
                            elif 'grade' in remaining_fields:
                                if extracted_info.get('name'):
                                    response = f"很高兴认识你，{extracted_info['name']}！请问你现在读几年级呢？"
                                else:
                                    response = "请问你现在读几年级呢？"
                            else:
                                response = "请问你的名字和年级是什么呢？"
                            
                            messages.append({"role": "assistant", "content": response})
                            return response
                    else:
                        # 没有提取到信息，询问缺失的信息
                        if 'name' in missing_fields and 'grade' in missing_fields:
                            response = "你好！我是广和通，你的AI助手。请问我该怎么称呼你？你现在读几年级？"
                        elif 'name' in missing_fields:
                            response = "请问我应该怎么称呼你呢？"
                        elif 'grade' in missing_fields:
                            response = "请问你现在读几年级呢？"
                        else:
                            response = "请告诉我你的名字和年级，这样我就能更好地为你服务了！"
                        
                        messages.append({"role": "assistant", "content": response})
                        return response
                        
            except Exception as info_e:
                print(f"⚠️ [线程C-{self.thread_id}] 用户信息处理异常: {info_e}")
            
            # 🔧 优先级3：集成skill功能 - 获取可用工具（普通对话处理）
            from xiaoxin2_skill import getTools
            available_tools = getTools()
            
            # 🎭 根据对话类型选择系统提示词
            # 检查是否需要用户信息收集
            from user_memory import get_user_info_status
            info_complete, _ = get_user_info_status()
            
            if info_complete:
                # 用户信息完整，使用带表情的提示词
                system_content = EMOTION_SYSTEM_PROMPT
                print(f"🎭 [线程C-{self.thread_id}] 使用带表情的AI提示词")
            else:
                # 用户信息不完整，使用普通提示词
                system_content = getSystemPrompt()
                print(f"📝 [线程C-{self.thread_id}] 使用普通AI提示词（信息收集阶段）")
            
            sysmesg = {"role": "system", "content": system_content}
            
            # 第一次调用，可能包含函数调用
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[sysmesg] + messages[-10:],
                tools=available_tools,  # 添加工具支持
                temperature=0.6,
                max_tokens=500,
                timeout=30
            )
            
            # 处理响应
            choice = response.choices[0]
            
            # 检查是否有函数调用
            if choice.message.tool_calls:
                print(f"🔧 [线程C-{self.thread_id}] 检测到函数调用")
                
                # 添加助手消息
                messages.append({
                    "role": "assistant", 
                    "content": choice.message.content,
                    "tool_calls": choice.message.tool_calls
                })
                
                # 记录是否有音乐播放函数调用
                has_playmusic_call = False
                
                # 执行函数调用
                for tool_call in choice.message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🛠️ [线程C-{self.thread_id}] 执行函数: {function_name}")
                    
                    # 🔧 检测音乐播放函数
                    if function_name == "playmusic":
                        has_playmusic_call = True
                    
                    # 动态调用skill函数
                    try:
                        import xiaoxin2_skill
                        if hasattr(xiaoxin2_skill, function_name):
                            function_result = getattr(xiaoxin2_skill, function_name)(**function_args)
                            print(f"✅ [线程C-{self.thread_id}] 函数执行结果: {function_result}")
                        else:
                            function_result = f"函数 {function_name} 不存在"
                            print(f"❌ [线程C-{self.thread_id}] 函数不存在: {function_name}")
                    except Exception as e:
                        function_result = f"函数执行失败: {str(e)}"
                        print(f"❌ [线程C-{self.thread_id}] 函数执行异常: {e}")
                    
                    # 添加函数结果消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_result
                    })
                
                # 🔧 音乐播放函数的特殊处理：直接返回函数结果，不要AI废话
                if has_playmusic_call:
                    print(f"🎵 [线程C-{self.thread_id}] 检测到音乐播放，直接返回函数结果")
                    # 🔧 关键修复：直接返回函数执行结果，忽略AI的长回复
                    for msg in reversed(messages):  # 从最新的消息开始找
                        if msg.get("role") == "tool" and "正在为您播放" in msg.get("content", ""):
                            ai_reply = msg["content"]
                            print(f"🎵 [线程C-{self.thread_id}] 找到音乐播放结果: {ai_reply}")
                            
                            # 🔧 重要修复：替换掉AI的长回复，只保留简洁的播放提示
                            # 移除之前添加的包含长回复的assistant消息
                            if messages and messages[-1].get("role") == "assistant" and messages[-1].get("tool_calls"):
                                print(f"🗑️ [线程C-{self.thread_id}] 移除AI的长回复，只保留简洁播放提示")
                                messages.pop()  # 移除包含长回复的消息
                            
                            messages.append({"role": "assistant", "content": ai_reply})
                            
                            # 🔧 记录音乐播放对话
                            try:
                                from user_memory import record_conversation
                                record_conversation(self.user_input, ai_reply, "music")
                            except Exception as record_e:
                                print(f"⚠️ 记录音乐对话失败: {record_e}")
                            
                            return ai_reply
                    
                    # 如果没有找到播放结果，检查是否有错误消息
                    for msg in reversed(messages):
                        if msg.get("role") == "tool" and ("抱歉" in msg.get("content", "") or "没有找到" in msg.get("content", "")):
                            ai_reply = msg["content"]
                            print(f"🎵 [线程C-{self.thread_id}] 找到音乐搜索失败结果: {ai_reply}")
                            messages.append({"role": "assistant", "content": ai_reply})
                            
                            try:
                                from user_memory import record_conversation
                                record_conversation(self.user_input, ai_reply, "music")
                            except Exception as record_e:
                                print(f"⚠️ 记录音乐对话失败: {record_e}")
                            
                            return ai_reply
                    
                    # 如果没有找到任何相关结果，使用默认回复
                    ai_reply = "好的，正在为您播放音乐！"
                    print(f"⚠️ [线程C-{self.thread_id}] 未找到具体播放结果，使用默认回复")
                    messages.append({"role": "assistant", "content": ai_reply})
                    
                    # 记录对话
                    try:
                        from user_memory import record_conversation
                        record_conversation(self.user_input, ai_reply, "music")
                    except Exception as record_e:
                        print(f"⚠️ 记录音乐对话失败: {record_e}")
                    
                    return ai_reply
                
                # 非音乐播放函数：正常处理，获取AI的最终回复
                final_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[sysmesg] + messages[-10:],
                    temperature=0.6,
                    max_tokens=500,
                    timeout=30
                )
                
                ai_reply = final_response.choices[0].message.content
                messages.append({"role": "assistant", "content": ai_reply})
                
                # 🔧 记录普通对话
                try:
                    from user_memory import record_conversation
                    record_conversation(self.user_input, ai_reply, "general")
                except Exception as record_e:
                    print(f"⚠️ 记录对话失败: {record_e}")
                
                return ai_reply
            else:
                # 没有函数调用，直接返回回复
                ai_reply = choice.message.content
                messages.append({"role": "assistant", "content": ai_reply})
                
                # 🔧 记录普通对话
                try:
                    from user_memory import record_conversation
                    record_conversation(self.user_input, ai_reply, "general")
                except Exception as record_e:
                    print(f"⚠️ 记录对话失败: {record_e}")
                
                return ai_reply
            
        except Exception as e:
            print(f"❌ [线程C-{self.thread_id}] AI生成失败: {e}")
            return "抱歉，我遇到了一些技术问题。"
    
    def play_tts_response(self, response):
        """播放TTS回复（流式播放）"""
        print(f"🎤 [线程C-{self.thread_id}] 开始播放TTS回复: {response[:50]}...")
        
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
            # 使用流式TTS播放
            from streaming_tts_player import get_streaming_player
            streaming_player = get_streaming_player()
            
            if streaming_player:
                # 分句进行流式播放
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
    
    def run(self):
        """运行线程C"""
        global current_state, tts_interrupt_flag
        
        current_state = SystemState.AI_PROCESSING
        
        print(f"🤖 [线程C-{self.thread_id}] 开始处理用户输入: {self.user_input}")
        
        # 🔧 在开始处理前先检查是否已被中断
        if self.check_interrupt():
            print(f"🛑 [线程C-{self.thread_id}] 启动时发现中断信号，立即退出")
            current_state = SystemState.WAKE_LISTENING
            return
        
        # 🔧 只有在没有中断的情况下才清除TTS中断标志
        tts_interrupt_flag = False
        print(f"🔄 [线程C-{self.thread_id}] 清除TTS中断标志，开始新对话")
        
        # 🎭 确保停止任何正在进行的流式TTS播放
        try:
            from streaming_tts_player import get_global_streaming_player
            streaming_player = get_global_streaming_player()
            if streaming_player.is_playing:
                streaming_player.interrupt()
                print(f"🛑 [线程C-{self.thread_id}] 已停止之前的流式TTS播放")
        except Exception as streaming_e:
            print(f"⚠️ [线程C-{self.thread_id}] 停止流式TTS播放失败: {streaming_e}")
        
        try:
            
            # 生成AI回复前再次检查中断
            if self.check_interrupt():
                print(f"🛑 [线程C-{self.thread_id}] AI处理前被中断")
                return
                
            # 生成AI回复 
            ai_response = self.generate_ai_response()
            print(f"🤖 [线程C-{self.thread_id}] AI回复: {ai_response[:50]}...")
            
            # AI处理完成后，开始播放前检查中断
            if self.check_interrupt():
                print(f"🛑 [线程C-{self.thread_id}] 在播放前被中断")
                return
            
            # 播放回复
            current_state = SystemState.AUDIO_PLAYING
            
           
            
            self.play_tts_response(ai_response)
            
            print(f"✅ [线程C-{self.thread_id}] 对话完成")
            
        except Exception as e:
            print(f"❌ [线程C-{self.thread_id}] 异常: {e}")
        finally:
            current_state = SystemState.WAKE_LISTENING
            

def play_mp3_audio(mp3_file, audio_type="music"):
    """
    播放MP3音频文件 - 🔧 修复版本：使用非阻塞MP3播放
    
    Args:
        mp3_file: MP3文件路径
        audio_type: 音频类型 ("music", "effect", etc.)
    
    Returns:
        bool: 播放是否成功启动
    """
    global music_playing, music_paused
    
    try:
        print(f"🎵 开始播放MP3音频: {mp3_file} (类型: {audio_type})")
        
        # 设置播放状态
        if audio_type == "music":
            music_playing = True
            music_paused = False
        
        # 🔧 直接使用audio_player的MP3播放功能（非阻塞）
        from audio_player import play_audio
        
        # 检查文件是否存在
        if not os.path.exists(mp3_file):
            print(f"❌ 音频文件不存在: {mp3_file}")
            if audio_type == "music":
                music_playing = False
                music_paused = False
            return False
        
        # 🔧 使用非阻塞播放（让音乐在后台播放）
        success = play_audio(mp3_file)
        
        if success:
            print(f"✅ 音乐播放成功启动: {mp3_file}")
            # 注意：这里不重置music_playing，因为音乐正在后台播放
            return True
        else:
            print(f"❌ 音乐播放启动失败: {mp3_file}")
            # 重置播放状态
            if audio_type == "music":
                music_playing = False
                music_paused = False
            return False
        
    except Exception as e:
        print(f"❌ 播放MP3失败: {e}")
        
        # 重置播放状态
        if audio_type == "music":
            music_playing = False
            music_paused = False
        
        return False

def play_mp3_audio_blocking_with_interrupt(mp3_file, audio_type="music"):
    """
    播放MP3音频文件 - 🔧 阻塞播放版本，支持唤醒中断
    
    Args:
        mp3_file: MP3文件路径
        audio_type: 音频类型 ("music", "effect", etc.)
    
    Returns:
        bool: 播放是否成功完成（False表示被中断）
    """
    global music_playing, music_paused, tts_interrupt_flag
    
    try:
        print(f"🎵 开始阻塞播放MP3音频: {mp3_file} (类型: {audio_type})")
        
        # 设置播放状态
        if audio_type == "music":
            music_playing = True
            music_paused = False
        
        # 检查文件是否存在
        if not os.path.exists(mp3_file):
            print(f"❌ 音频文件不存在: {mp3_file}")
            if audio_type == "music":
                music_playing = False
                music_paused = False
            return False
        
        # 转换MP3为WAV格式（因为我们的音频播放器主要支持WAV）
        wav_file = f"{mp3_file}.wav"
        if convert_mp3_to_wav(mp3_file, wav_file):
            print(f"✅ MP3转WAV成功: {wav_file}")
            
            # 使用阻塞播放，同时监控中断标志
            success = play_audio_with_interrupt_check(wav_file, audio_type)
            
            # 清理临时WAV文件
            try:
                if os.path.exists(wav_file):
                    os.remove(wav_file)
                    print(f"🗑️ 已清理临时WAV文件: {wav_file}")
            except Exception as e:
                print(f"⚠️ 清理WAV文件失败: {e}")
                
            return success
        else:
            print(f"❌ MP3转WAV失败: {mp3_file}")
            return False
        
    except Exception as e:
        print(f"❌ 阻塞播放MP3失败: {e}")
        
        # 重置播放状态
        if audio_type == "music":
            music_playing = False
            music_paused = False
    
    return False

def play_audio_with_interrupt_check(audio_file, audio_type="music"):
    """
    播放音频文件，支持唤醒中断检测
    
    Args:
        audio_file: 音频文件路径
        audio_type: 音频类型
    
    Returns:
        bool: 是否播放完成（False表示被中断）
    """
    global tts_interrupt_flag, music_playing, music_paused
    
    try:
        import threading
        import time
        from audio_player import play_audio_blocking
        
        # 播放状态标志
        playback_completed = threading.Event()
        playback_interrupted = threading.Event()
        
        def audio_playback_thread():
            """音频播放线程"""
            try:
                print(f"🎵 开始播放音频: {audio_file}")
                success = play_audio_blocking(audio_file)
                if success:
                    print(f"✅ 音频播放线程完成: {audio_file}")
                    playback_completed.set()
                else:
                    print(f"❌ 音频播放线程失败: {audio_file}")
                    playback_interrupted.set()
            except Exception as e:
                print(f"❌ 音频播放线程异常: {e}")
                playback_interrupted.set()
        
        # 启动播放线程
        play_thread = threading.Thread(target=audio_playback_thread, daemon=True)
        play_thread.start()
        
        # 主线程监控中断信号
        check_interval = 0.5          # 🔧 修改检查频率：音乐播放时更频繁检查中断（每100ms），其他音频每500ms
        check_interval = 0.1 if audio_type == "music" else 0.5
        
        while play_thread.is_alive():
            # 🔧 音乐播放时检查唤醒中断 - 修复版：立即响应中断
            if audio_type == "music":
                # 检查TTS中断标志（唤醒词触发）
                if tts_interrupt_flag:
                    print(f"🛑 检测到唤醒中断，立即停止音乐播放: {audio_file}")
                    
                    # 立即停止所有音频播放
                    from audio_player import stop_all_audio
                    stop_all_audio()
                    
                    # 重置音乐播放状态
                    global music_playing, music_paused
                    music_playing = False
                    music_paused = False
                    
                    # 设置中断标志
                    playback_interrupted.set()
                    
                    # 等待播放线程结束
                    play_thread.join(timeout=1)  # 减少等待时间，快速响应
                    
                    print(f"✅ 音乐播放已被唤醒中断，状态已重置")
                    return False
                
            else:
                # 🔧 非音乐类型（如TTS）仍然检查中断标志
                if tts_interrupt_flag:
                    print(f"🛑 检测到中断，停止{audio_type}播放: {audio_file}")
                    
                    # 停止所有音频播放
                    from audio_player import stop_all_audio
                    stop_all_audio()
                    
                    # 设置中断标志
                    playback_interrupted.set()
                    
                    # 等待播放线程结束
                    play_thread.join(timeout=2)
                    
                    return False
            
            time.sleep(check_interval)
        
        # 检查播放结果
        if playback_completed.is_set():
            print(f"✅ 音频播放成功完成: {audio_file}")
            return True
        else:
            print(f"⚠️ 音频播放未正常完成: {audio_file}")
            return False
            
    except Exception as e:
        print(f"❌ 音频播放中断检测异常: {e}")
        return False
    finally:
        # 🔧 只在播放真正完成或被中断时重置状态
        if audio_type == "music":
            # 如果播放完成或被中断，重置状态
            if playback_completed.is_set() or playback_interrupted.is_set():
                music_playing = False
                music_paused = False
                print(f"🔄 音乐播放状态已重置")
            else:
                # 如果播放异常结束，也重置状态
                music_playing = False
                music_paused = False
                print(f"⚠️ 音乐播放异常结束，状态已重置")

def stop_music_playback():
    """停止音乐播放 - 增强版：确保彻底停止所有音频"""
    global music_playing, music_paused, tts_interrupt_flag
    
    try:
        print("🛑 停止音乐播放（增强版）")
        
        # 设置中断标志
        tts_interrupt_flag = True
        
        # 重置音乐状态
        music_playing = False
        music_paused = False
        
        # 停止所有音频播放进程
        from audio_player import stop_all_audio
        stopped_count = stop_all_audio()
        
        # 额外的pygame停止（如果存在）
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.stop()
        except:
            pass
        
        print(f"✅ 音乐播放已彻底停止（停止了{stopped_count}个进程）")
        return True
    except Exception as e:
        print(f"❌ 停止音乐播放失败: {e}")
        return False

def handle_first_time_setup(audio_manager):
    """处理首次启动的用户信息收集"""
    print("🆕 开始首次用户信息收集流程")
    
    try:
        # 创建临时的ThreadB实例用于首次交互
        temp_thread_b = ThreadB(audio_manager)
        
        # 播放wake.mp3提示音
        print("🎵 播放交互提示音...")
        if not temp_thread_b.play_wake_audio():
            print("⚠️ 提示音播放失败")
            return False
            
        # 直接监听用户输入，无需唤醒词
        print("🎤 开始监听用户信息输入...")
        user_input = temp_thread_b.listen_user_input()
        
        if user_input and user_input != "restart":
            print(f"📥 收到首次用户输入: '{user_input}'")
            
            # 创建ThreadC处理用户信息
            thread_c = ThreadC(audio_manager, user_input)
            c_thread = threading.Thread(target=thread_c.run, daemon=True)
            c_thread.start()
            
            # 等待处理完成
            c_thread.join(timeout=30)
            
            print("✅ 首次用户信息收集完成")
            return True
        else:
            print("⚠️ 首次用户信息收集失败")
            return False
            
    except Exception as e:
        print(f"❌ 首次启动处理异常: {e}")
        return False

def main():
    """主函数: 三线程架构"""
    global thread_a_running, thread_b_running, current_c_thread
    
    print("🚀 启动三线程语音助手架构")
    print("📋 架构说明：")
    print("   线程A: PulseAudio + HK麦克风 → 持续监听唤醒词 (Azure KeywordRecognizer + wakeword.table)")
    print("   线程B: PulseAudio + HK麦克风 → 用户交互")
    print("   线程C: AI对话处理 → 可中断/恢复")
    
    # 初始化设备
    audio_manager = AudioDeviceManager()
    if not audio_manager.init_devices():
        print("❌ 音频设备初始化失败")
        return
    
    
    # 🔧 个性化启动流程
    first_time_setup_completed = False
    try:
        from user_memory import get_user_info_status, generate_welcome_response
        
        # 检查是否需要个性化启动
        use_personalized_startup = os.environ.get("use_personalized_startup", "true").lower() == "true"
        startup_audio = os.environ.get("startup_audio", "wake_new.mp3")
        
        if use_personalized_startup:
            # 检查用户信息完整性
            info_complete, missing_fields = get_user_info_status()
            
            if not info_complete:
                print(f"🆕 首次启动或用户信息不完整，使用个性化引导流程")
                print(f"📝 缺少信息: {missing_fields}")
                
                # 播放个性化引导音频
                if os.path.exists(startup_audio):
                    print(f"🎵 播放个性化引导音频: {startup_audio}")
                    # 转换并播放
                    startup_wav = startup_audio.replace('.mp3', '.wav')
                    if os.path.exists(startup_wav) or convert_mp3_to_wav(startup_audio, startup_wav):
                        play_audio_blocking(startup_wav)
                        print("✅ 个性化引导音频播放完成")
                        
                        # 🔧 首次引导后直接开始监听用户输入，不需要唤醒词
                        print("🎤 首次引导：直接开始监听用户回答，无需唤醒词")
                        
                        # 创建临时的线程B实例进行首次交互
                        temp_thread_b = ThreadB(audio_manager)

                        # 🔧 首次启动时不重复播放wake.wav，因为已经播放了个性化引导音频
                        print("🎤 首次启动：跳过wake.wav播放，直接开始监听用户信息...")

                        # 直接监听用户输入
                        user_input = temp_thread_b.listen_user_input()
                        
                        if user_input and user_input != "restart":
                            print(f"📥 收到首次用户输入: '{user_input}'")
                            
                            # 直接处理用户信息
                            thread_c = ThreadC(audio_manager, user_input)
                            c_thread = threading.Thread(target=thread_c.run, daemon=True)
                            c_thread.start()
                            c_thread.join(timeout=30)  # 等待处理完成
                            
                            print("✅ 首次用户信息收集完成")
                            first_time_setup_completed = True
                        else:
                            print("⚠️ 首次用户信息收集失败，继续正常流程")
                        
                    else:
                        print("❌ 个性化引导音频转换失败")
                else:
                    print(f"⚠️ 个性化引导音频不存在: {startup_audio}")
                    # 回退到默认流程
                    use_personalized_startup = False
            else:
                print("✅ 用户信息完整，跳过个性化引导")
                # 播放个性化欢迎语
                welcome_response = generate_welcome_response()
                print(f"🎙️ 个性化欢迎语: {welcome_response}")
                
                # 使用TTS播放欢迎语（可选）
                try:
                    from alsa_cosyvoice_tts import text_to_speech_alsa
                    text_to_speech_alsa(welcome_response)
                    print("✅ 个性化欢迎语播放完成")
                except Exception as tts_e:
                    print(f"⚠️ TTS播放欢迎语失败: {tts_e}")
        
        # 如果不使用个性化启动或回退，播放默认音频
        if not use_personalized_startup and not first_time_setup_completed:
            print("🎵 播放默认启动音频...")
            default_audio = "wakeup_word.mp3"
            if os.path.exists(default_audio):
                # 转换并播放
                if os.path.exists("wakeup_word.wav") or convert_mp3_to_wav(default_audio, "wakeup_word.wav"):
                    print("🎵 播放启动欢迎音频: wakeup_word.wav")
                    play_audio_blocking("wakeup_word.wav")
                    print("✅ 启动欢迎音频播放完成")
                else:
                    print("❌ wakeup_word.mp3转换失败")
            else:
                print("⚠️ wakeup_word.mp3文件不存在，跳过欢迎音频")
                
    except Exception as e:
        print(f"⚠️ 个性化启动流程失败: {e}")
        print("🔄 回退到默认启动流程")
    
    # 创建线程实例
    thread_a = ThreadA(audio_manager)
    thread_b = ThreadB(audio_manager)
    
    # 启动线程A和B
    threading.Thread(target=thread_a.run, daemon=True).start()
    threading.Thread(target=thread_b.run, daemon=True).start()
    
    print("✅ 线程A和线程B已启动")
    print(f"🎤 语音助手已启动，说'{keyword}'来唤醒")
    
    # 主循环: 处理用户输入，启动C线程
    try:
        print("🔄 主循环开始，等待用户输入...")
        while True:
            try:
                # 等待用户输入
                user_input = input_queue.get(timeout=1)
                
                print(f"📥 主循环收到用户输入: '{user_input}'")
                
                # 🔧 智能中断：只中断TTS，不中断音乐播放
                global tts_interrupt_flag, music_playing
                
                # 检查是否有正在运行的C线程（通常是TTS播放）
                if current_c_thread and current_c_thread.is_alive():
                    print(f"🛑 检测到正在运行的C线程，发送中断信号")
                    tts_interrupt_flag = True
                    print("🛑 设置TTS中断标志（针对当前对话）")

                    # 🔧 立即中断流式TTS播放
                    try:
                        from streaming_tts_player import get_global_streaming_player
                        streaming_player = get_global_streaming_player()
                        if streaming_player and streaming_player.is_playing:
                            print("🛑 立即中断流式TTS播放")
                            streaming_player.interrupt()
                    except Exception as e:
                        print(f"⚠️ 中断流式TTS失败: {e}")

                    # 强制停止所有ALSA TTS播放
                    try:
                        from alsa_cosyvoice_tts import get_alsa_tts
                        alsa_tts = get_alsa_tts()
                        if alsa_tts:
                            alsa_tts.interrupt_playback()
                            print("✅ 强制中断ALSA TTS播放")
                    except Exception as e:
                        print(f"⚠️ 中断ALSA TTS失败: {e}")

                    print(f"🛑 终止当前C线程 (ID: {current_c_thread.ident})")
                    interrupt_queue.put("interrupt")
                    try:
                        # 减少等待时间，提高响应速度
                        current_c_thread.join(timeout=2)
                        if current_c_thread.is_alive():
                            print(f"⚠️ C线程 {current_c_thread.ident} 仍在运行，但继续处理新请求")
                        else:
                            print(f"✅ C线程 {current_c_thread.ident} 已成功终止")
                    except Exception as e:
                        print(f"⚠️ 等待C线程结束异常: {e}")
                else:
                    print("💡 没有正在运行的C线程，无需中断")
                
                # 清空interrupt_queue，避免影响新线程
                cleared_interrupts = 0
                while not interrupt_queue.empty():
                    try:
                        interrupt_queue.get_nowait()
                        cleared_interrupts += 1
                    except queue.Empty:
                        break
                if cleared_interrupts > 0:
                    print(f"🧹 已清理{cleared_interrupts}个中断信号")
                
                # 🔧 为新对话重置TTS中断标志
                tts_interrupt_flag = False
                print("🔄 重置TTS中断标志，准备启动新对话")
                
                # 启动新的C线程
                print(f"🚀 准备启动C线程处理: '{user_input}'")
                thread_c = ThreadC(audio_manager, user_input)
                c_thread = threading.Thread(target=thread_c.run, daemon=True)
                c_thread.start()
                
                # 🔧 重要：更新当前C线程引用
                current_c_thread = c_thread
                
                print(f"✅ C线程已启动: {c_thread.ident}")
                
            except queue.Empty:
                # 定期检查队列状态
                continue
            except KeyboardInterrupt:
                print("\n🛑 收到退出信号")
                break
                
    except Exception as e:
        print(f"❌ 主循环异常: {e}")
    finally:
        # 清理资源
        print("🧹 清理资源...")
        thread_a_running = False
        thread_b_running = False
        
        if GIF_AVAILABLE:
            try:
                pass
            except:
                pass
        
        try:
            stop_continuous_detection()
        except:
            pass
        
        print("✅ 语音助手已安全关闭")

if __name__ == "__main__":
    main() 