#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ALSA语音识别模块

功能：
- 使用ALSA层的arecord进行麦克风采集
- 与Azure语音识别服务集成
- 实时语音流处理
"""

import os
import subprocess
import tempfile
import threading
import time
from typing import Optional, Callable
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("xiaoxin.env")

class ALSASpeechRecognizer:
    """ALSA语音识别器"""
    
    def __init__(self, card_name="lahainayupikiot", use_usb_mic=True):
        """
        初始化ALSA语音识别器
        
        Args:
            card_name: 声卡名称（用于混音器配置）
            use_usb_mic: 是否使用USB麦克风（hw:0,0）进行录音
        """
        self.card_name = card_name
        self.card_index = None
        self.use_usb_mic = use_usb_mic
        self.mic_device = "hw:0,0" if use_usb_mic else None
        
        # Azure语音服务配置
        self.speech_key = os.environ["Azure_speech_key"]
        self.service_region = os.environ["Azure_speech_region"]
        
        # 录音参数
        self.sample_rate = 48000  # 采样率
        self.channels = 2  # 双声道
        self.format = "S16_LE"  # 音频格式
        
        # 录音控制
        self.is_recording = False
        self.recording_process = None
        self.recording_thread = None
        
        print(f"🎤 初始化ALSA语音识别器")
        print(f"   声卡: {self.card_name}")
        print(f"   麦克风: {'USB麦克风(hw:0,0)' if use_usb_mic else 'lahainayupikiot麦克风'}")
        
    def get_sound_card_index(self):
        """获取指定声卡的索引"""
        try:
            ret = subprocess.run(["cat", "/proc/asound/cards"], 
                               check=True, stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, text=True)
            output = ret.stdout
            lines = output.splitlines()
            for line in lines:
                if self.card_name in line:
                    cindex = line.split()[0]
                    print(f"✅ 找到声卡 '{self.card_name}'，索引: {cindex}")
                    return cindex
            print(f"❌ 未找到声卡 '{self.card_name}'")
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ 获取声卡信息失败: {e.stderr}")
            return None
    
    def setup_mixer_commands(self, index):
        """设置声卡混音器命令（麦克风输入路径）"""
        commands = [
            # 输入路径设置
            ["amixer", "-c", str(index), "cset", "numid=128,iface=MIXER,name='MultiMedia1 Mixer TX_CDC_DMA_TX_3'", "1"],
            ["amixer", "-c", str(index), "cset", "numid=127,iface=MIXER,name='TX_CDC_DMA_TX_3 Channels'", "Two"],
            ["amixer", "-c", str(index), "cset", "numid=126,iface=MIXER,name='TX DEC0 MUX'", "SWR_MIC"],
            ["amixer", "-c", str(index), "cset", "numid=125,iface=MIXER,name='TX SMIC MUX0'", "ADC1"],
            ["amixer", "-c", str(index), "cset", "numid=124,iface=MIXER,name='TX_AIF1_CAP Mixer DEC0'", "1"],
            ["amixer", "-c", str(index), "cset", "numid=123,iface=MIXER,name='TX_AIF1_CAP Mixer DEC1'", "1"],
        ]
        
        print(f"🔧 配置麦克风输入路径...")
        for cmd in commands:
            try:
                result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, text=True)
                print(f"   ✅ {' '.join(cmd)}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ {' '.join(cmd)} 失败: {e.stderr}")
    
    def initialize(self):
        """初始化声卡设备"""
        # 获取声卡索引
        self.card_index = self.get_sound_card_index()
        if self.card_index is None:
            print("❌ 声卡初始化失败")
            return False
        
        # 设置混音器
        self.setup_mixer_commands(self.card_index)
        
        print("✅ ALSA语音识别器初始化完成")
        return True
    
    def record_audio_to_file(self, duration_seconds: int, output_file: str) -> bool:
        """
        录制音频到文件
        
        Args:
            duration_seconds: 录制时长（秒）
            output_file: 输出文件路径
            
        Returns:
            bool: 录制是否成功
        """
        # USB麦克风模式不需要card_index初始化
        if not self.use_usb_mic and not self.card_index:
            if not self.initialize():
                return False
        
        # 构建arecord命令
        mic_device = self.mic_device if self.use_usb_mic else f'hw:{self.card_index},0'
        arecord_cmd = [
            'arecord',
            '-t', 'wav',
            '-r', str(self.sample_rate),
            '-f', self.format,
            '-c', str(self.channels),
            '-D', mic_device,
            '-d', str(duration_seconds),
            output_file
        ]
        
        try:
            print(f"🎤 开始录音 ({duration_seconds}秒)...")
            print(f"🔧 录音命令: {' '.join(arecord_cmd)}")
            result = subprocess.run(arecord_cmd, check=True, 
                                  capture_output=True, text=True)
            print(f"✅ 录音完成: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 录音失败: {e.stderr}")
            print(f"🔧 失败的录音命令: {' '.join(arecord_cmd)}")
            return False
    
    def start_streaming_recording(self, callback: Callable[[bytes], None]) -> bool:
        """
        开始流式录音
        
        Args:
            callback: 音频数据回调函数
            
        Returns:
            bool: 启动是否成功
        """
        if self.is_recording:
            print("⚠️ 录音已在进行中")
            return False
        
        if not self.card_index:
            if not self.initialize():
                return False
        
        # 构建arecord命令（输出到stdout）
        mic_device = self.mic_device if self.use_usb_mic else f'hw:{self.card_index},0'
        arecord_cmd = [
            'arecord',
            '-t', 'raw',
            '-r', str(self.sample_rate),
            '-f', self.format,
            '-c', str(self.channels),
            '-D', mic_device
        ]
        
        try:
            print(f"🎤 开始流式录音...")
            self.recording_process = subprocess.Popen(
                arecord_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_recording = True
            
            # 启动读取线程
            self.recording_thread = threading.Thread(
                target=self._streaming_reader,
                args=(callback,),
                daemon=True
            )
            self.recording_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ 启动流式录音失败: {e}")
            return False
    
    def _streaming_reader(self, callback: Callable[[bytes], None]):
        """流式录音读取线程"""
        try:
            chunk_size = 1024  # 每次读取的字节数
            while self.is_recording and self.recording_process:
                data = self.recording_process.stdout.read(chunk_size)
                if data:
                    callback(data)
                else:
                    break
        except Exception as e:
            print(f"❌ 流式录音读取异常: {e}")
        finally:
            print("🎤 流式录音读取线程结束")
    
    def stop_streaming_recording(self):
        """停止流式录音"""
        if not self.is_recording:
            return
        
        print("🛑 停止流式录音...")
        self.is_recording = False
        
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait()
            self.recording_process = None
        
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
            self.recording_thread = None
        
        print("✅ 流式录音已停止")
    
    def recognize_speech_once(self, timeout: float = 5.0) -> Optional[str]:
        """
        单次语音识别
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            str: 识别结果，失败返回None
        """
        if not self.card_index:
            if not self.initialize():
                return None
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # 录制音频
            if not self.record_audio_to_file(int(timeout), temp_filename):
                return None
            
            # 使用Azure语音识别
            return self._recognize_audio_file(temp_filename)
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_filename)
            except:
                pass
    
    def _recognize_audio_file(self, audio_file: str) -> Optional[str]:
        """使用Azure语音识别识别音频文件"""
        try:
            # 创建语音配置
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region
            )
            speech_config.speech_recognition_language = "zh-CN"
            
            # 创建音频配置
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
            
            # 创建识别器
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # 执行识别
            print("🔍 开始语音识别...")
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"✅ 识别成功: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("⚠️ 未识别到有效语音")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"❌ 识别被取消: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    print(f"   错误详情: {cancellation.error_details}")
                return None
            else:
                print(f"❓ 未知识别结果: {result.reason}")
                return None
                
        except Exception as e:
            print(f"❌ 语音识别异常: {e}")
            return None
    
    def recognize_speech_continuous(self, callback: Callable[[str], None], 
                                   stop_event: threading.Event):
        """
        持续语音识别
        
        Args:
            callback: 识别结果回调函数
            stop_event: 停止事件
        """
        try:
            # 创建语音配置
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region
            )
            speech_config.speech_recognition_language = "zh-CN"
            
            # 创建音频配置（使用默认麦克风，会自动使用ALSA）
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            
            # 创建识别器
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # 设置回调
            def recognized(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    callback(evt.result.text)
            
            speech_recognizer.recognized.connect(recognized)
            
            # 开始持续识别
            print("🎤 开始持续语音识别...")
            speech_recognizer.start_continuous_recognition()
            
            # 等待停止事件
            stop_event.wait()
            
            # 停止识别
            speech_recognizer.stop_continuous_recognition()
            print("🛑 持续语音识别已停止")
            
        except Exception as e:
            print(f"❌ 持续语音识别异常: {e}")

# 全局实例
_alsa_recognizer = None

def get_alsa_recognizer():
    """获取ALSA语音识别器单例"""
    global _alsa_recognizer
    if _alsa_recognizer is None:
        _alsa_recognizer = ALSASpeechRecognizer()
    return _alsa_recognizer

def recognize_speech_once_alsa(timeout: float = 5.0) -> Optional[str]:
    """单次语音识别（ALSA）"""
    recognizer = get_alsa_recognizer()
    return recognizer.recognize_speech_once(timeout)

if __name__ == "__main__":
    # 测试ALSA语音识别
    recognizer = ALSASpeechRecognizer()
    
    if recognizer.initialize():
        # 测试单次识别
        print("请说话...")
        result = recognizer.recognize_speech_once(5)
        if result:
            print(f"识别结果: {result}")
        else:
            print("识别失败")
    else:
        print("初始化失败") 