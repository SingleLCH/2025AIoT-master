#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
线程池管理器

功能：
- 统一管理语音助手的所有线程
- 提供线程状态监控
- 支持线程池复用和负载均衡
- 提供线程异常处理和重启机制
"""

import threading
import time
import queue
import logging
import concurrent.futures
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreadType(Enum):
    """线程类型枚举"""
    WAKE_WORD_DETECTOR = "唤醒词检测"
    SPEECH_RECOGNIZER = "语音识别"
    TTS_PLAYER = "语音合成播放"
    AUDIO_PLAYER = "音频播放"
    CONVERSATION_MANAGER = "对话管理"
    BACKGROUND_LISTENER = "后台监听"
    SYSTEM_MONITOR = "系统监控"
    AUDIO_STREAM = "音频流处理"

@dataclass
class ThreadInfo:
    """线程信息"""
    thread_id: int
    name: str
    thread_type: ThreadType
    start_time: datetime
    status: str
    last_activity: datetime
    error_count: int = 0
    restart_count: int = 0
    
class ThreadPoolManager:
    """线程池管理器"""
    
    def __init__(self, max_workers: int = 10):
        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="VoiceAssistant"
        )
        
        # 线程管理
        self.active_threads: Dict[int, ThreadInfo] = {}
        self.thread_registry: Dict[str, threading.Thread] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        
        # 监控和控制
        self.monitor_thread = None
        self.shutdown_event = threading.Event()
        self.status_lock = threading.Lock()
        
        # 统计信息
        self.total_tasks_executed = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        
        logger.info(f"🎯 线程池管理器初始化完成 (最大工作线程: {max_workers})")
        
        # 启动监控线程
        self._start_monitor()
    
    def submit_task(self, task_name: str, thread_type: ThreadType, 
                   func: Callable, *args, **kwargs) -> concurrent.futures.Future:
        """
        提交任务到线程池
        
        Args:
            task_name: 任务名称
            thread_type: 线程类型
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            Future对象
        """
        try:
            # 创建包装函数以便追踪
            def wrapped_func():
                thread = threading.current_thread()
                thread_id = thread.ident
                
                # 注册线程信息
                with self.status_lock:
                    self.active_threads[thread_id] = ThreadInfo(
                        thread_id=thread_id,
                        name=task_name,
                        thread_type=thread_type,
                        start_time=datetime.now(),
                        status="运行中",
                        last_activity=datetime.now()
                    )
                    self.total_tasks_executed += 1
                
                try:
                    logger.info(f"🚀 启动线程: {task_name} (类型: {thread_type.value}, ID: {thread_id})")
                    result = func(*args, **kwargs)
                    
                    # 更新状态
                    with self.status_lock:
                        if thread_id in self.active_threads:
                            self.active_threads[thread_id].status = "已完成"
                            self.active_threads[thread_id].last_activity = datetime.now()
                    
                    return result
                    
                except Exception as e:
                    # 错误处理
                    with self.status_lock:
                        if thread_id in self.active_threads:
                            self.active_threads[thread_id].status = f"错误: {str(e)}"
                            self.active_threads[thread_id].error_count += 1
                            self.active_threads[thread_id].last_activity = datetime.now()
                        self.total_errors += 1
                    
                    logger.error(f"❌ 线程 {task_name} 执行错误: {e}")
                    logger.error(traceback.format_exc())
                    raise
                
                finally:
                    # 清理线程信息（延迟清理以便监控）
                    def delayed_cleanup():
                        time.sleep(5)  # 保留5秒供监控查看
                        with self.status_lock:
                            if thread_id in self.active_threads:
                                del self.active_threads[thread_id]
                    
                    cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
                    cleanup_thread.start()
            
            # 提交到线程池
            future = self.executor.submit(wrapped_func)
            self.futures[task_name] = future
            
            return future
            
        except Exception as e:
            logger.error(f"❌ 提交任务失败: {task_name}, 错误: {e}")
            raise
    
    def start_persistent_thread(self, task_name: str, thread_type: ThreadType,
                              func: Callable, auto_restart: bool = True,
                              *args, **kwargs) -> threading.Thread:
        """
        启动持久化线程（不使用线程池，适合长期运行的任务）
        
        Args:
            task_name: 任务名称
            thread_type: 线程类型
            func: 要执行的函数
            auto_restart: 是否自动重启
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            线程对象
        """
        def wrapped_func():
            while not self.shutdown_event.is_set():
                thread = threading.current_thread()
                thread_id = thread.ident
                
                try:
                    # 注册线程信息
                    with self.status_lock:
                        if thread_id not in self.active_threads:
                            self.active_threads[thread_id] = ThreadInfo(
                                thread_id=thread_id,
                                name=task_name,
                                thread_type=thread_type,
                                start_time=datetime.now(),
                                status="运行中",
                                last_activity=datetime.now()
                            )
                        else:
                            self.active_threads[thread_id].restart_count += 1
                            self.active_threads[thread_id].start_time = datetime.now()
                            self.active_threads[thread_id].status = "重启中"
                    
                    logger.info(f"🔄 启动持久线程: {task_name} (类型: {thread_type.value}, ID: {thread_id})")
                    
                    # 执行函数
                    func(*args, **kwargs)
                    
                    # 正常结束
                    with self.status_lock:
                        if thread_id in self.active_threads:
                            self.active_threads[thread_id].status = "已完成"
                            self.active_threads[thread_id].last_activity = datetime.now()
                    break
                    
                except Exception as e:
                    # 错误处理
                    with self.status_lock:
                        if thread_id in self.active_threads:
                            self.active_threads[thread_id].status = f"错误: {str(e)}"
                            self.active_threads[thread_id].error_count += 1
                            self.active_threads[thread_id].last_activity = datetime.now()
                        self.total_errors += 1
                    
                    logger.error(f"❌ 持久线程 {task_name} 执行错误: {e}")
                    
                    if not auto_restart:
                        break
                    
                    logger.info(f"🔄 准备重启线程: {task_name} (5秒后)")
                    time.sleep(5)  # 等待后重启
        
        # 创建线程
        thread = threading.Thread(
            target=wrapped_func,
            name=f"{task_name}Thread",
            daemon=True
        )
        
        self.thread_registry[task_name] = thread
        thread.start()
        
        return thread
    
    def stop_thread(self, task_name: str) -> bool:
        """
        停止指定线程
        
        Args:
            task_name: 任务名称
            
        Returns:
            是否成功停止
        """
        try:
            # 取消Future
            if task_name in self.futures:
                future = self.futures[task_name]
                future.cancel()
                del self.futures[task_name]
                logger.info(f"🛑 已取消任务: {task_name}")
                return True
            
            # 停止持久线程（通过设置shutdown标志）
            if task_name in self.thread_registry:
                # 这里我们只能设置标志，具体的停止逻辑需要线程函数自己检查
                logger.info(f"🛑 已请求停止线程: {task_name}")
                return True
            
            logger.warning(f"⚠️ 未找到线程: {task_name}")
            return False
            
        except Exception as e:
            logger.error(f"❌ 停止线程失败: {task_name}, 错误: {e}")
            return False
    
    def get_thread_status(self) -> Dict[str, Any]:
        """获取线程状态信息"""
        with self.status_lock:
            # 当前活跃线程
            active_threads_info = []
            for thread_info in self.active_threads.values():
                runtime = datetime.now() - thread_info.start_time
                active_threads_info.append({
                    "线程ID": thread_info.thread_id,
                    "名称": thread_info.name,
                    "类型": thread_info.thread_type.value,
                    "状态": thread_info.status,
                    "运行时长": str(runtime).split('.')[0],  # 去掉微秒
                    "错误次数": thread_info.error_count,
                    "重启次数": thread_info.restart_count,
                    "最后活动": thread_info.last_activity.strftime("%H:%M:%S")
                })
            
            # 线程池状态
            pool_info = {
                "最大工作线程": self.executor._max_workers,
                "当前活跃线程": len(self.active_threads),
                "已提交任务数": self.total_tasks_executed,
                "总错误数": self.total_errors,
                "运行时长": str(datetime.now() - self.start_time).split('.')[0]
            }
            
            return {
                "线程池信息": pool_info,
                "活跃线程": active_threads_info
            }
    
    def print_status(self):
        """打印线程状态（格式化输出）"""
        status = self.get_thread_status()
        
        print("\n" + "="*80)
        print("🎯 语音助手线程池状态监控")
        print("="*80)
        
        # 线程池信息
        pool_info = status["线程池信息"]
        print(f"📊 线程池信息:")
        for key, value in pool_info.items():
            print(f"   {key}: {value}")
        
        print(f"\n🔧 活跃线程 ({len(status['活跃线程'])} 个):")
        if status["活跃线程"]:
            # 表格头
            print(f"{'ID':<8} {'名称':<20} {'类型':<15} {'状态':<15} {'运行时长':<12} {'错误':<6} {'重启':<6} {'最后活动':<10}")
            print("-" * 100)
            
            # 线程信息
            for thread in status["活跃线程"]:
                print(f"{thread['线程ID']:<8} {thread['名称']:<20} {thread['类型']:<15} "
                      f"{thread['状态']:<15} {thread['运行时长']:<12} {thread['错误次数']:<6} "
                      f"{thread['重启次数']:<6} {thread['最后活动']:<10}")
        else:
            print("   无活跃线程")
        
        print("="*80)
    
    def _start_monitor(self):
        """启动监控线程"""
        def monitor_loop():
            while not self.shutdown_event.is_set():
                try:
                    # 检查死锁或长时间无响应的线程
                    current_time = datetime.now()
                    with self.status_lock:
                        for thread_id, thread_info in list(self.active_threads.items()):
                            # 检查线程是否长时间无活动（超过5分钟）
                            inactive_time = current_time - thread_info.last_activity
                            if inactive_time.total_seconds() > 300:  # 5分钟
                                logger.warning(f"⚠️ 线程 {thread_info.name} 长时间无活动: {inactive_time}")
                    
                    # 每30秒监控一次
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ 监控线程异常: {e}")
                    time.sleep(10)
        
        self.monitor_thread = threading.Thread(
            target=monitor_loop,
            name="ThreadPoolMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("🔍 线程池监控已启动")
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """
        关闭线程池管理器
        
        Args:
            wait: 是否等待线程完成
            timeout: 等待超时时间
        """
        logger.info("🛑 开始关闭线程池管理器...")
        
        # 设置关闭标志
        self.shutdown_event.set()
        
        # 取消所有Future
        for task_name, future in list(self.futures.items()):
            future.cancel()
            logger.info(f"🛑 已取消任务: {task_name}")
        
        # 关闭线程池（兼容不同Python版本）
        try:
            # Python 3.9+ 支持timeout参数
            self.executor.shutdown(wait=wait, timeout=timeout)
        except TypeError:
            # 早期版本不支持timeout参数
            self.executor.shutdown(wait=wait)
        
        # 等待监控线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("✅ 线程池管理器已关闭")

# 全局线程池管理器实例
_global_thread_manager = None

def get_thread_manager() -> ThreadPoolManager:
    """获取全局线程池管理器"""
    global _global_thread_manager
    if _global_thread_manager is None:
        _global_thread_manager = ThreadPoolManager()
    return _global_thread_manager

def shutdown_thread_manager():
    """关闭全局线程池管理器"""
    global _global_thread_manager
    if _global_thread_manager:
        _global_thread_manager.shutdown()
        _global_thread_manager = None

if __name__ == "__main__":
    # 测试线程池管理器
    manager = get_thread_manager()
    
    # 测试任务
    def test_task(name: str, duration: int):
        print(f"任务 {name} 开始执行，将运行 {duration} 秒")
        time.sleep(duration)
        print(f"任务 {name} 完成")
        return f"任务 {name} 的结果"
    
    def test_persistent_task(name: str):
        count = 0
        while count < 10:
            print(f"持久任务 {name} 执行第 {count+1} 次")
            time.sleep(2)
            count += 1
    
    # 提交一些任务
    future1 = manager.submit_task("测试任务1", ThreadType.SPEECH_RECOGNIZER, test_task, "任务1", 3)
    future2 = manager.submit_task("测试任务2", ThreadType.TTS_PLAYER, test_task, "任务2", 5)
    
    # 启动持久任务
    manager.start_persistent_thread("持久测试", ThreadType.WAKE_WORD_DETECTOR, test_persistent_task, True, "持久任务")
    
    # 监控状态
    for i in range(10):
        time.sleep(2)
        manager.print_status()
    
    # 关闭
    manager.shutdown() 