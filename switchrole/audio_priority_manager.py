#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频优先级管理系统

优先级层次：
1. 最高优先级：唤醒词监听 - 随时可以打断其他音频
2. 中等优先级：TTS语音播放 - 可以被唤醒词打断，但优先于音乐  
3. 最低优先级：音乐播放 - 可以被唤醒词和TTS打断
"""

import threading
import time
import logging
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class AudioPriority(Enum):
    """音频优先级枚举"""
    WAKE_WORD = 1      # 最高优先级：唤醒词监听
    TTS = 2           # 中等优先级：TTS语音播放
    MUSIC = 3         # 最低优先级：音乐播放

class AudioPriorityManager:
    """
    音频优先级管理器
    
    管理不同优先级的音频播放，确保高优先级音频可以打断低优先级音频
    """
    
    def __init__(self):
        self._current_priority = None
        self._lock = threading.RLock()
        self._wake_word_active = False
        self._tts_active = False
        self._music_active = False
        
        # 回调函数
        self._stop_music_callback = None
        self._stop_tts_callback = None
        
    def set_callbacks(self, stop_music_callback: Callable, stop_tts_callback: Callable):
        """设置停止音频的回调函数"""
        self._stop_music_callback = stop_music_callback
        self._stop_tts_callback = stop_tts_callback
    
    def request_audio_access(self, priority: AudioPriority, requester_id: str = "") -> bool:
        """
        请求音频播放权限
        
        Args:
            priority: 请求的优先级
            requester_id: 请求者标识
            
        Returns:
            bool: 是否获得播放权限
        """
        with self._lock:
            logger.info(f"🎵 [{requester_id}] 请求音频权限, 优先级: {priority.name}")
            
            # 如果没有当前音频或请求优先级更高，则允许播放
            if self._current_priority is None or priority.value <= self._current_priority.value:
                
                # 如果有更低优先级的音频在播放，停止它们
                if self._current_priority and priority.value < self._current_priority.value:
                    self._stop_lower_priority_audio(priority)
                
                # 更新当前优先级
                self._current_priority = priority
                self._update_audio_status(priority, True)
                
                logger.info(f"✅ [{requester_id}] 获得音频权限")
                return True
            else:
                logger.info(f"❌ [{requester_id}] 音频权限被拒绝，当前优先级更高: {self._current_priority.name}")
                return False
    
    def release_audio_access(self, priority: AudioPriority, requester_id: str = ""):
        """
        释放音频播放权限
        
        Args:
            priority: 释放的优先级
            requester_id: 请求者标识
        """
        with self._lock:
            logger.info(f"🔊 [{requester_id}] 释放音频权限, 优先级: {priority.name}")
            
            if self._current_priority == priority:
                self._current_priority = None
                self._update_audio_status(priority, False)
                
                # 检查是否有其他音频等待播放
                self._check_pending_audio()
                
                logger.info(f"✅ [{requester_id}] 音频权限已释放")
            else:
                logger.warning(f"⚠️ [{requester_id}] 尝试释放不匹配的音频权限")
    
    def is_wake_word_listening(self) -> bool:
        """检查唤醒词监听是否活跃"""
        return self._wake_word_active
    
    def is_tts_playing(self) -> bool:
        """检查TTS是否正在播放"""
        return self._tts_active
    
    def is_music_playing(self) -> bool:
        """检查音乐是否正在播放"""
        return self._music_active
    
    def get_current_priority(self) -> Optional[AudioPriority]:
        """获取当前音频优先级"""
        return self._current_priority
    
    def force_stop_all(self, except_priority: Optional[AudioPriority] = None):
        """
        强制停止所有音频（除了指定优先级）
        
        Args:
            except_priority: 不停止的优先级
        """
        with self._lock:
            logger.info(f"🛑 强制停止所有音频，除了: {except_priority.name if except_priority else 'None'}")
            
            if except_priority != AudioPriority.MUSIC and self._music_active:
                self._stop_music()
            
            if except_priority != AudioPriority.TTS and self._tts_active:
                self._stop_tts()
            
            # 更新当前优先级
            if except_priority:
                self._current_priority = except_priority
            else:
                self._current_priority = None
    
    def _stop_lower_priority_audio(self, current_priority: AudioPriority):
        """停止比当前优先级低的音频"""
        if current_priority == AudioPriority.WAKE_WORD:
            # 唤醒词可以打断所有音频
            self._stop_tts()
            self._stop_music()
        elif current_priority == AudioPriority.TTS:
            # TTS可以打断音乐，但不能影响唤醒词监听
            self._stop_music()
            # 注意：TTS播放时唤醒词监听继续运行
        # 音乐不能打断任何音频
    
    def _stop_music(self):
        """停止音乐播放"""
        if self._music_active and self._stop_music_callback:
            logger.info("🎵 停止音乐播放")
            try:
                self._stop_music_callback()
                self._music_active = False
            except Exception as e:
                logger.error(f"停止音乐失败: {e}")
    
    def _stop_tts(self):
        """停止TTS播放"""
        if self._tts_active and self._stop_tts_callback:
            logger.info("🎤 停止TTS播放")
            try:
                self._stop_tts_callback()
                self._tts_active = False
            except Exception as e:
                logger.error(f"停止TTS失败: {e}")
    
    def _update_audio_status(self, priority: AudioPriority, active: bool):
        """更新音频状态"""
        if priority == AudioPriority.WAKE_WORD:
            self._wake_word_active = active
        elif priority == AudioPriority.TTS:
            self._tts_active = active
        elif priority == AudioPriority.MUSIC:
            self._music_active = active
    
    def _check_pending_audio(self):
        """检查是否有等待播放的音频"""
        # 这里可以实现音频队列逻辑
        # 目前简化为直接释放
        pass
    
    def get_status_info(self) -> dict:
        """获取当前状态信息"""
        return {
            "current_priority": self._current_priority.name if self._current_priority else None,
            "wake_word_active": self._wake_word_active,
            "tts_active": self._tts_active,
            "music_active": self._music_active
        }

# 全局音频优先级管理器实例
_global_audio_manager = None

def get_audio_manager() -> AudioPriorityManager:
    """获取全局音频优先级管理器实例"""
    global _global_audio_manager
    if _global_audio_manager is None:
        _global_audio_manager = AudioPriorityManager()
    return _global_audio_manager

# 便捷函数
def request_audio_access(priority: AudioPriority, requester_id: str = "") -> bool:
    """请求音频播放权限"""
    return get_audio_manager().request_audio_access(priority, requester_id)

def release_audio_access(priority: AudioPriority, requester_id: str = ""):
    """释放音频播放权限"""
    get_audio_manager().release_audio_access(priority, requester_id)

def is_audio_available_for(priority: AudioPriority) -> bool:
    """检查指定优先级是否可以获得音频权限"""
    manager = get_audio_manager()
    current = manager.get_current_priority()
    return current is None or priority.value <= current.value

def force_stop_all_audio(except_priority: Optional[AudioPriority] = None):
    """强制停止所有音频"""
    get_audio_manager().force_stop_all(except_priority)

def get_audio_status() -> dict:
    """获取音频状态信息"""
    return get_audio_manager().get_status_info()

if __name__ == "__main__":
    # 测试音频优先级管理器
    print("🎧 音频优先级管理器测试")
    print("=" * 50)
    
    manager = get_audio_manager()
    
    # 模拟音乐播放
    print("1. 开始播放音乐...")
    success = manager.request_audio_access(AudioPriority.MUSIC, "音乐播放器")
    print(f"   音乐播放权限: {'✅ 获得' if success else '❌ 拒绝'}")
    print(f"   当前状态: {manager.get_status_info()}")
    
    # 模拟TTS播放（应该打断音乐）
    print("\n2. AI要说话...")
    success = manager.request_audio_access(AudioPriority.TTS, "TTS引擎")
    print(f"   TTS播放权限: {'✅ 获得' if success else '❌ 拒绝'}")
    print(f"   当前状态: {manager.get_status_info()}")
    
    # 模拟唤醒词检测（应该打断TTS）
    print("\n3. 检测到唤醒词...")
    success = manager.request_audio_access(AudioPriority.WAKE_WORD, "唤醒词检测")
    print(f"   唤醒词权限: {'✅ 获得' if success else '❌ 拒绝'}")
    print(f"   当前状态: {manager.get_status_info()}")
    
    # 释放唤醒词权限
    print("\n4. 唤醒词处理完成...")
    manager.release_audio_access(AudioPriority.WAKE_WORD, "唤醒词检测")
    print(f"   当前状态: {manager.get_status_info()}")
    
    print("\n✅ 测试完成") 