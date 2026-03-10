#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音助手启动脚本 - 修复版
修复唤醒词检测问题
"""

import sys
import os
import time
import threading

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入主要模块
from xiaoxin2_zh import *

def main():
    """主启动函数"""
    try:
        print("🚀 启动语音助手 - 修复版")
        print("="*60)
        
        # 显示系统信息
        print(f"📍 工作目录: {os.getcwd()}")
        print(f"🔧 Python版本: {sys.version.split()[0]}")
        print(f"💻 操作系统: {platform.system()}")
        
        # 检查必要文件
        required_files = ["wakeword.table", "wake.mp3"]
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print(f"⚠️ 缺少必要文件: {', '.join(missing_files)}")
            print("请确保这些文件存在于当前目录")
        
        # 手动初始化各个组件
        print("\n🔧 正在初始化组件...")
        
        # 1. 初始化音频设备锁
        try:
            from audio_device_lock import get_audio_device_lock
            audio_lock = get_audio_device_lock()
            print("✅ 音频设备锁初始化成功")
        except Exception as e:
            print(f"❌ 音频设备锁初始化失败: {e}")
            return False
        
        # 2. 初始化音频会话管理器
        try:
            from audio_session_manager import get_audio_session_manager
            session_manager = get_audio_session_manager()
            print("✅ 音频会话管理器初始化成功")
        except Exception as e:
            print(f"❌ 音频会话管理器初始化失败: {e}")
            return False
        
        # 3. 初始化线程池管理器
        try:
            thread_manager = get_thread_manager()
            print("✅ 线程池管理器初始化成功")
        except Exception as e:
            print(f"❌ 线程池管理器初始化失败: {e}")
            return False
        
        # 4. 启动持续唤醒词检测器
        print("\n🎯 启动持续唤醒词检测器...")
        try:
            detector = start_continuous_detection(continuous_wake_callback)
            if detector:
                print("✅ 持续唤醒词检测器启动成功")
                print("🎤 现在可以说'你好广和通'来唤醒助手")
            else:
                print("❌ 持续唤醒词检测器启动失败")
                return False
        except Exception as e:
            print(f"❌ 启动唤醒词检测器异常: {e}")
            return False
        
        # 5. 启动GIF API服务（如果可用）
        if GIF_INTEGRATION_AVAILABLE:
            try:
                thread_manager.start_persistent_thread(
                    "GIF API服务",
                    ThreadType.SYSTEM_MONITOR,
                    init_gif_api_service,
                    auto_restart=True
                )
                print("✅ GIF API服务已启动")
            except Exception as e:
                print(f"⚠️ GIF API服务启动失败: {e}")
        
        # 6. 启动线程状态监控
        try:
            thread_manager.start_persistent_thread(
                "线程状态监控",
                ThreadType.SYSTEM_MONITOR,
                start_periodic_status_monitor,
                auto_restart=True
            )
            print("✅ 线程状态监控已启动")
        except Exception as e:
            print(f"⚠️ 线程状态监控启动失败: {e}")
        
        print("\n" + "="*60)
        print("🎉 语音助手已成功启动！")
        print("\n📋 使用说明:")
        print("1. 🗣️  说'你好广和通'唤醒助手")
        print("2. 🔊  等待提示音后开始对话")
        print("3. 👋  说'再见'或'退出'结束对话")
        print("4. ⌨️  输入'status'查看系统状态")
        print("5. ⌨️  按Ctrl+C退出程序")
        print("="*60)
        
        # 播放启动欢迎音
        if is_first_startup:
            print("\n🎵 播放启动欢迎音...")
            if os.path.exists("wakeup_word.mp3"):
                play_mp3_audio("wakeup_word.mp3", "system")
            else:
                text_to_speech("语音助手已启动，请说你好广和通来唤醒我", is_welcome=True)
        
        # 主循环 - 保持程序运行并处理用户命令
        print("\n🔄 进入主监听循环...")
        
        last_status_time = time.time()
        status_interval = 300  # 每5分钟显示一次状态
        
        while True:
            try:
                # 定期显示状态
                current_time = time.time()
                if current_time - last_status_time > status_interval:
                    print(f"\n⏰ 系统运行中... (运行时长: {int((current_time - start_time) / 60)} 分钟)")
                    last_status_time = current_time
                
                # 检查用户输入
                import select
                if select.select([sys.stdin], [], [], 1.0)[0]:
                    user_input = input().strip().lower()
                    
                    if user_input == 'status':
                        show_thread_status()
                    elif user_input == 'quit' or user_input == 'exit':
                        print("👋 用户请求退出...")
                        break
                    elif user_input == 'restart':
                        print("🔄 重启唤醒词检测...")
                        stop_continuous_detection()
                        time.sleep(1)
                        detector = start_continuous_detection(continuous_wake_callback)
                        if detector:
                            print("✅ 唤醒词检测器重启成功")
                        else:
                            print("❌ 唤醒词检测器重启失败")
                    elif user_input == 'help':
                        print("\n📚 可用命令:")
                        print("  status  - 查看系统状态")
                        print("  restart - 重启唤醒词检测器")
                        print("  quit    - 退出程序")
                        print("  help    - 显示此帮助")
                    elif user_input == 'test':
                        print("🧪 测试唤醒词检测...")
                        # 手动触发唤醒事件用于测试
                        test_event = {
                            'timestamp': time.time(),
                            'text': '你好广和通',
                            'confidence': 1.0
                        }
                        continuous_wake_callback(test_event)
                    else:
                        print(f"❓ 未知命令: {user_input}，输入'help'查看帮助")
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\n👋 收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"\n❌ 主循环异常: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"\n❌ 启动异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        print("\n🧹 正在清理资源...")
        
        try:
            stop_continuous_detection()
            print("✅ 已停止唤醒词检测器")
        except:
            pass
        
        try:
            stop_background_keyword_listening()
            print("✅ 已停止后台监听")
        except:
            pass
        
        try:
            if GIF_INTEGRATION_AVAILABLE:
                stop_gif_service()
                print("✅ 已停止GIF API服务")
        except:
            pass
        
        try:
            shutdown_thread_manager()
            print("✅ 已关闭线程池管理器")
        except:
            pass
        
        print("🎯 语音助手已安全关闭")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 