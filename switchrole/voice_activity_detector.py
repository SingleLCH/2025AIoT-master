#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音活动检测模块 (Voice Activity Detection - VAD)

功能：
- 检测用户是否在真实说话
- 区分有效语音和环境噪音
- 支持超时检测
- 与Azure语音识别集成
"""

import os
import time
import threading
from typing import Optional, Tuple
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# 加载环境变量
load_dotenv("xiaoxin.env")

class VoiceActivityResult:
    """语音活动检测结果"""
    
    def __init__(self, has_speech: bool, text: str = "", confidence: float = 0.0, reason: str = ""):
        self.has_speech = has_speech      # 是否检测到有效语音
        self.text = text                  # 识别的文本
        self.confidence = confidence      # 置信度
        self.reason = reason              # 结果原因
        self.timestamp = time.time()      # 时间戳

class VoiceActivityDetector:
    """语音活动检测器"""
    
    def __init__(self):
        # Azure语音服务配置
        self.speech_key = os.environ["Azure_speech_key"]
        self.service_region = os.environ["Azure_speech_region"]
        
        # 检测参数
        self.silence_timeout = 3.0  # 静音超时时间(秒)
        self.min_speech_duration = 0.5  # 最小语音时长(秒)
        
        print("🎙️ 语音活动检测器初始化完成")
    
    def detect_voice_activity(self, timeout: float = 5.0) -> VoiceActivityResult:
        """
        检测语音活动（强力音频设备独占锁）
        
        Args:
            timeout: 最大等待时间(秒)
            
        Returns:
            VoiceActivityResult: 检测结果
        """
        # 导入强力音频设备锁
        from audio_device_lock import get_audio_device_lock
        audio_lock = get_audio_device_lock()
        
        # 导入音频会话管理器
        from audio_session_manager import get_audio_session_manager
        session_manager = get_audio_session_manager()
        
        requester = f"语音检测_{threading.current_thread().ident}"
        
        print(f"🔍 开始语音活动检测 (超时: {timeout}秒)")
        
        # 获取音频设备录音锁（等待播放完成）
        if not audio_lock.acquire_for_recording(requester, timeout=timeout+5):
            print("❌ 无法获取音频设备录音锁")
            return VoiceActivityResult(
                has_speech=False,
                reason="音频设备被播放占用，无法开始录音"
            )
        
        # 检查是否允许录音
        if not session_manager.is_recording_allowed():
            print("⚠️ 会话管理器不允许录音，等待...")
            # 等待播放完成
            if not session_manager.wait_for_playback_completion(timeout=5.0):
                print("❌ 等待会话管理器允许录音超时")
                audio_lock.release(requester)
                return VoiceActivityResult(
                    has_speech=False,
                    reason="等待会话管理器允许录音超时"
                )
        
        # 开始录音会话
        if not session_manager.start_recording():
            print("❌ 无法开始录音会话")
            audio_lock.release(requester)
            return VoiceActivityResult(
                has_speech=False,
                reason="会话管理器拒绝录音"
            )
        
        try:
            # 创建语音配置
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region
            )
            speech_config.speech_recognition_language = "zh-CN"
            
            # 设置识别超时
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
                str(int(timeout * 1000))
            )
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
                str(int(self.silence_timeout * 1000))
            )
            
            # 创建音频配置和识别器
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # 执行识别
            print("👂 正在监听语音输入...")
            start_time = time.time()
            result = speech_recognizer.recognize_once()
            duration = time.time() - start_time
            
            # 分析结果
            return self._analyze_recognition_result(result, duration, timeout)
            
        except Exception as e:
            print(f"❌ 语音活动检测异常: {e}")
            return VoiceActivityResult(
                has_speech=False,
                reason=f"检测异常: {e}"
            )
        finally:
            # 结束录音会话和释放设备锁
            session_manager.finish_recording()
            audio_lock.release(requester)
    
    def _analyze_recognition_result(self, result, duration: float, timeout: float) -> VoiceActivityResult:
        """分析语音识别结果"""
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # 识别到语音
            text = result.text.strip()
            if len(text) > 0:
                print(f"✅ 检测到有效语音: '{text}' (时长: {duration:.1f}s)")
                return VoiceActivityResult(
                    has_speech=True,
                    text=text,
                    confidence=1.0,
                    reason="成功识别语音"
                )
            else:
                print(f"⚠️ 识别到空文本 (时长: {duration:.1f}s)")
                return VoiceActivityResult(
                    has_speech=False,
                    reason="识别到空文本"
                )
                
        elif result.reason == speechsdk.ResultReason.NoMatch:
            # 没有匹配的语音
            print(f"🔇 未检测到清晰语音 (时长: {duration:.1f}s)")
            return VoiceActivityResult(
                has_speech=False,
                reason="未检测到清晰语音"
            )
            
        elif result.reason == speechsdk.ResultReason.Canceled:
            # 识别被取消
            cancellation = result.cancellation_details
            if cancellation.reason == speechsdk.CancellationReason.EndOfStream:
                print(f"⏰ 语音检测超时 (时长: {duration:.1f}s)")
                return VoiceActivityResult(
                    has_speech=False,
                    reason="检测超时"
                )
            elif cancellation.reason == speechsdk.CancellationReason.Error:
                print(f"❌ 语音识别错误: {cancellation.error_details}")
                return VoiceActivityResult(
                    has_speech=False,
                    reason=f"识别错误: {cancellation.error_details}"
                )
            else:
                print(f"🛑 语音识别被取消: {cancellation.reason}")
                return VoiceActivityResult(
                    has_speech=False,
                    reason=f"识别取消: {cancellation.reason}"
                )
        else:
            print(f"❓ 未知识别结果: {result.reason}")
            return VoiceActivityResult(
                has_speech=False,
                reason=f"未知结果: {result.reason}"
            )
    
    def quick_voice_check(self, timeout: float = 2.0) -> bool:
        """
        快速语音检测（只返回是否有语音）
        
        Args:
            timeout: 检测超时时间
            
        Returns:
            bool: 是否检测到有效语音
        """
        result = self.detect_voice_activity(timeout)
        return result.has_speech
    
    def wait_for_silence(self, max_wait: float = 5.0) -> bool:
        """
        等待环境安静（无语音输入）
        
        Args:
            max_wait: 最大等待时间
            
        Returns:
            bool: 是否达到安静状态
        """
        print(f"🤫 等待环境安静 (最多等待 {max_wait}秒)")
        
        start_time = time.time()
        check_interval = 0.5
        
        while time.time() - start_time < max_wait:
            # 短时间检测是否有语音
            has_voice = self.quick_voice_check(check_interval)
            if not has_voice:
                print("✅ 环境已安静")
                return True
            
            print("⏳ 仍有语音活动，继续等待...")
            time.sleep(0.1)
        
        print("⏰ 等待安静超时")
        return False

# 全局检测器实例
_global_vad = None

def get_voice_activity_detector() -> VoiceActivityDetector:
    """获取全局语音活动检测器实例"""
    global _global_vad
    if _global_vad is None:
        _global_vad = VoiceActivityDetector()
    return _global_vad

def detect_voice_activity(timeout: float = 5.0) -> VoiceActivityResult:
    """便捷函数：检测语音活动"""
    detector = get_voice_activity_detector()
    return detector.detect_voice_activity(timeout)

def quick_voice_check(timeout: float = 2.0) -> bool:
    """便捷函数：快速语音检测"""
    detector = get_voice_activity_detector()
    return detector.quick_voice_check(timeout)

def wait_for_silence(max_wait: float = 5.0) -> bool:
    """便捷函数：等待环境安静"""
    detector = get_voice_activity_detector()
    return detector.wait_for_silence(max_wait)

# 测试函数
def test_voice_activity_detection():
    """测试语音活动检测功能"""
    print("🧪 开始测试语音活动检测")
    print("=" * 50)
    
    detector = get_voice_activity_detector()
    
    # 测试1：正常语音检测
    print("\n📍 测试1：正常语音检测（5秒超时）")
    print("请说话...")
    result = detector.detect_voice_activity(5.0)
    print(f"结果: 有语音={result.has_speech}, 文本='{result.text}', 原因={result.reason}")
    
    # 测试2：快速检测
    print("\n📍 测试2：快速语音检测（2秒超时）")
    print("请说话或保持安静...")
    has_voice = detector.quick_voice_check(2.0)
    print(f"结果: 有语音={has_voice}")
    
    # 测试3：等待安静
    print("\n📍 测试3：等待环境安静")
    print("请保持安静...")
    is_quiet = detector.wait_for_silence(3.0)
    print(f"结果: 环境安静={is_quiet}")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_voice_activity_detection() 