#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频设备独占锁系统

功能：
- 提供底层音频设备独占访问
- 确保播放期间完全禁止录音
- 支持强制音频设备释放
- 解决音频反馈死循环问题
"""

import threading
import time
import subprocess
import signal
import logging
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class AudioDeviceState(Enum):
    """音频设备状态"""
    FREE = "空闲"
    PLAYING = "播放占用"
    RECORDING = "录音占用"
    LOCKED = "强制锁定"

class AudioDeviceLock:
    """音频设备独占锁"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state = AudioDeviceState.FREE
        self._occupier = None
        self._occupy_time = None
        
        # 强制终止音频进程的列表
        self._audio_processes: List[subprocess.Popen] = []
        self._kill_audio_on_conflict = True
        
        print("🔒 音频设备独占锁已初始化")
    
    def acquire_for_playback(self, requester: str, timeout: float = 5.0) -> bool:
        """
        为播放获取音频设备独占锁
        
        Args:
            requester: 请求者标识
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功获取锁
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if self._state == AudioDeviceState.FREE:
                    self._state = AudioDeviceState.PLAYING
                    self._occupier = requester
                    self._occupy_time = time.time()
                    print(f"🔊 [{requester}] 获得播放设备锁")
                    return True
                elif self._state == AudioDeviceState.RECORDING:
                    print(f"⚠️ 设备被录音占用，强制终止录音进程...")
                    self._force_kill_recording_processes()
                    # 等待一下再重试
                    time.sleep(0.1)
                else:
                    print(f"⏳ [{requester}] 等待设备释放... (当前占用者: {self._occupier})")
                    time.sleep(0.1)
        
        print(f"❌ [{requester}] 获取播放设备锁超时")
        return False
    
    def acquire_for_recording(self, requester: str, timeout: float = 10.0) -> bool:
        """
        为录音获取音频设备独占锁
        
        Args:
            requester: 请求者标识
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否成功获取锁
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if self._state == AudioDeviceState.FREE:
                    self._state = AudioDeviceState.RECORDING
                    self._occupier = requester
                    self._occupy_time = time.time()
                    print(f"🎤 [{requester}] 获得录音设备锁")
                    return True
                elif self._state == AudioDeviceState.PLAYING:
                    # 播放期间不允许录音，等待播放完成
                    occupy_duration = time.time() - self._occupy_time if self._occupy_time else 0
                    print(f"⏳ [{requester}] 等待播放完成... (已播放: {occupy_duration:.1f}s)")
                    time.sleep(0.2)
                else:
                    print(f"⏳ [{requester}] 等待设备释放... (当前占用者: {self._occupier})")
                    time.sleep(0.1)
        
        print(f"❌ [{requester}] 获取录音设备锁超时")
        return False
    
    def release(self, requester: str):
        """
        释放音频设备锁
        
        Args:
            requester: 请求者标识
        """
        with self._lock:
            if self._occupier == requester:
                old_state = self._state
                self._state = AudioDeviceState.FREE
                self._occupier = None
                self._occupy_time = None
                print(f"✅ [{requester}] 释放设备锁 (之前状态: {old_state.value})")
            else:
                print(f"⚠️ [{requester}] 尝试释放非自己占用的设备锁 (当前占用者: {self._occupier})")
    
    def force_release(self, reason: str = "强制释放"):
        """
        强制释放音频设备（安全版本）
        
        Args:
            reason: 强制释放的原因
        """
        with self._lock:
            print(f"🔓 强制释放音频设备: {reason}")
            
            # 优雅停止注册的音频进程
            self._graceful_stop_audio_processes()
            
            # 重置状态
            self._state = AudioDeviceState.FREE
            self._occupier = None
            self._occupy_time = None
            
            print(f"✅ 音频设备已释放: {reason}")
    
    def is_playing(self) -> bool:
        """检查是否正在播放"""
        with self._lock:
            return self._state == AudioDeviceState.PLAYING
    
    def is_recording(self) -> bool:
        """检查是否正在录音"""
        with self._lock:
            return self._state == AudioDeviceState.RECORDING
    
    def is_free(self) -> bool:
        """检查设备是否空闲"""
        with self._lock:
            return self._state == AudioDeviceState.FREE
    
    def get_status(self) -> dict:
        """获取设备状态信息"""
        with self._lock:
            occupy_duration = time.time() - self._occupy_time if self._occupy_time else 0
            return {
                "state": self._state.value,
                "occupier": self._occupier,
                "occupy_duration": occupy_duration,
                "active_processes": len(self._audio_processes)
            }
    
    def register_audio_process(self, process: subprocess.Popen, process_type: str):
        """
        注册音频进程（用于强制终止）
        
        Args:
            process: 音频进程
            process_type: 进程类型（播放/录音）
        """
        with self._lock:
            self._audio_processes.append(process)
            print(f"📝 注册音频进程: {process_type} (PID: {process.pid})")
    
    def unregister_audio_process(self, process: subprocess.Popen):
        """
        注销音频进程
        
        Args:
            process: 音频进程
        """
        with self._lock:
            if process in self._audio_processes:
                self._audio_processes.remove(process)
                print(f"📝 注销音频进程 (PID: {process.pid})")
    
    def _force_kill_recording_processes(self):
        """强制终止录音相关进程"""
        # 终止arecord进程
        try:
            subprocess.run(['pkill', '-f', 'arecord'], timeout=2, capture_output=True)
            print("🔪 已终止arecord进程")
        except:
            pass
        
        # 终止Azure语音SDK相关进程
        try:
            subprocess.run(['pkill', '-f', 'speechsdk'], timeout=2, capture_output=True)
            print("🔪 已终止speechsdk进程")
        except:
            pass
        
        time.sleep(0.2)  # 等待进程完全终止
    
    def _graceful_stop_audio_processes(self):
        """优雅停止注册的音频进程"""
        for process in self._audio_processes[:]:  # 复制列表避免修改时迭代
            try:
                if process.poll() is None:  # 进程仍在运行
                    print(f"🔄 优雅停止音频进程 (PID: {process.pid})")
                    
                    # 首先尝试terminate
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                        print(f"✅ 音频进程已优雅停止 (PID: {process.pid})")
                    except subprocess.TimeoutExpired:
                        print(f"⚠️ 音频进程停止超时 (PID: {process.pid})")
                        # 仅在超时时使用kill
                        try:
                            process.kill()
                            process.wait(timeout=1)
                            print(f"✅ 音频进程已强制停止 (PID: {process.pid})")
                        except:
                            print(f"❌ 无法停止音频进程 (PID: {process.pid})")
                
                self._audio_processes.remove(process)
            except Exception as e:
                print(f"⚠️ 停止音频进程时出错: {e}")
        
        # 仅在Linux系统且没有其他方法时，才使用系统级进程清理
        import platform
        if platform.system().lower() == "linux":
            self._minimal_system_audio_cleanup()
    
    def _minimal_system_audio_cleanup(self):
        """最小化的系统音频进程清理（仅在必要时）"""
        # 仅清理明确的音频播放进程，避免影响系统组件
        try:
            # 仅终止明确的音频播放进程（不用-9）
            subprocess.run(['pkill', '-TERM', 'aplay'], timeout=1, capture_output=True)
            time.sleep(0.2)  # 给进程时间正常退出
            print("🔄 已尝试优雅停止aplay进程")
        except:
            pass

# 全局音频设备锁实例
_global_audio_lock = None

def get_audio_device_lock() -> AudioDeviceLock:
    """获取全局音频设备锁实例"""
    global _global_audio_lock
    if _global_audio_lock is None:
        _global_audio_lock = AudioDeviceLock()
    return _global_audio_lock

def with_audio_playback_lock(func):
    """装饰器：为播放函数添加设备锁"""
    def wrapper(*args, **kwargs):
        audio_lock = get_audio_device_lock()
        requester = f"播放函数_{func.__name__}"
        
        if audio_lock.acquire_for_playback(requester, timeout=10.0):
            try:
                return func(*args, **kwargs)
            finally:
                audio_lock.release(requester)
        else:
            print(f"❌ {requester} 无法获取播放设备锁")
            return False
    
    return wrapper

def with_audio_recording_lock(func):
    """装饰器：为录音函数添加设备锁"""
    def wrapper(*args, **kwargs):
        audio_lock = get_audio_device_lock()
        requester = f"录音函数_{func.__name__}"
        
        if audio_lock.acquire_for_recording(requester, timeout=15.0):
            try:
                return func(*args, **kwargs)
            finally:
                audio_lock.release(requester)
        else:
            print(f"❌ {requester} 无法获取录音设备锁")
            return None
    
    return wrapper 