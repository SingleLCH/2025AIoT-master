#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音助手线程状态监控工具

独立工具，用于实时监控xiaoxin2_zh.py的线程运行状态
"""

import time
import sys
import threading
from datetime import datetime
from thread_pool_manager import get_thread_manager

def clear_screen():
    """清屏"""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')

def show_real_time_status():
    """实时显示线程状态"""
    try:
        manager = get_thread_manager()
        
        while True:
            clear_screen()
            
            print("=" * 100)
            print(f"🎯 语音助手线程状态实时监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 100)
            
            # 显示线程状态
            manager.print_status()
            
            print("\n💡 监控说明:")
            print("  • 持续唤醒词检测: 负责监听'你好广和通'唤醒词")
            print("  • 线程状态监控: 定期打印线程状态信息")
            print("  • 提醒检查: 当启用时检查待办提醒")
            print("  • 语音对话处理: 处理用户对话请求")
            print("  • 语音合成播放: 执行TTS语音播放")
            print("  • GIF API服务: 控制表情动画显示")
            print("  • 音频流处理: 处理音频数据流")
            
            print("\n🔧 控制命令:")
            print("  程序将每3秒自动刷新")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 监控异常: {e}")
        sys.exit(1)

def show_current_status():
    """显示当前状态（一次性）"""
    try:
        manager = get_thread_manager()
        
        print("=" * 100)
        print(f"🎯 语音助手线程状态快照 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        
        manager.print_status()
        
        print("\n📊 线程类型统计:")
        thread_types = {}
        with manager.status_lock:
            for thread_info in manager.active_threads.values():
                thread_type = thread_info.thread_type.value
                if thread_type not in thread_types:
                    thread_types[thread_type] = {'运行中': 0, '已完成': 0, '异常': 0}
                
                if '运行中' in thread_info.status:
                    thread_types[thread_type]['运行中'] += 1
                elif '已完成' in thread_info.status:
                    thread_types[thread_type]['已完成'] += 1
                elif '异常' in thread_info.status:
                    thread_types[thread_type]['异常'] += 1
        
        for thread_type, counts in thread_types.items():
            print(f"  {thread_type}: 运行中 {counts['运行中']}, 已完成 {counts['已完成']}, 异常 {counts['异常']}")
        
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--realtime':
        # 实时监控模式
        print("🚀 启动实时线程状态监控...")
        show_real_time_status()
    else:
        # 单次查看模式
        show_current_status()

if __name__ == "__main__":
    print("🎯 语音助手线程状态监控工具")
    print("使用方法:")
    print("  python3 thread_status_monitor.py           # 查看当前状态")
    print("  python3 thread_status_monitor.py --realtime # 实时监控模式")
    print()
    
    main() 