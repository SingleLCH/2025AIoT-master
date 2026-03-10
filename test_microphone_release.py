#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
麦克风释放测试脚本 - 测试语音助手暂停/恢复机制
不依赖GUI，直接测试麦克风权限的释放和重新获取
"""

import os
import sys
import time
import logging
import threading
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MicrophoneReleaseTest:
    """麦克风释放测试类"""
    
    def __init__(self):
        self.voice_service = None
        self.xiaoxin_module = None
        self.audio_manager = None
        
    def setup_voice_assistant(self):
        """设置语音助手"""
        try:
            logger.info("🚀 开始初始化语音助手...")
            
            # 添加switchrole目录到路径
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
                
                # 导入语音助手模块
                import xiaoxin2_zh_new as xiaoxin_module
                self.xiaoxin_module = xiaoxin_module
                logger.info("✅ 语音助手模块导入成功")
                
                # 初始化音频设备管理器
                self.audio_manager = xiaoxin_module.AudioDeviceManager()
                if not self.audio_manager.init_devices():
                    logger.error("❌ 音频设备初始化失败")
                    return False
                
                logger.info("✅ 音频设备管理器初始化成功")
                return True
                
            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"❌ 语音助手初始化失败: {e}")
            return False
    
    def start_voice_assistant(self):
        """启动语音助手"""
        try:
            logger.info("🎤 启动语音助手...")
            
            # 启动语音助手主循环（在后台线程中）
            def run_voice_assistant():
                try:
                    # 设置系统运行状态
                    self.xiaoxin_module.system_running.set()
                    
                    # 启动三线程架构
                    thread_a = self.xiaoxin_module.ThreadA(self.audio_manager)
                    thread_b = self.xiaoxin_module.ThreadB(self.audio_manager)
                    thread_c = self.xiaoxin_module.ThreadC(self.audio_manager)
                    
                    # 启动线程
                    threading.Thread(target=thread_a.run, daemon=True).start()
                    threading.Thread(target=thread_b.run, daemon=True).start()
                    threading.Thread(target=thread_c.run, daemon=True).start()
                    
                    logger.info("✅ 语音助手三线程已启动")
                    
                    # 保持运行
                    while self.xiaoxin_module.system_running.is_set():
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"❌ 语音助手运行异常: {e}")
            
            # 在后台线程中启动语音助手
            voice_thread = threading.Thread(target=run_voice_assistant, daemon=True)
            voice_thread.start()
            
            # 等待语音助手启动
            time.sleep(3)
            logger.info("✅ 语音助手已启动并运行")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动语音助手失败: {e}")
            return False
    
    def test_microphone_pause_resume(self):
        """测试麦克风暂停和恢复"""
        try:
            logger.info("🔧 开始测试麦克风暂停/恢复机制...")
            
            # 1. 检查语音助手是否正在运行
            logger.info("📊 检查语音助手运行状态...")
            if not self.xiaoxin_module.system_running.is_set():
                logger.error("❌ 语音助手未运行")
                return False
            
            logger.info("✅ 语音助手正在运行")
            
            # 2. 暂停语音助手
            logger.info("⏸️ 暂停语音助手以释放麦克风...")
            self.xiaoxin_module.set_interrupt()
            time.sleep(2)  # 等待暂停生效
            logger.info("✅ 语音助手已暂停")
            
            # 3. 测试录音
            logger.info("🎤 测试录音功能...")
            recording_success = self._test_recording()
            
            if recording_success:
                logger.info("✅ 录音测试成功 - 麦克风已正确释放")
            else:
                logger.error("❌ 录音测试失败 - 麦克风可能仍被占用")
            
            # 4. 恢复语音助手
            logger.info("▶️ 恢复语音助手...")
            self.xiaoxin_module.clear_interrupt()
            time.sleep(2)  # 等待恢复生效
            logger.info("✅ 语音助手已恢复")
            
            return recording_success
            
        except Exception as e:
            logger.error(f"❌ 麦克风暂停/恢复测试失败: {e}")
            return False
    
    def _test_recording(self) -> bool:
        """测试录音功能"""
        try:
            logger.info("🎙️ 开始录音测试（3秒）...")
            
            # 使用ALSA录音器测试
            from alsa_speech_recognizer import ALSASpeechRecognizer
            recognizer = ALSASpeechRecognizer(card_name="lahainayupikiot", use_usb_mic=True)
            
            # 配置录音参数
            recognizer.sample_rate = 48000
            recognizer.channels = 2
            recognizer.format = "S16_LE"
            
            if not recognizer.initialize():
                logger.error("❌ ALSA录音器初始化失败")
                return False
            
            # 生成测试录音文件
            test_file = "test_recording.wav"
            
            # 录制3秒音频
            logger.info("🔴 开始录音（请说话）...")
            success = recognizer.record_audio_to_file(3, test_file)
            
            if success:
                logger.info(f"✅ 录音成功，文件: {test_file}")
                
                # 检查文件大小
                if os.path.exists(test_file):
                    file_size = os.path.getsize(test_file)
                    logger.info(f"📁 录音文件大小: {file_size} 字节")
                    
                    # 清理测试文件
                    try:
                        os.remove(test_file)
                        logger.info("🗑️ 测试文件已清理")
                    except:
                        pass
                    
                    return file_size > 1000  # 如果文件大于1KB，认为录音成功
                else:
                    logger.error("❌ 录音文件不存在")
                    return False
            else:
                logger.error("❌ 录音失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 录音测试异常: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            logger.info("🧹 清理测试资源...")
            
            if self.xiaoxin_module:
                # 停止语音助手
                self.xiaoxin_module.system_running.clear()
                logger.info("✅ 语音助手已停止")
            
            logger.info("✅ 资源清理完成")
            
        except Exception as e:
            logger.error(f"❌ 资源清理失败: {e}")

def main():
    """主函数"""
    logger.info("🧪 麦克风释放测试开始")
    
    test = MicrophoneReleaseTest()
    
    try:
        # 1. 设置语音助手
        if not test.setup_voice_assistant():
            logger.error("❌ 语音助手设置失败")
            return
        
        # 2. 启动语音助手
        if not test.start_voice_assistant():
            logger.error("❌ 语音助手启动失败")
            return
        
        # 3. 等待语音助手稳定运行
        logger.info("⏳ 等待语音助手稳定运行...")
        time.sleep(5)
        
        # 4. 测试麦克风暂停/恢复
        success = test.test_microphone_pause_resume()
        
        if success:
            logger.info("🎉 测试成功！麦克风释放机制工作正常")
        else:
            logger.error("💥 测试失败！麦克风释放机制存在问题")
        
        # 5. 等待一段时间观察
        logger.info("⏳ 等待10秒观察语音助手恢复状态...")
        time.sleep(10)
        
    except KeyboardInterrupt:
        logger.info("🛑 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试过程异常: {e}")
    finally:
        # 清理资源
        test.cleanup()
        logger.info("🏁 测试结束")

if __name__ == "__main__":
    main()
