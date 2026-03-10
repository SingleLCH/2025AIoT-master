#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置指尖单词功能所需的音频文件和文件夹
"""

import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_folders():
    """创建必要的文件夹"""
    folders = [
        "word_audio",      # 单词TTS音频文件夹
        "word_recordings"  # 录音文件夹
    ]
    
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logger.info(f"✅ 创建文件夹: {folder}")
        else:
            logger.info(f"📁 文件夹已存在: {folder}")

def create_placeholder_audio_files():
    """创建占位符音频文件"""
    audio_files = [
        "1st.wav",   # 第一轮提示音
        "2nd.wav",   # 第二轮提示音
        "3rd.wav",   # 第三轮提示音
        "good.wav",  # 成功音频
        "bad.wav"    # 失败音频
    ]
    
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            # 创建空的WAV文件作为占位符
            # 实际使用时需要替换为真实的音频文件
            with open(audio_file, 'wb') as f:
                # 写入最小的WAV文件头（44字节）
                wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
                f.write(wav_header)
            logger.info(f"📄 创建占位符音频文件: {audio_file}")
        else:
            logger.info(f"🎵 音频文件已存在: {audio_file}")

def check_dependencies():
    """检查依赖项"""
    logger.info("🔍 检查依赖项...")
    
    try:
        import sounddevice
        logger.info("✅ sounddevice 已安装")
    except ImportError:
        logger.warning("⚠️ sounddevice 未安装，请运行: pip install sounddevice")
    
    try:
        from tencentcloud.common import credential
        logger.info("✅ tencentcloud-sdk-python 已安装")
    except ImportError:
        logger.warning("⚠️ tencentcloud-sdk-python 未安装，请运行: pip install tencentcloud-sdk-python")
    
    try:
        import dashscope
        logger.info("✅ dashscope 已安装")
    except ImportError:
        logger.warning("⚠️ dashscope 未安装，请运行: pip install dashscope")

def show_usage_instructions():
    """显示使用说明"""
    print("\n" + "="*60)
    print("🎯 指尖单词增强功能设置完成")
    print("="*60)
    
    print("\n📋 功能说明:")
    print("1. 🔍 识别手指指向的单词")
    print("2. 🎵 使用longxiaochun声音朗读单词")
    print("3. 🎤 录音跟读练习（3轮机会）")
    print("4. 📊 腾讯云语音评测打分")
    print("5. 🎉 根据分数播放成功/失败音频")
    
    print("\n📁 文件夹结构:")
    print("├── word_audio/        # 单词TTS音频文件")
    print("├── word_recordings/   # 用户录音文件")
    print("├── 1st.wav           # 第一轮提示音")
    print("├── 2nd.wav           # 第二轮提示音")
    print("├── 3rd.wav           # 第三轮提示音")
    print("├── good.wav          # 成功音频")
    print("└── bad.wav           # 失败音频")
    
    print("\n🔧 使用流程:")
    print("1. 打开指尖单词功能")
    print("2. 用手指指向单词")
    print("3. 发送6-0-1拍照")
    print("4. 系统识别单词并开始学习流程:")
    print("   • TTS播放3遍单词（间隔3秒）")
    print("   • 播放轮次提示音（1st.wav等）")
    print("   • 录音5秒用户跟读")
    print("   • 语音评测打分")
    print("   • 分数≥90分：播放good.wav，结束")
    print("   • 分数<90分：继续下一轮（最多3轮）")
    print("   • 3轮后：播放bad.wav，结束")
    
    print("\n⚙️ 配置要求:")
    print("• DASHSCOPE_API_KEY: 阿里云TTS API密钥")
    print("• 腾讯云语音评测API密钥已内置")
    print("• MQTT连接用于录音控制")
    
    print("\n🎵 音频文件说明:")
    print("• 当前创建的是占位符文件")
    print("• 请替换为实际的提示音和反馈音频")
    print("• 建议音频格式：WAV，16kHz，单声道")

def main():
    """主函数"""
    print("🚀 设置指尖单词增强功能")
    print("="*50)
    
    # 创建文件夹
    create_folders()
    
    # 创建占位符音频文件
    create_placeholder_audio_files()
    
    # 检查依赖项
    check_dependencies()
    
    # 显示使用说明
    show_usage_instructions()
    
    print("\n✅ 设置完成！")

if __name__ == "__main__":
    main()
