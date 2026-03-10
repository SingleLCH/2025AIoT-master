#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别适配器
用于家庭问答功能，使用switchrole的语音转文字能力
避免与语音助手的线程冲突
"""

import os
import sys
import time
import logging
import threading
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

# 配置日志
logger = logging.getLogger(__name__)

class VoiceRecognitionAdapter(QObject):
    """语音识别适配器类"""
    
    # 信号定义
    recognition_started = pyqtSignal()
    recognition_completed = pyqtSignal(str)  # 识别完成，返回文本
    recognition_failed = pyqtSignal(str)  # 识别失败，返回错误信息
    
    def __init__(self):
        super().__init__()
        self.is_initialized = False
        self.audio_manager = None
        self.recognition_mutex = QMutex()  # 防止并发调用
        
        # 线程B实例（用于语音转文字）
        self.thread_b_instance = None
        
        logger.info("语音识别适配器初始化")
    
    def initialize(self) -> bool:
        """初始化语音识别适配器"""
        try:
            if self.is_initialized:
                return True
            
            logger.info("初始化语音识别适配器...")
            
            # 添加switchrole目录到路径
            switchrole_path = os.path.join(os.getcwd(), 'switchrole')
            if switchrole_path not in sys.path:
                sys.path.insert(0, switchrole_path)
            
            # 加载switchrole环境变量配置
            env_file_path = os.path.join(switchrole_path, 'xiaoxin.env')
            if os.path.exists(env_file_path):
                logger.info(f"🔧 加载环境配置文件: {env_file_path}")
                self._load_env_file(env_file_path)
            else:
                logger.warning(f"⚠️ 环境配置文件不存在: {env_file_path}")
            
            # 导入switchrole模块
            try:
                from switchrole.xiaoxin2_zh  import AudioDeviceManager, ThreadB
                self.AudioDeviceManager = AudioDeviceManager
                self.ThreadB = ThreadB
                logger.info("✅ switchrole模块导入成功")
            except ImportError as e:
                logger.error(f"❌ 导入switchrole模块失败: {e}")
                return False
            
            # 初始化音频设备管理器
            self.audio_manager = self.AudioDeviceManager()
            if not self.audio_manager.init_devices():
                logger.error("❌ 音频设备初始化失败")
                return False
            
            # 创建ThreadB实例（仅用于语音识别，不启动线程）
            self.thread_b_instance = self.ThreadB(self.audio_manager)
            
            logger.info("✅ 语音识别适配器初始化成功")
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ 语音识别适配器初始化失败: {e}")
            return False
    
    def _load_env_file(self, env_file_path: str):
        """加载环境变量配置文件"""
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if line.startswith('#') or not line or '=' not in line:
                        continue
                    
                    # 解析键值对
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 设置环境变量
                    os.environ[key] = value
                    logger.debug(f"设置环境变量: {key}")
            
            logger.info(f"✅ 环境变量配置加载成功")
                    
        except Exception as e:
            logger.error(f"❌ 加载环境变量配置失败: {e}")
    
    def recognize_speech_with_hint(self, hint_audio_file: str, timeout: int = 5) -> Optional[str]:
        """
        播放提示音后进行语音识别
        
        Args:
            hint_audio_file: 提示音文件路径（如kemu.wav、kunhuo.wav）
            timeout: 识别超时时间（秒）
            
        Returns:
            识别到的文本，失败返回None
        """
        
        # 使用互斥锁防止并发调用
        locker = QMutexLocker(self.recognition_mutex)
        
        try:
            if not self.is_initialized:
                if not self.initialize():
                    self.recognition_failed.emit("语音识别适配器初始化失败")
                    return None
            
            logger.info(f"🎤 开始语音识别 - 提示音: {hint_audio_file}")
            self.recognition_started.emit()
            
            # 播放提示音
            if not self._play_hint_audio(hint_audio_file):
                error_msg = f"播放提示音失败: {hint_audio_file}"
                logger.error(error_msg)
                self.recognition_failed.emit(error_msg)
                return None
            
            # 等待提示音播放完成
            time.sleep(2)
            
            # 进行语音识别
            result = self._perform_speech_recognition(timeout)
            
            if result:
                logger.info(f"✅ 语音识别成功: {result}")
                self.recognition_completed.emit(result)
                return result
            else:
                error_msg = "语音识别失败，未检测到有效语音"
                logger.warning(error_msg)
                self.recognition_failed.emit(error_msg)
                return None
                
        except Exception as e:
            error_msg = f"语音识别过程异常: {e}"
            logger.error(error_msg)
            self.recognition_failed.emit(error_msg)
            return None
    
    def recognize_subject(self, timeout: int = 5) -> Optional[str]:
        """
        识别科目（播放kemu.wav提示音）
        
        Args:
            timeout: 识别超时时间（秒）
            
        Returns:
            识别到的科目，失败返回None
        """
        result = self.recognize_speech_with_hint("kemu.wav", timeout)
        if result:
            # 解析科目
            parsed_subject = self._parse_subject_from_text(result)
            logger.info(f"📚 科目识别结果: {result} -> {parsed_subject}")
            return parsed_subject
        return None
    
    def recognize_difficulty(self, timeout: int = 5) -> Optional[str]:
        """
        识别困惑点（播放kunhuo.wav提示音）
        
        Args:
            timeout: 识别超时时间（秒）
            
        Returns:
            识别到的困惑点，失败返回None
        """
        result = self.recognize_speech_with_hint("kunhuo.wav", timeout)
        if result:
            logger.info(f"🤔 困惑点识别结果: {result}")
            return result.strip()
        return None
    
    def _play_hint_audio(self, hint_audio_file: str) -> bool:
        """播放提示音"""
        try:
            if not os.path.exists(hint_audio_file):
                logger.error(f"提示音文件不存在: {hint_audio_file}")
                return False
            
            logger.info(f"🎵 播放提示音: {hint_audio_file}")
            
            # 使用ALSA播放提示音
            from ALSA import playAudioFile, getSoundCardIndex, setSoundMixerCommand
            
            card_index = getSoundCardIndex()
            if card_index:
                setSoundMixerCommand(card_index)
                playAudioFile(card_index, hint_audio_file)
                logger.info(f"✅ 提示音播放完成: {hint_audio_file}")
                return True
            else:
                logger.warning("未找到声卡，尝试系统默认播放")
                os.system(f'aplay {hint_audio_file} &')
                return True
                
        except Exception as e:
            logger.error(f"播放提示音失败: {e}")
            return False
    
    def _perform_speech_recognition(self, timeout: int) -> Optional[str]:
        """执行语音识别"""
        try:
            if not self.thread_b_instance:
                logger.error("ThreadB实例未初始化")
                return None
            
            logger.info(f"🎤 开始语音识别，超时时间: {timeout}秒")
            
            # 临时调整音频管理器的超时时间
            original_timeout = getattr(self.thread_b_instance, 'timeout', 8.0)
            
            # 使用ThreadB的listen_user_input方法
            # 创建一个临时的自定义listen方法
            def custom_listen_with_timeout():
                """自定义的带超时的监听方法"""
                start_time = time.time()
                max_retries = 3
                retry_count = 0
                
                while time.time() - start_time < timeout:
                    try:
                        logger.info(f"🎤 尝试语音识别 (第{retry_count + 1}次)...")
                        
                        # 使用Azure PulseAudio语音识别器
                        result = self.audio_manager.azure_recognizer.recognize_once()
                        
                        if hasattr(result, 'reason'):
                            import azure.cognitiveservices.speech as speechsdk
                            
                            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                                user_input = result.text.strip()
                                if user_input:
                                    logger.info(f"🗣️ 识别成功: '{user_input}'")
                                    return user_input
                                else:
                                    logger.info("识别到空内容，继续监听...")
                            elif result.reason == speechsdk.ResultReason.NoMatch:
                                logger.info("未匹配到语音，继续监听...")
                                retry_count += 1
                                if retry_count >= max_retries:
                                    logger.warning(f"已重试{max_retries}次，仍无匹配")
                                    retry_count = 0
                            elif result.reason == speechsdk.ResultReason.Canceled:
                                cancellation = result.cancellation_details
                                logger.warning(f"识别被取消: {cancellation.reason}")
                                if cancellation.reason == speechsdk.CancellationReason.Error:
                                    logger.error(f"识别错误: {cancellation.error_details}")
                            else:
                                logger.warning(f"未知识别结果: {result.reason}")
                        
                        # 短暂休息后继续
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.warning(f"语音识别异常: {e}")
                        retry_count += 1
                        time.sleep(0.5)
                
                logger.warning(f"语音识别超时({timeout}秒)，未检测到有效输入")
                return None
            
            # 执行自定义的语音识别
            return custom_listen_with_timeout()
            
        except Exception as e:
            logger.error(f"语音识别执行失败: {e}")
            return None
    
    def _parse_subject_from_text(self, text: str) -> str:
        """从识别文本中解析科目"""
        try:
            logger.info(f"解析科目文本: {text}")
            
            # 检测常见科目关键词
            subjects_map = {
                '数学': ['数学', '算术', '代数', '几何', '微积分', '函数', '方程', '三角', '统计'],
                '语文': ['语文', '语言', '文字', '阅读', '作文', '诗词', '古文', '文学', '诗歌'],
                '英语': ['英语', '英文', '单词', '语法', '口语', '听力', '阅读', '写作'],
                '物理': ['物理', '力学', '电学', '光学', '热学', '声学', '机械', '电路'],
                '化学': ['化学', '元素', '分子', '反应', '实验', '化合', '有机', '无机'],
                '生物': ['生物', '细胞', '遗传', '生态', '解剖', '植物', '动物', '基因'],
                '历史': ['历史', '古代', '近代', '朝代', '战争', '文明', '年代'],
                '地理': ['地理', '地图', '气候', '地形', '国家', '城市', '山脉', '河流'],
                '政治': ['政治', '法律', '制度', '权利', '国家', '政府', '法规'],
                '科学': ['科学', '实验', '研究', '观察', '科技', '技术']
            }
            
            # 匹配科目
            for subject_name, keywords in subjects_map.items():
                for keyword in keywords:
                    if keyword in text:
                        logger.info(f"匹配到科目: {subject_name}")
                        return subject_name
            
            # 如果没有匹配到，返回原文本作为科目
            logger.warning(f"未匹配到已知科目，使用原文本: {text.strip()}")
            return text.strip() if text.strip() else "未知科目"
            
        except Exception as e:
            logger.error(f"解析科目失败: {e}")
            return "未知科目"


# 全局语音识别适配器实例
_voice_adapter_instance = None

def get_voice_recognition_adapter() -> VoiceRecognitionAdapter:
    """获取全局语音识别适配器实例"""
    global _voice_adapter_instance
    if _voice_adapter_instance is None:
        _voice_adapter_instance = VoiceRecognitionAdapter()
    return _voice_adapter_instance

def recognize_subject_with_switchrole(timeout: int = 5) -> Optional[str]:
    """
    使用switchrole技术识别科目
    
    Args:
        timeout: 识别超时时间（秒）
        
    Returns:
        识别到的科目，失败返回None
    """
    adapter = get_voice_recognition_adapter()
    return adapter.recognize_subject(timeout)

def recognize_difficulty_with_switchrole(timeout: int = 5) -> Optional[str]:
    """
    使用switchrole技术识别困惑点
    
    Args:
        timeout: 识别超时时间（秒）
        
    Returns:
        识别到的困惑点，失败返回None
    """
    adapter = get_voice_recognition_adapter()
    return adapter.recognize_difficulty(timeout) 