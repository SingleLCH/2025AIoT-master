#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
对话线程管理器

功能：
- 管理对话线程的生命周期
- 支持线程挂起、恢复、终止
- 处理唤醒词中断逻辑
- 语音活动检测
"""

import threading
import time
import queue
import logging
from enum import Enum
from typing import Optional, Callable

class ConversationState(Enum):
    """对话状态枚举"""
    IDLE = "idle"                    # 空闲状态
    LISTENING = "listening"          # 监听用户输入
    PROCESSING = "processing"        # 处理用户输入
    SPEAKING = "speaking"           # AI回复中
    SUSPENDED = "suspended"         # 挂起状态
    TERMINATED = "terminated"       # 终止状态

class ConversationThread:
    """对话线程类"""
    
    def __init__(self, thread_id: str, conversation_func: Callable, callback_on_complete: Callable = None):
        self.thread_id = thread_id
        self._conversation_func = conversation_func  # 修复：确保属性名正确
        self.callback_on_complete = callback_on_complete
        
        # 线程控制
        self._thread = None
        self._state = ConversationState.IDLE
        self._suspend_event = threading.Event()
        self._terminate_event = threading.Event()
        self._state_lock = threading.RLock()
        
        # 设置初始状态为运行
        self._suspend_event.set()
        
        print(f"🆕 创建对话线程: {thread_id}")
    
    def start(self):
        """启动对话线程"""
        if self._thread and self._thread.is_alive():
            print(f"⚠️ 对话线程 {self.thread_id} 已在运行")
            return False
        
        self._state = ConversationState.IDLE
        self._thread = threading.Thread(
            target=self._conversation_loop,
            name=f"ConversationThread-{self.thread_id}",
            daemon=True
        )
        self._thread.start()
        print(f"🚀 启动对话线程: {self.thread_id}")
        return True
    
    def suspend(self):
        """挂起对话线程"""
        with self._state_lock:
            if self._state not in [ConversationState.TERMINATED]:
                print(f"⏸️ 挂起对话线程: {self.thread_id}")
                self._suspend_event.clear()
                self._state = ConversationState.SUSPENDED
                return True
        return False
    
    def resume(self):
        """恢复对话线程"""
        with self._state_lock:
            if self._state == ConversationState.SUSPENDED:
                print(f"▶️ 恢复对话线程: {self.thread_id}")
                self._suspend_event.set()
                self._state = ConversationState.IDLE
                return True
        return False
    
    def terminate(self):
        """终止对话线程"""
        with self._state_lock:
            print(f"🛑 终止对话线程: {self.thread_id}")
            self._terminate_event.set()
            self._suspend_event.set()  # 确保线程能够检查终止标志
            self._state = ConversationState.TERMINATED
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
    
    def get_state(self):
        """获取当前状态"""
        with self._state_lock:
            return self._state
    
    def set_state(self, state: ConversationState):
        """设置状态"""
        with self._state_lock:
            self._state = state
    
    def is_alive(self):
        """检查线程是否存活"""
        return self._thread and self._thread.is_alive()
    
    def _conversation_loop(self):
        """对话线程主循环"""
        print(f"🔄 对话线程循环开始: {self.thread_id}")
        
        try:
            while not self._terminate_event.is_set():
                # 等待恢复信号（如果被挂起）
                self._suspend_event.wait()
                
                # 检查是否需要终止
                if self._terminate_event.is_set():
                    break
                
                # 执行对话逻辑
                try:
                    result = self._conversation_func(self)
                    if result == "terminate":
                        break
                except Exception as e:
                    print(f"❌ 对话函数执行异常: {e}")
                    time.sleep(1)
                
                # 短暂等待，避免CPU占用过高
                time.sleep(0.1)
                
        except Exception as e:
            print(f"❌ 对话线程异常: {e}")
        finally:
            self._state = ConversationState.TERMINATED
            if self.callback_on_complete:
                try:
                    self.callback_on_complete(self.thread_id)
                except Exception as e:
                    print(f"❌ 完成回调异常: {e}")
            print(f"✅ 对话线程结束: {self.thread_id}")

class ConversationThreadManager:
    """对话线程管理器"""
    
    def __init__(self):
        self._conversations = {}  # thread_id -> ConversationThread
        self._active_thread_id = None
        self._lock = threading.RLock()
        
        print("🎛️ 对话线程管理器初始化完成")
    
    def create_conversation(self, conversation_func: Callable, thread_id: str = None) -> str:
        """
        创建新的对话线程
        
        Args:
            conversation_func: 对话函数
            thread_id: 线程ID，如果为None则自动生成
            
        Returns:
            str: 线程ID
        """
        with self._lock:
            if thread_id is None:
                thread_id = f"conv_{int(time.time() * 1000)}"
            
            # 终止现有的活跃线程
            if self._active_thread_id and self._active_thread_id in self._conversations:
                old_thread = self._conversations[self._active_thread_id]
                print(f"🔄 终止旧对话线程: {self._active_thread_id}")
                old_thread.terminate()
                del self._conversations[self._active_thread_id]
            
            # 创建新线程
            conversation = ConversationThread(
                thread_id, 
                conversation_func, 
                self._on_conversation_complete
            )
            
            self._conversations[thread_id] = conversation
            self._active_thread_id = thread_id
            
            return thread_id
    
    def start_conversation(self, thread_id: str) -> bool:
        """启动指定的对话线程"""
        with self._lock:
            if thread_id in self._conversations:
                return self._conversations[thread_id].start()
        return False
    
    def suspend_active_conversation(self) -> bool:
        """挂起当前活跃的对话线程"""
        with self._lock:
            if self._active_thread_id and self._active_thread_id in self._conversations:
                return self._conversations[self._active_thread_id].suspend()
        return False
    
    def resume_active_conversation(self) -> bool:
        """恢复当前活跃的对话线程"""
        with self._lock:
            if self._active_thread_id and self._active_thread_id in self._conversations:
                return self._conversations[self._active_thread_id].resume()
        return False
    
    def terminate_active_conversation(self) -> bool:
        """终止当前活跃的对话线程"""
        with self._lock:
            if self._active_thread_id and self._active_thread_id in self._conversations:
                thread = self._conversations[self._active_thread_id]
                thread.terminate()
                del self._conversations[self._active_thread_id]
                self._active_thread_id = None
                return True
        return False
    
    def get_active_thread_state(self) -> Optional[ConversationState]:
        """获取活跃线程的状态"""
        with self._lock:
            if self._active_thread_id and self._active_thread_id in self._conversations:
                return self._conversations[self._active_thread_id].get_state()
        return None
    
    def set_active_thread_state(self, state: ConversationState) -> bool:
        """设置活跃线程的状态"""
        with self._lock:
            if self._active_thread_id and self._active_thread_id in self._conversations:
                self._conversations[self._active_thread_id].set_state(state)
                return True
        return False
    
    def has_active_conversation(self) -> bool:
        """检查是否有活跃的对话线程"""
        with self._lock:
            return (self._active_thread_id and 
                   self._active_thread_id in self._conversations and
                   self._conversations[self._active_thread_id].is_alive())
    
    def get_status(self) -> dict:
        """获取管理器状态"""
        with self._lock:
            return {
                'active_thread_id': self._active_thread_id,
                'total_conversations': len(self._conversations),
                'active_thread_state': self.get_active_thread_state(),
                'has_active_conversation': self.has_active_conversation()
            }
    
    def _on_conversation_complete(self, thread_id: str):
        """对话完成回调"""
        with self._lock:
            print(f"🏁 对话线程完成: {thread_id}")
            if thread_id in self._conversations:
                del self._conversations[thread_id]
            if self._active_thread_id == thread_id:
                self._active_thread_id = None

# 全局管理器实例
_global_manager = None

def get_conversation_manager() -> ConversationThreadManager:
    """获取全局对话线程管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConversationThreadManager()
    return _global_manager

def create_and_start_conversation(conversation_func: Callable, thread_id: str = None) -> str:
    """创建并启动对话线程的便捷函数"""
    manager = get_conversation_manager()
    thread_id = manager.create_conversation(conversation_func, thread_id)
    manager.start_conversation(thread_id)
    return thread_id 