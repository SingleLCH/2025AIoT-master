#!/bin/bash
# 语音助手启动脚本 - 新架构版本

echo "🚀 启动语音助手 v2.0 (三线程架构)"
echo "按 Ctrl+C 停止程序"
echo "================================"

# 检查Python版本
python3 --version

# 启动新架构
python3 voice_assistant_main.py
