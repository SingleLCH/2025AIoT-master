#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频进程检查脚本 - 检查当前运行的音频相关进程
"""

import subprocess
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def check_audio_processes():
    """检查当前运行的音频相关进程"""
    logger.info("🔍 检查当前音频相关进程...")
    
    # 检查的进程类型
    process_types = [
        ('arecord', '录音进程'),
        ('aplay', '播放进程'),
        ('pulseaudio', 'PulseAudio'),
        ('speechsdk', 'Azure语音SDK'),
        ('python.*xiaoxin', '语音助手'),
        ('alsa', 'ALSA相关')
    ]
    
    for pattern, description in process_types:
        try:
            result = subprocess.run(
                ['pgrep', '-f', pattern], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logger.info(f"✅ {description}: 找到 {len(pids)} 个进程")
                
                # 获取详细信息
                for pid in pids:
                    try:
                        ps_result = subprocess.run(
                            ['ps', '-p', pid, '-o', 'pid,ppid,cmd'],
                            capture_output=True,
                            text=True
                        )
                        if ps_result.returncode == 0:
                            lines = ps_result.stdout.strip().split('\n')
                            if len(lines) > 1:  # 跳过标题行
                                logger.info(f"   PID {pid}: {lines[1]}")
                    except:
                        logger.info(f"   PID {pid}: (无法获取详细信息)")
            else:
                logger.info(f"❌ {description}: 未找到进程")
                
        except Exception as e:
            logger.error(f"❌ 检查{description}失败: {e}")

def test_interrupt_mechanism():
    """测试中断机制"""
    logger.info("\n" + "="*50)
    logger.info("测试中断机制")
    logger.info("="*50)
    
    try:
        # 添加switchrole路径
        import sys
        import os
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
            
            # 导入模块
            import xiaoxin2_zh_new as xiaoxin_module
            
            logger.info("🔍 测试前检查进程状态:")
            check_audio_processes()
            
            logger.info("\n⏸️ 调用 set_interrupt()...")
            xiaoxin_module.set_interrupt()
            
            logger.info("⏳ 等待2秒让中断生效...")
            time.sleep(2)
            
            logger.info("\n🔍 中断后检查进程状态:")
            check_audio_processes()
            
            logger.info("\n▶️ 调用 clear_interrupt()...")
            xiaoxin_module.clear_interrupt()
            
            logger.info("✅ 中断机制测试完成")
            return True
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        logger.error(f"❌ 中断机制测试失败: {e}")
        return False

def test_direct_recording_after_interrupt():
    """在中断后测试直接录音"""
    logger.info("\n" + "="*50)
    logger.info("测试中断后直接录音")
    logger.info("="*50)
    
    try:
        # 先执行中断
        test_interrupt_mechanism()
        
        logger.info("\n🎤 尝试直接录音...")
        
        # 添加switchrole路径
        import sys
        import os
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
        
        test_file = "interrupt_test_recording.wav"
        
        logger.info("🔴 开始录音（3秒），请说话...")
        success = recognizer.record_audio_to_file(3, test_file)
        
        if success and os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            logger.info(f"✅ 中断后录音成功，文件大小: {file_size} 字节")
            
            # 清理文件
            try:
                os.remove(test_file)
            except:
                pass
            
            return True
        else:
            logger.error("❌ 中断后录音失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 中断后录音测试异常: {e}")
        return False

def main():
    """主函数"""
    logger.info("🧪 音频进程检查和中断测试")
    
    try:
        # 1. 检查初始进程状态
        logger.info("\n" + "="*50)
        logger.info("步骤1: 检查初始进程状态")
        logger.info("="*50)
        check_audio_processes()
        
        # 2. 测试中断机制
        interrupt_success = test_interrupt_mechanism()
        
        # 3. 测试中断后录音
        recording_success = test_direct_recording_after_interrupt()
        
        # 4. 最终检查
        logger.info("\n" + "="*50)
        logger.info("步骤4: 最终进程状态检查")
        logger.info("="*50)
        check_audio_processes()
        
        # 5. 结果总结
        logger.info("\n" + "="*50)
        logger.info("测试结果总结")
        logger.info("="*50)
        
        logger.info(f"中断机制测试: {'✅ 成功' if interrupt_success else '❌ 失败'}")
        logger.info(f"中断后录音测试: {'✅ 成功' if recording_success else '❌ 失败'}")
        
        if interrupt_success and recording_success:
            logger.info("🎉 所有测试通过！中断机制工作正常")
        else:
            logger.error("💥 测试失败！中断机制存在问题")
        
    except KeyboardInterrupt:
        logger.info("🛑 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
    
    logger.info("🏁 测试结束")

if __name__ == "__main__":
    main()
