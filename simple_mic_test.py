#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版麦克风测试 - 模拟指尖识词的暂停/恢复流程
"""

import os
import sys
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pause_resume_mechanism():
    """测试暂停/恢复机制"""
    try:
        logger.info("🧪 开始简化版麦克风释放测试")
        
        # 添加switchrole路径
        switchrole_path = os.path.join(os.getcwd(), 'switchrole')
        if switchrole_path not in sys.path:
            sys.path.insert(0, switchrole_path)
        
        # 切换到switchrole目录
        original_cwd = os.getcwd()
        os.chdir(switchrole_path)
        
        try:
            # 加载环境变量
            if os.path.exists('xiaoxin.env'):
                from dotenv import load_dotenv
                load_dotenv('xiaoxin.env')
                logger.info("✅ 环境变量已加载")
            
            # 导入模块
            import xiaoxin2_zh_new as xiaoxin_module
            logger.info("✅ 语音助手模块导入成功")
            
            # 测试中断机制
            logger.info("🔧 测试中断机制...")
            
            # 1. 设置中断
            logger.info("⏸️ 设置中断标志...")
            xiaoxin_module.set_interrupt()
            logger.info("✅ 中断标志已设置")
            
            # 2. 等待中断生效
            time.sleep(2)
            
            # 3. 测试录音
            logger.info("🎤 测试录音（5秒）...")
            success = test_recording()
            
            if success:
                logger.info("✅ 录音成功 - 麦克风已释放")
            else:
                logger.error("❌ 录音失败 - 麦克风可能被占用")
            
            # 4. 清除中断
            logger.info("▶️ 清除中断标志...")
            xiaoxin_module.clear_interrupt()
            logger.info("✅ 中断标志已清除")
            
            return success
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False

def test_recording() -> bool:
    """测试录音功能"""
    try:
        from alsa_speech_recognizer import ALSASpeechRecognizer
        
        # 创建录音器
        recognizer = ALSASpeechRecognizer(card_name="lahainayupikiot", use_usb_mic=True)
        recognizer.sample_rate = 48000
        recognizer.channels = 2
        recognizer.format = "S16_LE"
        
        if not recognizer.initialize():
            logger.error("❌ 录音器初始化失败")
            return False
        
        # 录音文件
        test_file = "simple_test_recording.wav"
        
        logger.info("🔴 开始录音，请说话...")
        success = recognizer.record_audio_to_file(5, test_file)
        
        if success and os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            logger.info(f"📁 录音完成，文件大小: {file_size} 字节")
            
            # 清理文件
            try:
                os.remove(test_file)
            except:
                pass
            
            return file_size > 1000
        else:
            logger.error("❌ 录音失败或文件不存在")
            return False
            
    except Exception as e:
        logger.error(f"❌ 录音测试异常: {e}")
        return False

def test_direct_recording():
    """直接测试录音（不涉及语音助手）"""
    try:
        logger.info("🎤 直接录音测试（不涉及语音助手）...")
        
        # 添加switchrole路径
        switchrole_path = os.path.join(os.getcwd(), 'switchrole')
        if switchrole_path not in sys.path:
            sys.path.insert(0, switchrole_path)
        
        from alsa_speech_recognizer import ALSASpeechRecognizer
        
        recognizer = ALSASpeechRecognizer(card_name="lahainayupikiot", use_usb_mic=True)
        recognizer.sample_rate = 48000
        recognizer.channels = 2
        recognizer.format = "S16_LE"
        
        if not recognizer.initialize():
            logger.error("❌ 录音器初始化失败")
            return False
        
        test_file = "direct_test_recording.wav"
        
        logger.info("🔴 直接录音测试（3秒），请说话...")
        success = recognizer.record_audio_to_file(3, test_file)
        
        if success and os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            logger.info(f"✅ 直接录音成功，文件大小: {file_size} 字节")
            
            # 清理文件
            try:
                os.remove(test_file)
            except:
                pass
            
            return True
        else:
            logger.error("❌ 直接录音失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 直接录音测试异常: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始麦克风释放测试")
    
    try:
        # 1. 先测试直接录音
        logger.info("\n" + "="*50)
        logger.info("第一步：测试直接录音（基线测试）")
        logger.info("="*50)
        
        direct_success = test_direct_recording()
        
        if not direct_success:
            logger.error("❌ 直接录音都失败了，请检查麦克风设备")
            return
        
        # 2. 测试暂停/恢复机制
        logger.info("\n" + "="*50)
        logger.info("第二步：测试暂停/恢复机制")
        logger.info("="*50)
        
        pause_resume_success = test_pause_resume_mechanism()
        
        # 3. 结果总结
        logger.info("\n" + "="*50)
        logger.info("测试结果总结")
        logger.info("="*50)
        
        logger.info(f"直接录音测试: {'✅ 成功' if direct_success else '❌ 失败'}")
        logger.info(f"暂停/恢复测试: {'✅ 成功' if pause_resume_success else '❌ 失败'}")
        
        if direct_success and pause_resume_success:
            logger.info("🎉 所有测试通过！麦克风释放机制工作正常")
        elif direct_success and not pause_resume_success:
            logger.error("💥 暂停/恢复机制有问题，但基础录音功能正常")
        else:
            logger.error("💥 基础录音功能有问题")
        
    except KeyboardInterrupt:
        logger.info("🛑 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试过程异常: {e}")
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    main()
