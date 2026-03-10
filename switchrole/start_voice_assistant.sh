#!/bin/bash

echo "🚀 启动广和通语音助手"
echo "=" * 50

# 确保PulseAudio在运行
echo "🔧 配置音频系统..."
pulseaudio --start 2>/dev/null

# 加载USB麦克风到PulseAudio
echo "🎤 配置USB麦克风..."
pactl load-module module-alsa-source device=hw:0 source_name=usb_mic 2>/dev/null || echo "麦克风模块已存在"

# 设置默认音频源
echo "🔊 设置默认音频源..."
pactl set-default-source usb_mic

# 检查配置
echo "✅ 音频配置完成:"
echo "   默认源: $(pactl info | grep 'Default Source' | cut -d: -f2 | tr -d ' ')"

echo ""
echo "🎵 启动语音助手..."
echo "💡 现在可以说'你好广和通'来唤醒助手"

# 启动主程序
python3 xiaoxin2_zh.py 