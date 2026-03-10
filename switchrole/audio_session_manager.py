#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频会话管理器

功能：
- 解决音频播放和录音冲突问题
- 确保播放完成后再开始录音
- 避免AI声音被麦克风录入导致死循环
"""

import threading
import time
import logging
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)

class AudioSessionState(Enum):
    """音频会话状态"""
    IDLE = "空闲"
    PLAYING = "播放中"
    RECORDING = "录音中"
    PAUSED = "暂停"

class AudioSessionManager:
    """音频会话管理器"""
    
    def __init__(self):
        self._state = AudioSessionState.IDLE
        self._lock = threading.RLock()
        self._playback_complete_event = threading.Event()
        self._recording_allowed = True
        
        # 回调函数
        self._pause_recording_callback = None
        self._resume_recording_callback = None
        self._stop_playback_callback = None
        
        print("🎛️ 音频会话管理器已初始化")
    
    def set_callbacks(self, 
                     pause_recording_callback: Optional[Callable] = None,
                     resume_recording_callback: Optional[Callable] = None,
                     stop_playback_callback: Optional[Callable] = None):
        """
        设置回调函数
        
        Args:
            pause_recording_callback: 暂停录音回调
            resume_recording_callback: 恢复录音回调  
            stop_playback_callback: 停止播放回调
        """
        self._pause_recording_callback = pause_recording_callback
        self._resume_recording_callback = resume_recording_callback
        self._stop_playback_callback = stop_playback_callback
        
        print("✅ 音频会话管理器回调函数已设置")
    
    def start_playback(self, audio_type: str = "tts") -> bool:
        """
        开始播放音频
        
        Args:
            audio_type: 音频类型 (tts, system, music)
            
        Returns:
            bool: 是否成功开始播放
        """
        with self._lock:
            if self._state == AudioSessionState.RECORDING:
                print(f"🎤 暂停录音以播放 {audio_type} 音频")
                self._pause_recording()
            
            self._state = AudioSessionState.PLAYING
            self._playback_complete_event.clear()
            self._recording_allowed = False
            
            logger.info(f"🔊 开始播放音频: {audio_type}")
            return True
    
    def finish_playback(self, audio_type: str = "tts"):
        """
        完成播放音频
        
        Args:
            audio_type: 音频类型
        """
        with self._lock:
            if self._state == AudioSessionState.PLAYING:
                self._state = AudioSessionState.IDLE
                self._recording_allowed = True
                self._playback_complete_event.set()
                
                logger.info(f"✅ 音频播放完成: {audio_type}")
                
                # 等待一小段时间确保音频完全释放
                time.sleep(0.3)
                
                # 恢复录音
                print("🎤 恢复录音功能")
                self._resume_recording()
    
    def start_recording(self) -> bool:
        """
        开始录音
        
        Returns:
            bool: 是否允许开始录音
        """
        with self._lock:
            if not self._recording_allowed:
                print("⚠️ 当前正在播放音频，不允许录音")
                return False
            
            if self._state == AudioSessionState.PLAYING:
                print("⚠️ 播放进行中，等待播放完成后再录音")
                return False
            
            self._state = AudioSessionState.RECORDING
            logger.info("🎤 开始录音")
            return True
    
    def finish_recording(self):
        """完成录音"""
        with self._lock:
            if self._state == AudioSessionState.RECORDING:
                self._state = AudioSessionState.IDLE
                logger.info("✅ 录音完成")
    
    def wait_for_playback_completion(self, timeout: float = 10.0) -> bool:
        """
        等待播放完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否在超时前完成
        """
        if self._state != AudioSessionState.PLAYING:
            return True
        
        print(f"⏳ 等待音频播放完成（最长等待 {timeout} 秒）")
        return self._playback_complete_event.wait(timeout)
    
    def force_stop_playback(self):
        """强制停止播放"""
        with self._lock:
            if self._state == AudioSessionState.PLAYING:
                logger.info("🛑 强制停止音频播放")
                
                if self._stop_playback_callback:
                    try:
                        self._stop_playback_callback()
                    except Exception as e:
                        logger.error(f"停止播放回调执行失败: {e}")
                
                self._state = AudioSessionState.IDLE
                self._recording_allowed = True
                self._playback_complete_event.set()
                
                # 恢复录音
                self._resume_recording()
    
    def get_state(self) -> AudioSessionState:
        """获取当前状态"""
        return self._state
    
    def is_recording_allowed(self) -> bool:
        """检查是否允许录音"""
        return self._recording_allowed and self._state != AudioSessionState.PLAYING
    
    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self._state == AudioSessionState.PLAYING
    
    def _pause_recording(self):
        """暂停录音"""
        if self._pause_recording_callback:
            try:
                self._pause_recording_callback()
                print("⏸️ 录音已暂停")
            except Exception as e:
                logger.error(f"暂停录音失败: {e}")
    
    def _resume_recording(self):
        """恢复录音"""
        if self._resume_recording_callback:
            try:
                self._resume_recording_callback()
                print("▶️ 录音已恢复")
            except Exception as e:
                logger.error(f"恢复录音失败: {e}")
    
    def get_status_info(self) -> dict:
        """获取状态信息"""
        return {
            "state": self._state.value,
            "recording_allowed": self._recording_allowed,
            "is_playing": self.is_playing()
        }

# 全局实例
_global_session_manager = None

def get_audio_session_manager() -> AudioSessionManager:
    """获取全局音频会话管理器实例"""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = AudioSessionManager()
    return _global_session_manager 