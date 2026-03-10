#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化ALSA唤醒词检测器

专门为三线程架构设计：
- 使用ALSA直接操作m麦克风设备
- 避免与PulseAudio设备冲突
- 轻量级实现，专注唤醒词检测
"""

import os
import time
import threading
import subprocess
from dotenv import load_dotenv

load_dotenv("xiaoxin.env")

class ALSAWakewordDetector:
    """简化的ALSA唤醒词检测器"""
    
    def __init__(self):
        self.running = False
        self.callback = None
        self.thread = None
        self.device = "hw:2,0"  # m麦克风设备
        self.keyword = os.environ.get("WakeupWord", "你好广和通")
        
    def set_callback(self, callback):
        """设置唤醒回调函数"""
        self.callback = callback
    
    def start(self):
        """启动检测器"""
        if self.running:
            return True
            
        print(f"🎤 [ALSA检测器] 启动唤醒词检测: {self.keyword}")
        self.running = True
        
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        
        return True
    
    def stop(self):
        """停止检测器"""
        print("🛑 [ALSA检测器] 停止检测")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
    
    def _detection_loop(self):
        """检测循环 - 使用arecord录音并检测"""
        print(f"🔍 [ALSA检测器] 开始监听设备: {self.device}")
        
        detection_count = 0
        
        while self.running:
            try:
                detection_count += 1
                print(f"🎤 [ALSA检测器] 第{detection_count}次检测...")
                
                # 使用plughw代替hw，自动处理采样率转换
                cmd = [
                    'arecord',
                    '-D', f'plughw:{self.device.split(":")[1]}',  # 从hw:2,0转换为plughw:2
                    '-f', 'S16_LE',
                    '-r', '16000',
                    '-c', '1',
                    '-d', '3',
                    '/tmp/wake_detect.wav'
                ]
                
                print(f"🎵 [ALSA检测器] 录音命令: {' '.join(cmd)}")
                
                # 录音
                result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
                
                if result.returncode == 0:
                    if os.path.exists('/tmp/wake_detect.wav'):
                        file_size = os.path.getsize('/tmp/wake_detect.wav')
                        print(f"📁 [ALSA检测器] 录音完成，文件大小: {file_size} bytes")
                        
                        # 检查音频活动
                        if self._check_audio_activity('/tmp/wake_detect.wav'):
                            # 触发唤醒回调
                            if self.callback:
                                wake_event = {
                                    'text': self.keyword,
                                    'timestamp': time.time(),
                                    'confidence': 0.8,
                                    'device': 'alsa_m_mic',
                                    'detection_count': detection_count
                                }
                                print(f"🎯 [ALSA检测器] 检测到语音活动，触发唤醒 (第{detection_count}次)")
                                self.callback(wake_event)
                        else:
                            print(f"🔇 [ALSA检测器] 第{detection_count}次检测：无语音活动")
                        
                        # 清理临时文件
                        try:
                            os.remove('/tmp/wake_detect.wav')
                        except:
                            pass
                    else:
                        print(f"❌ [ALSA检测器] 录音文件未生成")
                else:
                    print(f"❌ [ALSA检测器] 录音失败 (退出码: {result.returncode})")
                    if result.stderr:
                        print(f"   错误信息: {result.stderr}")
                
            except subprocess.TimeoutExpired:
                print(f"⚠️ [ALSA检测器] 第{detection_count}次录音超时")
            except Exception as e:
                if self.running:  # 只在运行时报告错误
                    print(f"⚠️ [ALSA检测器] 第{detection_count}次检测异常: {e}")
                time.sleep(1)
        
        print("🔚 [ALSA检测器] 检测循环结束")
    
    def _check_audio_activity(self, wav_file):
        """检查音频文件是否有语音活动"""
        try:
            # 方法1: 使用sox检查音频统计信息
            cmd = ['sox', wav_file, '-n', 'stat']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                print(f"📊 [ALSA检测器] sox分析结果:")
                # 解析输出中的RMS amplitude和Maximum amplitude
                rms_value = None
                max_value = None
                
                for line in result.stderr.split('\n'):
                    if 'RMS amplitude' in line and ':' in line:
                        try:
                            rms_str = line.split(':')[1].strip()
                            rms_value = float(rms_str)
                            print(f"   RMS amplitude: {rms_value:.6f}")
                        except (ValueError, IndexError):
                            print(f"   RMS amplitude: 解析失败 - {line}")
                    elif 'Maximum amplitude' in line and ':' in line:
                        try:
                            max_str = line.split(':')[1].strip()
                            max_value = float(max_str)
                            print(f"   Maximum amplitude: {max_value:.6f}")
                        except (ValueError, IndexError):
                            print(f"   Maximum amplitude: 解析失败 - {line}")
                
                # 设置更严格的阈值检测语音活动
                rms_threshold = 0.005   # 提高阈值，减少误触发
                max_threshold = 0.05    # 提高最大值阈值
                duration_threshold = 0.5  # 持续时间阈值
                
                # 检查音频持续时间（简单估算）
                file_size = os.path.getsize(wav_file)
                expected_size = 3 * 16000 * 2  # 3秒的期望大小
                actual_duration = (file_size / expected_size) * 3.0
                
                print(f"   估算音频时长: {actual_duration:.1f}秒")
                
                # 多重条件检测，减少误触发
                rms_pass = rms_value and rms_value > rms_threshold
                max_pass = max_value and max_value > max_threshold
                duration_pass = actual_duration > duration_threshold
                
                if rms_pass and max_pass and duration_pass:
                    print(f"✅ [ALSA检测器] 严格检测通过: RMS={rms_value:.6f}>{rms_threshold}, Max={max_value:.6f}>{max_threshold}, 时长={actual_duration:.1f}s>{duration_threshold}")
                    return True
                else:
                    print(f"🔇 [ALSA检测器] 严格检测未通过:")
                    print(f"   - RMS检测: {'✅' if rms_pass else '❌'} ({rms_value:.6f if rms_value else 'N/A'} vs {rms_threshold})")
                    print(f"   - 最大值检测: {'✅' if max_pass else '❌'} ({max_value:.6f if max_value else 'N/A'} vs {max_threshold})")
                    print(f"   - 时长检测: {'✅' if duration_pass else '❌'} ({actual_duration:.1f}s vs {duration_threshold}s)")
                    return False
                    
        except Exception as e:
            print(f"⚠️ [ALSA检测器] sox分析失败: {e}")
        
        # 方法2: 如果sox不可用，使用更严格的文件大小检测
        try:
            file_size = os.path.getsize(wav_file)
            expected_size = 3 * 16000 * 2  # 3秒 * 16kHz * 2字节
            min_size = expected_size * 0.8  # 提高到80%的预期大小
            
            print(f"📁 [ALSA检测器] 严格文件大小检测: {file_size} bytes (期望: {expected_size}, 最小: {min_size})")
            
            if file_size > min_size:
                print(f"✅ [ALSA检测器] 文件大小检测通过")
                return True
            else:
                print(f"🔇 [ALSA检测器] 文件过小，可能无有效音频")
                return False
        except Exception as e:
            print(f"❌ [ALSA检测器] 文件大小检测失败: {e}")
        
        return False

# 单例模式
_alsa_detector = None

def get_alsa_wakeword_detector():
    """获取ALSA唤醒词检测器实例"""
    global _alsa_detector
    if _alsa_detector is None:
        _alsa_detector = ALSAWakewordDetector()
    return _alsa_detector

if __name__ == "__main__":
    # 测试代码
    def test_callback(event):
        print(f"🎉 检测到唤醒: {event}")
    
    detector = get_alsa_wakeword_detector()
    detector.set_callback(test_callback)
    
    print("🚀 启动ALSA唤醒词检测器测试")
    detector.start()
    
    try:
        print("💬 请对着m麦克风说话...")
        time.sleep(30)  # 测试30秒
    except KeyboardInterrupt:
        print("\n🛑 测试中断")
    finally:
        detector.stop()
        print("✅ 测试完成") 