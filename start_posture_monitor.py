#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
姿势检测系统启动脚本
"""

import sys
import os
import logging

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('posture_monitor.log'),
        logging.StreamHandler()
    ]
)

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 智能姿势检测系统启动")
    print("=" * 60)
    
    # 启动应用
    print("\n🚀 启动姿势检测界面...")
    try:
        from posture_monitor_ui import main as ui_main
        ui_main()
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        logging.exception("启动失败")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
