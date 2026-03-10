#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速麦克风测试 - 模拟enhanced_gesture_word_handler的暂停/恢复流程
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class MockVoiceAssistantService:
    """模拟语音助手服务"""
    
    def __init__(self):
        self.xiaoxin_module = None
        self._setup_module()
    
    def _setup_module(self):
        """设置模块"""
        try:
            switchrole_path = os.path.join(os.getcwd(), 'switchrole')
            if switchrole_path not in sys.path:
                sys.path.insert(0, switchrole_path)
            
            original_cwd = os.getcwd()
            os.chdir(switchrole_path)
            
            try:
                if os.path.exists('xiaoxin.env'):
                    from dotenv import load_dotenv
                    load_dotenv('xiaoxin.env')
                
                import xiaoxin2_zh_new as xiaoxin_module
                self.xiaoxin_module = xiaoxin_module
                logger.info("✅ 语音助手模块加载成功")
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"❌ 模块设置失败: {e}")
    
    def pause_for_external_audio(self):
        """为外部音频暂停语音功能"""
        if self.xiaoxin_module:
            logger.info("⏸️ 调用 xiaoxin_module.set_interrupt()")
            self.xiaoxin_module.set_interrupt()
        else:
            logger.error("❌ xiaoxin_module 未加载")
    
    def resume_after_external_audio(self):
        """外部音频结束后恢复语音功能"""
        if self.xiaoxin_module:
            logger.info("▶️ 调用 xiaoxin_module.clear_interrupt()")
            self.xiaoxin_module.clear_interrupt()
        else:
            logger.error("❌ xiaoxin_module 未加载")

class MockWidget:
    """模拟主窗口"""
    
    def __init__(self):
        self.voice_assistant_service = MockVoiceAssistantService()

def simulate_enhanced_gesture_word_pause_resume():
    """模拟enhanced_gesture_word_handler的暂停/恢复流程"""
    
    # 模拟PyQt应用和窗口
    mock_widget = MockWidget()
    
    def _pause_voice_assistant():
        """模拟 enhanced_gesture_word_handler._pause_voice_assistant()"""
        try:
            logger.info("🔧 模拟暂停语音助手以释放麦克风...")
            
            # 模拟寻找语音助手服务实例（简化版）
            widget = mock_widget  # 在真实环境中这是通过QApplication.instance()找到的
            
            if hasattr(widget, 'voice_assistant_service') and widget.voice_assistant_service:
                logger.info("找到语音助手服务，执行暂停操作...")
                widget.voice_assistant_service.pause_for_external_audio()
                logger.info("✅ 语音助手已暂停")
                
                # 等待暂停生效（增加等待时间确保进程完全停止）
                time.sleep(2.0)
                logger.info("✅ 麦克风应已释放")
                return True
            else:
                logger.error("❌ 未找到语音助手服务")
                return False
                
        except Exception as e:
            logger.error(f"❌ 暂停语音助手失败: {e}")
            return False
    
    def _resume_voice_assistant():
        """模拟 enhanced_gesture_word_handler._resume_voice_assistant()"""
        try:
            logger.info("🔧 模拟恢复语音助手...")
            
            # 模拟寻找语音助手服务实例（简化版）
            widget = mock_widget
            
            if hasattr(widget, 'voice_assistant_service') and widget.voice_assistant_service:
                widget.voice_assistant_service.resume_after_external_audio()
                logger.info("✅ 语音助手已恢复")
                return True
            else:
                logger.error("❌ 未找到语音助手服务")
                return False
                
        except Exception as e:
            logger.error(f"❌ 恢复语音助手失败: {e}")
            return False
    
    def _test_recording():
        """测试录音"""
        try:
            logger.info("🎤 测试录音（3秒）...")
            
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
            
            test_file = "quick_test_recording.wav"
            
            logger.info("🔴 开始录音，请说话...")
            success = recognizer.record_audio_to_file(3, test_file)
            
            if success and os.path.exists(test_file):
                file_size = os.path.getsize(test_file)
                logger.info(f"✅ 录音成功，文件大小: {file_size} 字节")
                
                # 清理文件
                try:
                    os.remove(test_file)
                except:
                    pass
                
                return file_size > 1000
            else:
                logger.error("❌ 录音失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 录音测试异常: {e}")
            return False
    
    # 执行测试流程
    logger.info("🧪 开始模拟指尖识词的暂停/恢复流程")
    
    try:
        # 1. 暂停语音助手
        logger.info("\n" + "="*40)
        logger.info("步骤1: 暂停语音助手")
        logger.info("="*40)
        
        pause_success = _pause_voice_assistant()
        if not pause_success:
            logger.error("❌ 暂停失败，终止测试")
            return False
        
        # 2. 测试录音
        logger.info("\n" + "="*40)
        logger.info("步骤2: 测试录音")
        logger.info("="*40)
        
        recording_success = _test_recording()
        
        # 3. 恢复语音助手
        logger.info("\n" + "="*40)
        logger.info("步骤3: 恢复语音助手")
        logger.info("="*40)
        
        resume_success = _resume_voice_assistant()
        
        # 4. 结果
        logger.info("\n" + "="*40)
        logger.info("测试结果")
        logger.info("="*40)
        
        logger.info(f"暂停操作: {'✅ 成功' if pause_success else '❌ 失败'}")
        logger.info(f"录音测试: {'✅ 成功' if recording_success else '❌ 失败'}")
        logger.info(f"恢复操作: {'✅ 成功' if resume_success else '❌ 失败'}")
        
        overall_success = pause_success and recording_success and resume_success
        
        if overall_success:
            logger.info("🎉 整体测试成功！暂停/恢复机制工作正常")
        else:
            logger.error("💥 测试失败！暂停/恢复机制存在问题")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"❌ 测试流程异常: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 快速麦克风释放测试")
    
    try:
        success = simulate_enhanced_gesture_word_pause_resume()
        
        if success:
            logger.info("✅ 测试通过 - enhanced_gesture_word_handler的暂停/恢复机制应该能正常工作")
        else:
            logger.error("❌ 测试失败 - enhanced_gesture_word_handler可能仍有问题")
        
    except KeyboardInterrupt:
        logger.info("🛑 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    main()
