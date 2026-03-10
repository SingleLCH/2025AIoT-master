#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
持续唤醒词检测模块

功能：
- 在后台持续监听"你好广和通"唤醒词
- 不受对话状态影响，始终保持监听
- 检测到唤醒词时立即执行唤醒流程
- 支持多线程安全操作
"""

import os
import threading
import time
import queue
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# 加载环境变量
load_dotenv("xiaoxin.env")

class ContinuousWakewordDetector:
    """持续唤醒词检测器"""
    
    def __init__(self):
        # Azure语音服务配置
        self.speech_key = os.environ["Azure_speech_key"]
        self.service_region = os.environ["Azure_speech_region"]
        
        # 唤醒词配置
        self.keyword = os.environ["WakeupWord"]
        model_file_name = os.environ["WakeupModelFile"]
        
        # 🔧 确保使用绝对路径
        if not os.path.isabs(model_file_name):
            # 相对路径，转换为绝对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.model_file = os.path.join(script_dir, model_file_name)
        else:
            self.model_file = model_file_name
        
        # 线程控制
        self._detector_thread = None
        self._running = False
        self._wake_queue = queue.Queue()
        
        # 回调函数
        self._wake_callback = None
        
        print(f"🎤 初始化持续唤醒词检测器")
        print(f"   唤醒词: {self.keyword}")
        print(f"   模型文件: {self.model_file}")
    
    def set_wake_callback(self, callback):
        """
        设置唤醒回调函数
        
        Args:
            callback: 检测到唤醒词时调用的函数
        """
        self._wake_callback = callback
        print(f"✅ 已设置唤醒回调函数")
    
    def start(self):
        """启动持续唤醒词检测"""
        if self._running:
            print("⚠️ 唤醒词检测已在运行中")
            return
        
        print("🚀 启动持续唤醒词检测...")
        
        # 请求最高优先级音频权限（唤醒词监听）
        from audio_priority_manager import AudioPriority, request_audio_access
        if request_audio_access(AudioPriority.WAKE_WORD, "持续唤醒词检测"):
            print("🎤 获得唤醒词监听权限")
        else:
            print("⚠️ 无法获得唤醒词监听权限，但将继续尝试启动")
        
        self._running = True
        
        # 启动检测线程
        self._detector_thread = threading.Thread(
            target=self._detector_loop,
            name="ContinuousWakewordDetector",
            daemon=True
        )
        self._detector_thread.start()
        
        # 启动处理线程
        self._handler_thread = threading.Thread(
            target=self._handler_loop,
            name="WakewordHandler",
            daemon=True
        )
        self._handler_thread.start()
        
        print("✅ 持续唤醒词检测已启动")
    
    def stop(self):
        """停止持续唤醒词检测"""
        if not self._running:
            print("⚠️ 唤醒词检测未在运行")
            return
        
        print("🛑 停止持续唤醒词检测...")
        self._running = False
        
        # 释放音频权限
        from audio_priority_manager import AudioPriority, release_audio_access
        release_audio_access(AudioPriority.WAKE_WORD, "持续唤醒词检测")
        
        # 等待线程结束
        if self._detector_thread and self._detector_thread.is_alive():
            self._detector_thread.join(timeout=2)
        
        print("✅ 持续唤醒词检测已停止")
    
    def _detector_loop(self):
        """检测器主循环（独立音频通道，避免被TTS播放阻塞）"""
        print("🔍 唤醒词检测线程已启动")
        
        # 检测器重启计数
        restart_count = 0
        max_restarts = 5
        
        while self._running:
            try:
                # 导入音频会话管理器
                from audio_session_manager import get_audio_session_manager
                session_manager = get_audio_session_manager()
                
                # 设置回调，确保唤醒检测可以中断音频播放
                session_manager.set_callbacks(
                    pause_recording_callback=None,  # 唤醒检测不需要暂停
                    resume_recording_callback=None,
                    stop_playback_callback=self._stop_current_playback
                )
                
                # 创建语音配置
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.speech_key,
                    region=self.service_region
                )
                speech_config.speech_recognition_language = "zh-CN"
                
                # 设置更短的超时，确保检测器不会被阻塞太久
                speech_config.set_property(
                    speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
                    "3000"  # 3秒超时
                )
                
                # 创建音频配置 - 使用独立的音频通道
                # 注意：这里使用默认麦克风，但我们会通过音频优先级管理来协调
                audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
                
                # 创建唤醒词识别器
                keyword_recognizer = speechsdk.KeywordRecognizer(audio_config=audio_config)
                
                # 加载唤醒词模型
                model = speechsdk.KeywordRecognitionModel(self.model_file)
                
                # 设置回调处理唤醒事件
                def on_keyword_recognized(evt):
                    """唤醒词识别回调"""
                    print(f"🎯 检测到唤醒词: {evt.result.text} (置信度: {evt.result.reason})")
                    # 将唤醒事件放入队列
                    self._wake_queue.put({
                        'timestamp': time.time(),
                        'text': evt.result.text,
                        'confidence': getattr(evt.result, 'confidence', 1.0)
                    })
                    # 重置重启计数
                    restart_count = 0
                
                def on_recognition_canceled(evt):
                    """识别取消回调"""
                    print(f"⚠️ 唤醒词检测取消: {evt.reason}")
                    if evt.reason == speechsdk.CancellationReason.Error:
                        print(f"❌ 唤醒词检测错误: {evt.error_details}")
                
                # 连接回调
                keyword_recognizer.recognized.connect(on_keyword_recognized)
                keyword_recognizer.canceled.connect(on_recognition_canceled)
                
                print(f"👂 开始持续监听唤醒词: '{self.keyword}' (重启次数: {restart_count})")
                
                # 🚀 关键修复：持续循环调用recognize_once_async实现真正的持续检测
                
                # 状态检查变量
                check_interval = 5.0  # 每5秒输出一次状态
                last_check = time.time()
                consecutive_errors = 0
                max_consecutive_errors = 3
                
                print(f"👂 开始持续监听唤醒词: '{self.keyword}' (重启次数: {restart_count})")
                
                while self._running:
                    try:
                        current_time = time.time()
                        
                        # 定期输出状态确认检测器在运行
                        if current_time - last_check > check_interval:
                            print(f"🔍 唤醒词检测器运行中... (队列大小: {self._wake_queue.qsize()})")
                            last_check = current_time
                        
                        # 执行一次唤醒词检测（静默模式）
                        result_future = keyword_recognizer.recognize_once_async(model)
                        
                        # 设置较短的超时避免长时间阻塞
                        try:
                            result = result_future.get()
                            consecutive_errors = 0  # 重置连续错误计数
                            
                            # 仅在非NoMatch时输出调试信息
                            if result.reason != speechsdk.ResultReason.NoMatch:
                                print(f"🔍 检测结果: reason={result.reason}, text='{result.text}'")
                            
                            # 检查结果
                            if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                                print(f"🎯 检测到唤醒词: {result.text} (置信度: {result.reason})")
                                # 将唤醒事件放入队列
                                self._wake_queue.put({
                                    'timestamp': time.time(),
                                    'text': result.text,
                                    'confidence': getattr(result, 'confidence', 1.0)
                                })
                                # 重置重启计数
                                restart_count = 0
                                # 短暂等待后继续检测
                                time.sleep(0.5)
                            elif result.reason == speechsdk.ResultReason.Canceled:
                                cancellation = result.cancellation_details
                                if cancellation.reason == speechsdk.CancellationReason.Error:
                                    print(f"❌ 唤醒词检测错误: {cancellation.error_details}")
                                    consecutive_errors += 1
                                    if consecutive_errors >= max_consecutive_errors:
                                        print(f"❌ 连续错误次数过多，重启检测器")
                                        break
                                    time.sleep(1)  # 错误时等待1秒
                                else:
                                    # 其他取消原因（如超时），快速重试
                                    print(f"ℹ️ 检测取消: {cancellation.reason}")
                                    time.sleep(0.1)
                            elif result.reason == speechsdk.ResultReason.NoMatch:
                                print(f"🔇 未匹配到关键词，继续监听...")
                                time.sleep(0.1)
                            else:
                                # 其他情况
                                print(f"❓ 未知检测结果: {result.reason}")
                                time.sleep(0.1)
                                
                        except Exception as timeout_error:
                            print(f"⏰ 唤醒词检测超时或异常: {timeout_error}")
                            consecutive_errors += 1
                            if consecutive_errors >= max_consecutive_errors:
                                print(f"❌ 连续超时次数过多，重启检测器")
                                break
                            time.sleep(1)
                            
                    except Exception as inner_e:
                        print(f"❌ 检测循环内部异常: {inner_e}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print(f"❌ 连续内部异常次数过多，重启检测器")
                            break
                        time.sleep(1)
                
                print(f"🔄 检测循环结束，准备重启... (重启次数: {restart_count})")
                # 短暂等待后重启检测器
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ 唤醒词检测异常: {e}")
                restart_count += 1
                if restart_count >= max_restarts:
                    print(f"❌ 唤醒词检测异常次数过多，停止检测")
                    break
                if self._running:
                    time.sleep(2)  # 异常时等待较长时间后重试
        
        print("🔍 唤醒词检测线程已停止")
    
    def _stop_current_playback(self):
        """优雅停止当前音频播放的回调函数（安全版）"""
        try:
            print("🔄 唤醒词检测：执行优雅音频中断")
            
            # 设置全局中断标志
            try:
                import xiaoxin2_zh
                xiaoxin2_zh.tts_interrupt_flag = True
                print("🚩 设置全局TTS中断标志")
            except:
                pass
            
            # 优雅中断流式TTS播放
            try:
                from streaming_tts_player import get_streaming_player
                player = get_streaming_player()
                if player and player.is_playing:
                    print("🛑 优雅中断流式TTS播放")
                    player.interrupt()
            except:
                pass
            
            # 优雅停止ALSA TTS
            try:
                from alsa_cosyvoice_tts import get_alsa_tts
                alsa_tts = get_alsa_tts()
                if alsa_tts:
                    alsa_tts.finish_streaming_playback()  # 使用优雅停止而不是强制中断
                    print("✅ ALSA TTS已优雅停止")
            except:
                pass
            
            # 使用音频优先级管理器
            try:
                from audio_priority_manager import AudioPriority, request_audio_access
                if request_audio_access(AudioPriority.WAKE_WORD, "唤醒词检测"):
                    print("✅ 获得唤醒词监听权限")
            except:
                pass
            
            # 停止pygame音频（如果是Windows）
            import platform
            if platform.system().lower() == "windows":
                try:
                    import pygame
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.stop()
                        print("✅ pygame音频已停止")
                except:
                    pass
            
            # 给音频进程时间优雅结束
            time.sleep(0.3)
            
            print("✅ 优雅音频中断完成，唤醒词可以正常检测")
            
        except Exception as e:
            print(f"❌ 优雅停止音频播放时出错: {e}")
    
    def _handler_loop(self):
        """唤醒事件处理循环"""
        print("🔧 唤醒事件处理线程已启动")
        
        while self._running:
            try:
                # 等待唤醒事件
                wake_event = self._wake_queue.get(timeout=1)
                
                print(f"🎉 处理唤醒事件: {wake_event['text']}")
                
                # 调用回调函数
                if self._wake_callback:
                    try:
                        self._wake_callback(wake_event)
                    except Exception as callback_error:
                        print(f"❌ 唤醒回调函数执行错误: {callback_error}")
                else:
                    print("⚠️ 未设置唤醒回调函数")
                
            except queue.Empty:
                continue  # 超时继续等待
            except Exception as e:
                print(f"❌ 唤醒事件处理异常: {e}")
                if self._running:
                    time.sleep(0.5)
        
        print("🔧 唤醒事件处理线程已停止")
    
    def _on_keyword_recognized(self, evt):
        """唤醒词识别回调"""
        # 这个方法在检测器线程中被调用
        # 实际处理在 _detector_loop 中完成
        pass
    
    def _on_recognition_canceled(self, evt):
        """识别取消回调"""
        # 这个方法在检测器线程中被调用
        # 实际处理在 _detector_loop 中完成
        pass
    
    def is_running(self):
        """检查是否正在运行"""
        return self._running
    
    def get_status(self):
        """获取状态信息"""
        return {
            'running': self._running,
            'detector_thread_alive': self._detector_thread.is_alive() if self._detector_thread else False,
            'handler_thread_alive': self._handler_thread.is_alive() if hasattr(self, '_handler_thread') and self._handler_thread else False,
            'queue_size': self._wake_queue.qsize()
        }

# 全局检测器实例
_global_detector = None

def get_continuous_detector():
    """获取全局持续唤醒词检测器实例"""
    global _global_detector
    if _global_detector is None:
        _global_detector = ContinuousWakewordDetector()
    return _global_detector

def start_continuous_detection(wake_callback=None):
    """启动持续唤醒词检测"""
    detector = get_continuous_detector()
    if wake_callback:
        detector.set_wake_callback(wake_callback)
    detector.start()
    return detector

def stop_continuous_detection():
    """停止持续唤醒词检测"""
    detector = get_continuous_detector()
    detector.stop()

# 测试函数
def test_continuous_detector():
    """测试持续唤醒词检测"""
    def test_callback(wake_event):
        print(f"🎯 测试回调：检测到唤醒词 '{wake_event['text']}' at {wake_event['timestamp']}")
    
    print("🧪 开始测试持续唤醒词检测")
    detector = start_continuous_detection(test_callback)
    
    try:
        print("⏳ 测试运行30秒，请说'你好广和通'...")
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n⌨️ 用户中断测试")
    finally:
        stop_continuous_detection()
        print("✅ 测试完成")

if __name__ == "__main__":
    test_continuous_detector() 