# -*- coding: utf-8 -*-
"""
阿里云语音识别模块
基于DashScope SDK实现语音识别功能
支持分步语音识别：科目识别和困惑点识别
使用麦克风实时流式识别，无需临时文件
"""

import os
import time
import logging
import threading
from typing import Dict, Optional, Tuple
from ALSA import playAudioFile, getSoundCardIndex, setSoundMixerCommand

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AliCloudVoiceRecognizer:
    """阿里云语音识别器"""
    
    def __init__(self):
        self.is_recording = False
        self.api_key = None
        self.setup_api_key()
    
    def setup_api_key(self):
        """设置API密钥，从环境变量获取"""
        self.api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.error("未设置DASHSCOPE_API_KEY环境变量，语音识别将无法正常工作")
    
    def play_subject_hint_audio(self):
        """播放科目提示音频"""
        try:
            if os.path.exists('kemu.wav'):
                logger.info("播放科目提示：请说出你要询问的科目")
                
                # 获取声卡索引
                card_index = getSoundCardIndex()
                if card_index:
                    # 设置音频混合器
                    setSoundMixerCommand(card_index)
                    # 播放音频文件
                    playAudioFile(card_index, 'kemu.wav')
                else:
                    logger.warning("未找到指定的声卡，尝试使用系统默认播放")
                    os.system('aplay kemu.wav &')
            else:
                logger.warning("未找到科目提示音频文件 kemu.wav")
        except Exception as e:
            logger.error(f"播放科目提示音频失败: {e}")
    
    def play_difficulty_hint_audio(self):
        """播放困惑点提示音频"""
        try:
            if os.path.exists('kunhuo.wav'):
                logger.info("播放困惑点提示：请说出你遇到的困惑")
            
            # 获取声卡索引
            card_index = getSoundCardIndex()
            if card_index:
                # 设置音频混合器
                setSoundMixerCommand(card_index)
                # 播放音频文件
                playAudioFile(card_index, 'kunhuo.wav')
            else:
                logger.warning("未找到指定的声卡，尝试使用系统默认播放")
                os.system('aplay kunhuo.wav &')
          
        except Exception as e:
            logger.error(f"播放困惑点提示音频失败: {e}")
    
    def recognize_with_microphone(self, max_duration: int = 5) -> Optional[str]:
        """直接使用麦克风进行实时语音识别"""
        try:
            if not self.api_key:
                logger.error("API密钥未设置，无法进行语音识别")
                return None
            
            # 尝试导入依赖
            try:
                import dashscope
                from dashscope.audio.asr import TranslationRecognizerChat, TranslationRecognizerCallback
                from dashscope.audio.asr import TranscriptionResult, TranslationResult
                import pyaudio
            except ImportError as e:
                logger.error(f"缺少依赖模块，请安装: pip install dashscope pyaudio")
                logger.error(f"导入错误: {e}")
                return None
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            logger.info(f"开始麦克风语音识别，最大时长 {max_duration} 秒...")
            
            # 语音识别回调类
            class MicrophoneCallback(TranslationRecognizerCallback):
                def __init__(self):
                    self.recognition_result = None
                    self.is_complete = False
                    self.error_message = None
                    self.mic = None
                    self.stream = None
                
                def on_open(self):
                    logger.info("语音识别连接已建立，开始录音...")
                    try:
                        self.mic = pyaudio.PyAudio()
                        self.stream = self.mic.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            frames_per_buffer=3200  # 100ms的音频数据
                        )
                        logger.info("麦克风初始化成功")
                    except Exception as e:
                        logger.error(f"麦克风初始化失败: {e}")
                        self.error_message = f"麦克风初始化失败: {e}"
                        self.is_complete = True
                
                def on_close(self):
                    logger.info("语音识别连接已关闭")
                    if self.stream:
                        try:
                            self.stream.stop_stream()
                            self.stream.close()
                        except:
                            pass
                    if self.mic:
                        try:
                            self.mic.terminate()
                        except:
                            pass
                    self.stream = None
                    self.mic = None
                
                def on_event(self, request_id, transcription_result: TranscriptionResult,
                           translation_result: TranslationResult, usage):
                    if transcription_result:
                        if transcription_result.is_sentence_end:
                            self.recognition_result = transcription_result.text
                            logger.info(f"识别到完整句子: {self.recognition_result}")
                        else:
                            # 中间结果
                            logger.info(f"识别中间结果: {transcription_result.text}")
                
                def on_complete(self):
                    self.is_complete = True
                    logger.info("语音识别完成")
                
                def on_error(self, result):
                    self.error_message = str(result)
                    self.is_complete = True
                    logger.error(f"语音识别错误: {result}")
            
            # 创建回调对象
            callback = MicrophoneCallback()
            
            # 创建语音识别器
            recognizer = TranslationRecognizerChat(
                model="gummy-chat-v1",
                format="pcm",
                sample_rate=16000,
                transcription_enabled=True,
                translation_enabled=False,
                callback=callback
            )
            
            # 开始识别
            recognizer.start()
            
            # 等待麦克风初始化
            time.sleep(0.5)
            
            if callback.error_message:
                return None
            
            # 开始录音并发送音频数据
            start_time = time.time()
            logger.info("请开始说话...")
            
            while callback.stream and not callback.is_complete:
                try:
                    # 检查是否超时
                    if time.time() - start_time > max_duration:
                        logger.info("达到最大录音时长，停止录音")
                        break
                    
                    # 读取音频数据
                    data = callback.stream.read(3200, exception_on_overflow=False)
                    
                    # 发送音频数据
                    if not recognizer.send_audio_frame(data):
                        logger.info("检测到句子结束，停止录音")
                        break
                        
                except Exception as e:
                    logger.error(f"录音过程出错: {e}")
                    break
            
            # 停止识别
            recognizer.stop()
            
            # 等待识别完成
            timeout = 5  # 5秒超时
            wait_start = time.time()
            while not callback.is_complete and (time.time() - wait_start) < timeout:
                time.sleep(0.1)
            
            if callback.error_message:
                logger.error(f"语音识别失败: {callback.error_message}")
                return None
            
            if callback.recognition_result:
                logger.info(f"语音识别成功: {callback.recognition_result}")
                return callback.recognition_result.strip()
            else:
                logger.warning("未获得识别结果")
                return None
                
        except Exception as e:
            logger.error(f"语音识别过程出错: {e}")
            return None
    

    
    def recognize_subject(self, duration: int = 5) -> Optional[str]:
        """识别科目 - 使用switchrole的语音转文字功能"""
        try:
            logger.info("开始科目识别 - 使用switchrole技术")
            
            # 使用语音识别适配器
            from voice_recognition_adapter import recognize_subject_with_switchrole
            
            subject = recognize_subject_with_switchrole(timeout=duration)
            
            if subject:
                logger.info(f"科目识别结果: {subject}")
                return subject
            else:
                logger.error("科目识别失败")
                return None
                
        except Exception as e:
            logger.error(f"科目识别流程失败: {e}")
            return None
    
    def recognize_difficulty(self, duration: int = 5) -> Optional[str]:
        """识别困惑点 - 使用switchrole的语音转文字功能"""
        try:
            logger.info("开始困惑点识别 - 使用switchrole技术")
            
            # 使用语音识别适配器
            from voice_recognition_adapter import recognize_difficulty_with_switchrole
            
            difficulty = recognize_difficulty_with_switchrole(timeout=duration)
            
            if difficulty:
                logger.info(f"困惑点识别结果: {difficulty}")
                return difficulty.strip()
            else:
                logger.error("困惑点识别失败")
                return None
                
        except Exception as e:
            logger.error(f"困惑点识别流程失败: {e}")
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
    
    def stop_recording(self):
        """停止录音 - 现在使用流式识别，此方法保留以兼容现有接口"""
        self.is_recording = False
        logger.info("停止录音请求（流式识别模式下自动管理）")


# 测试函数
if __name__ == "__main__":
    recognizer = AliCloudVoiceRecognizer()
    
    print("=== 阿里云DashScope语音识别测试 ===")
    print("确保已安装依赖: pip install dashscope pyaudio")
    print("API Key已设置为: sk-93bb40ac8c6b45c1b9bd295902ed4d2f")
    
    print("\n开始科目识别测试...")
    subject = recognizer.recognize_subject(duration=5)
    print(f"科目识别结果：{subject}")
    
    if subject:
        print("\n开始困惑点识别测试...")
        difficulty = recognizer.recognize_difficulty(duration=5)
        print(f"困惑点识别结果：{difficulty}")
    else:
        print("科目识别失败，跳过困惑点识别测试") 