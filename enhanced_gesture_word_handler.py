#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版指尖单词处理器 - 支持TTS保存、多轮练习和语音评测
"""

import os
import sys
import time
import logging
import requests
import datetime
import hashlib
import base64
import hmac
import json
import uuid
import sounddevice as sd
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedGestureWordHandler(QObject):
    """增强版指尖单词处理器"""
    
    # 信号定义
    word_recognized = pyqtSignal(str)  # 单词识别完成信号
    tts_started = pyqtSignal(str)  # TTS开始信号
    tts_completed = pyqtSignal()  # TTS完成信号
    recording_started = pyqtSignal()  # 录音开始信号
    recording_completed = pyqtSignal(str)  # 录音完成信号 (录音文件路径)
    score_updated = pyqtSignal(float, int)  # 分数更新信号 (分数, 轮次)
    process_completed = pyqtSignal(str, bool)  # 流程完成信号 (单词, 是否成功)
    error_occurred = pyqtSignal(str)  # 错误信号
    status_updated = pyqtSignal(str, str)  # 状态更新信号 (消息, 颜色)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 讯飞API配置 - 从环境变量获取
        self.APPID = os.environ.get("XFYUN_APP_ID", "")
        self.Secret = os.environ.get("XFYUN_API_SECRET", "")
        self.APIKey = os.environ.get("XFYUN_API_KEY", "")
        self.Host = "tyocr.xfyun.cn"
        self.RequestUri = "/v2/ocr"
        self.url = "https://" + self.Host + self.RequestUri
        self.HttpMethod = "POST"
        self.Algorithm = "hmac-sha256"
        self.HttpProto = "HTTP/1.1"
        
        # 腾讯云语音评测配置 - 从环境变量获取
        self.TENCENT_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
        self.TENCENT_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
        self.TENCENT_REGION = os.environ.get("TENCENT_REGION", "ap-shanghai")
        
        # 业务参数
        self.BusinessArgs = {
            "ent": "fingerocr",
            "mode": "finger+ocr",
            "method": "dynamic",
            "resize_w": 1088,
            "resize_h": 1632,
        }
        
        # 文件夹配置
        self.word_audio_folder = "word_audio"  # 单词音频文件夹
        self.recording_folder = "word_recordings"  # 录音文件夹
        self._ensure_folders()
        
        # TTS处理器
        self.tts_handler = None
        self.init_tts()
        
        # MQTT处理器
        self.mqtt_handler = None
        self.init_mqtt()
        
        # 状态
        self.is_processing = False
        self.current_word = ""
        self.current_round = 0  # 当前轮次 (1-3)
        self.max_rounds = 3
        self.target_score = 70.0
        self.current_score = 0.0
        self.recording_duration = 5  # 录音时长
        
        logger.info("增强版指尖单词处理器初始化完成")
    
    def _ensure_folders(self):
        """确保必要的文件夹存在"""
        folders = [self.word_audio_folder, self.recording_folder]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logger.info(f"创建文件夹: {folder}")
    
    def init_tts(self):
        """初始化TTS处理器"""
        try:
            # TTS功能总是可用，即使API key未设置也要尝试
            from switchrole.alsa_cosyvoice_tts import text_to_speech_alsa
            self.tts_function = text_to_speech_alsa
            self.tts_handler = True  # 标记TTS可用
            logger.info("TTS处理器初始化成功")
        except Exception as e:
            logger.error(f"TTS处理器初始化失败: {e}")
            self.tts_handler = None
            self.tts_function = None
    
    def init_mqtt(self):
        """初始化MQTT处理器"""
        try:
            from mqtt_handler import MQTTHandler
            self.mqtt_handler = MQTTHandler()
            # 启动MQTT连接
            self.mqtt_handler.start()
            logger.info("MQTT处理器初始化并启动成功")
        except Exception as e:
            logger.error(f"MQTT处理器初始化失败: {e}")
            self.mqtt_handler = None
    
    def httpdate(self, dt):
        """生成HTTP日期格式"""
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                        dt.year, dt.hour, dt.minute, dt.second)
    
    def hashlib_256(self, res):
        """生成SHA256哈希"""
        m = hashlib.sha256(bytes(res.encode(encoding='utf-8'))).digest()
        result = "SHA-256=" + base64.b64encode(m).decode(encoding='utf-8')
        return result
    
    def generateSignature(self, digest, date):
        """生成签名"""
        signatureStr = "host: " + self.Host + "\n"
        signatureStr += "date: " + date + "\n"
        signatureStr += self.HttpMethod + " " + self.RequestUri + " " + self.HttpProto + "\n"
        signatureStr += "digest: " + digest
        signature = hmac.new(bytes(self.Secret.encode(encoding='utf-8')),
                             bytes(signatureStr.encode(encoding='utf-8')),
                             digestmod=hashlib.sha256).digest()
        result = base64.b64encode(signature)
        return result.decode(encoding='utf-8')
    
    def init_header(self, data, date):
        """初始化请求头"""
        digest = self.hashlib_256(data)
        sign = self.generateSignature(digest, date)
        authHeader = 'api_key="%s", algorithm="%s", headers="host date request-line digest", signature="%s"' \
                     % (self.APIKey, self.Algorithm, sign)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Method": "POST",
            "Host": self.Host,
            "Date": date,
            "Digest": digest,
            "Authorization": authHeader
        }
        return headers
    
    def imgRead(self, path):
        """读取图片文件"""
        with open(path, 'rb') as fo:
            return fo.read()
    
    def get_body(self, image_path):
        """构建请求体"""
        audioData = self.imgRead(image_path)
        content = base64.b64encode(audioData).decode(encoding='utf-8')
        postdata = {
            "common": {"app_id": self.APPID},
            "business": self.BusinessArgs,
            "data": {
                "image": content,
            }
        }
        body = json.dumps(postdata)
        return body
    
    def find_nearest_word(self, respData):
        """查找手指最近的单词"""
        try:
            finger_x = respData["data"]["finger_pos"]["pos_x"]
            finger_y = respData["data"]["finger_pos"]["pos_y"]
            words = respData["data"]["finger_ocr"]["word"]["list"]
            
            min_dist = float('inf')
            closest_word = None
            
            for word in words:
                coords = word.get("coord", [])
                if len(coords) != 4:
                    continue
                center_x = sum(p["x"] for p in coords) / 4
                center_y = sum(p["y"] for p in coords) / 4
                dist = ((center_x - finger_x) ** 2 + (center_y - finger_y) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_word = word.get("content", "")
            
            return closest_word
        except Exception as e:
            logger.error(f"查找最近单词失败: {e}")
            return None
    
    def recognize_word_from_image(self, image_path: str):
        """从图片识别指尖单词并开始完整流程"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        if not os.path.exists(image_path):
            self.error_occurred.emit(f"图片文件不存在: {image_path}")
            return
        
        self.is_processing = True
        self.current_round = 0
        self.status_updated.emit("正在识别指尖单词...", "#f39c12")
        
        try:
            # 生成时间戳
            curTime_utc = datetime.datetime.utcnow()
            date = self.httpdate(curTime_utc)
            
            # 构建请求
            body = self.get_body(image_path)
            headers = self.init_header(body, date)
            
            # 发送请求
            logger.info("发送指尖单词识别请求...")
            response = requests.post(self.url, data=body, headers=headers, timeout=10)
            
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}，错误: {response.text}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                self.is_processing = False
                return
            
            # 解析响应
            respData = json.loads(response.text)
            code = str(respData.get("code", "0"))
            
            if code != '0':
                error_msg = f"API返回错误码: {code}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                self.is_processing = False
                return
            
            # 提取识别的单词
            word_list = respData.get("data", {}).get("finger_ocr", {}).get("word", {}).get("list", [])
            
            if not word_list:
                self.error_occurred.emit("未识别出任何单词")
                self.is_processing = False
                return
            
            # 获取第一个单词（或最近的单词）
            recognized_word = word_list[0].get("content", "").strip()
            
            # 尝试查找手指最近的单词
            nearest_word = self.find_nearest_word(respData)
            if nearest_word:
                recognized_word = nearest_word.strip()
            
            if recognized_word:
                logger.info(f"识别到单词: {recognized_word}")
                self.current_word = recognized_word
                self.word_recognized.emit(recognized_word)
                self.status_updated.emit(f"识别成功: {recognized_word}", "#27ae60")
                
                # 开始完整的学习流程
                self._start_learning_process()
            else:
                self.error_occurred.emit("识别的单词为空")
                self.is_processing = False
                
        except Exception as e:
            error_msg = f"识别过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_processing = False

    def _start_learning_process(self):
        """开始学习流程"""
        logger.info(f"开始单词学习流程: {self.current_word}")

        # 1. 生成并保存TTS音频
        self._generate_and_save_tts()

        # 2. 开始第一轮练习
        self.current_round = 1
        self._start_practice_round()

    def _generate_and_save_tts(self):
        """生成并保存TTS音频文件"""
        try:
            word_audio_path = os.path.join(self.word_audio_folder, f"{self.current_word}.wav")

            if os.path.exists(word_audio_path):
                logger.info(f"TTS音频文件已存在: {word_audio_path}")
                return

            logger.info(f"生成TTS音频: {self.current_word}")
            self.status_updated.emit("正在生成语音文件...", "#3498db")

            # 使用longxiaochun声音生成TTS
            success = self._generate_tts_with_longxiaochun(self.current_word, word_audio_path)

            if success:
                logger.info(f"TTS音频生成成功: {word_audio_path}")
            else:
                logger.warning("TTS音频生成失败，将使用在线TTS")

        except Exception as e:
            logger.error(f"生成TTS音频失败: {e}")

    def _generate_tts_with_longxiaochun(self, text: str, output_path: str) -> bool:
        """使用longxiaochun声音生成TTS并保存为WAV文件"""
        try:
            import os
            import tempfile
            import subprocess
            from switchrole.alsa_cosyvoice_tts import ALSACosyVoiceTTS

            # 检查API key
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                logger.error("DASHSCOPE_API_KEY未设置")
                return False

            # 创建专门的TTS实例，使用longxiaochun声音
            tts = ALSACosyVoiceTTS()
            # 设置声音为longxiaochun
            original_voice = tts.voice
            tts.voice = "longxiaochun"

            logger.info(f"使用longxiaochun声音生成TTS并保存: {text} -> {output_path}")

            # 使用阿里云TTS生成音频数据
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer

            # 设置API key
            dashscope.api_key = api_key

            synthesizer = SpeechSynthesizer(
                model="cosyvoice-v1",
                voice="longxiaochun"
            )

            # 生成音频数据
            audio_data = synthesizer.call(text)

            if audio_data and isinstance(audio_data, bytes):
                # 保存音频数据到临时文件
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_mp3_path = temp_file.name

                # 使用ffmpeg转换为WAV格式
                try:
                    ffmpeg_cmd = [
                        'ffmpeg', '-i', temp_mp3_path,
                        '-ar', '16000',  # 采样率16kHz
                        '-ac', '1',      # 单声道
                        '-y',            # 覆盖输出文件
                        output_path
                    ]

                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        logger.info(f"TTS音频保存成功: {output_path}")
                        # 清理临时文件
                        os.unlink(temp_mp3_path)
                        return True
                    else:
                        logger.error(f"ffmpeg转换失败: {result.stderr}")
                        # 清理临时文件
                        os.unlink(temp_mp3_path)
                        return False

                except Exception as e:
                    logger.error(f"音频转换异常: {e}")
                    # 清理临时文件
                    if os.path.exists(temp_mp3_path):
                        os.unlink(temp_mp3_path)
                    return False
            else:
                logger.error("TTS生成失败，无音频数据")
                return False

        except Exception as e:
            logger.error(f"longxiaochun TTS异常: {e}")
            return False

    def _start_practice_round(self):
        """开始练习轮次"""
        logger.info(f"开始第{self.current_round}轮练习")
        self.status_updated.emit(f"第{self.current_round}轮练习开始", "#3498db")

        # 1. TTS播放三遍，每遍间隔1秒
        self._play_tts_three_times()

    def _play_tts_three_times(self):
        """在一个线程中播放三次单词音频（间隔1秒）然后播放1st.wav"""
        logger.info("开始在一个线程中播放三次单词音频+1st.wav")
        self.status_updated.emit("正在播放单词发音...", "#3498db")

        # 暂停语音助手一次，播放期间保持暂停状态
        logger.info("TTS播放前暂停语音助手...")
        self._pause_voice_assistant()

        try:
            # 获取单词音频路径
            word_audio_path = os.path.join(self.word_audio_folder, f"{self.current_word}.wav")
            
            # 确保音频文件存在
            if not os.path.exists(word_audio_path):
                logger.info(f"生成TTS音频文件: {self.current_word}")
                success = self._generate_tts_with_longxiaochun(self.current_word, word_audio_path)
                if not success or not os.path.exists(word_audio_path):
                    logger.error("TTS音频生成失败")
                    self._resume_voice_assistant()
                    self.error_occurred.emit("TTS音频生成失败")
                    return

            # 1. 连续播放三次单词音频，每次间隔1秒
            from switchrole.audio_player import play_audio_blocking
            import time
            
            for i in range(3):
                logger.info(f"播放第{i+1}次单词音频: {word_audio_path}")
                result = play_audio_blocking(word_audio_path)
                
                if not result:
                    logger.warning(f"第{i+1}次单词音频播放失败")
                
                # 如果不是最后一次，等待1秒
                if i < 2:
                    logger.info("等待1秒间隔...")
                    time.sleep(1)

            logger.info("三次单词音频播放完成")

            # 2. 等待1秒后播放对应轮次的提示音
            hint_files = {
                1: "1st.wav",
                2: "2nd.wav", 
                3: "3rd.wav"
            }
            hint_file = hint_files.get(self.current_round, "1st.wav")
            
            logger.info(f"等待1秒后播放{hint_file}...")
            time.sleep(1)
            
            if os.path.exists(hint_file):
                logger.info(f"播放第{self.current_round}轮提示音频: {hint_file}")
                result = play_audio_blocking(hint_file)
                if not result:
                    logger.warning(f"提示音频播放失败: {hint_file}")
            else:
                logger.warning(f"提示音频文件不存在: {hint_file}")

            logger.info("所有音频播放完成")

        except Exception as e:
            logger.error(f"音频播放异常: {e}")
            self.error_occurred.emit(f"音频播放异常: {e}")
        finally:
            # 恢复语音助手
            logger.info("TTS播放完成，恢复语音助手...")
            self._resume_voice_assistant()
            # 开始录音
            self._play_round_hint()

    # 已删除 _play_single_tts 方法，因为现在在 _play_tts_three_times 中统一处理

    def _tts_with_longxiaochun(self, word: str) -> bool:
        """使用longxiaochun声音进行TTS朗读"""
        try:
            # 检查是否已有保存的音频文件
            word_audio_path = os.path.join(self.word_audio_folder, f"{word}.wav")

            # 暂停语音助手以释放音频设备
            logger.info("TTS播放前暂停语音助手...")
            self._pause_voice_assistant()

            try:
                if os.path.exists(word_audio_path):
                    logger.info(f"播放已保存的TTS音频: {word_audio_path}")
                    # 使用ALSA播放WAV文件
                    from switchrole.audio_player import play_audio_blocking
                    result = play_audio_blocking(word_audio_path)
                else:
                    # 如果没有保存的文件，先生成再播放
                    logger.info(f"生成TTS音频文件: {word}")
                    success = self._generate_tts_with_longxiaochun(word, word_audio_path)

                    if success and os.path.exists(word_audio_path):
                        # 播放生成的音频文件
                        from switchrole.audio_player import play_audio_blocking
                        result = play_audio_blocking(word_audio_path)
                    else:
                        logger.error("TTS音频生成失败")
                        result = False

                return result

            finally:
                # 恢复语音助手
                logger.info("TTS播放后恢复语音助手...")
                self._resume_voice_assistant()

        except Exception as e:
            logger.error(f"longxiaochun TTS异常: {e}")
            # 确保在异常情况下也恢复语音助手
            self._resume_voice_assistant()
            return False

    def _tts_with_longxiaochun_nonblocking(self, word: str) -> bool:
        """使用longxiaochun声音进行TTS朗读（非阻塞方式）"""
        try:
            # 检查是否已有保存的音频文件
            word_audio_path = os.path.join(self.word_audio_folder, f"{word}.wav")

            # 暂停语音助手以释放音频设备
            logger.info("TTS播放前暂停语音助手...")
            self._pause_voice_assistant()

            try:
                if os.path.exists(word_audio_path):
                    logger.info(f"播放已保存的TTS音频（非阻塞）: {word_audio_path}")
                    # 使用非阻塞播放
                    from switchrole.audio_player import get_audio_player
                    player = get_audio_player()
                    result = player.play(word_audio_path)
                else:
                    # 如果没有保存的文件，先生成再播放
                    logger.info(f"生成TTS音频文件: {word}")
                    success = self._generate_tts_with_longxiaochun(word, word_audio_path)

                    if success and os.path.exists(word_audio_path):
                        # 非阻塞播放生成的音频文件
                        from switchrole.audio_player import get_audio_player
                        player = get_audio_player()
                        result = player.play(word_audio_path)
                    else:
                        logger.error("TTS音频生成失败")
                        result = False

                return result

            finally:
                # 恢复语音助手
                logger.info("TTS播放后恢复语音助手...")
                self._resume_voice_assistant()

        except Exception as e:
            logger.error(f"longxiaochun TTS非阻塞异常: {e}")
            # 确保在异常情况下也恢复语音助手
            self._resume_voice_assistant()
            return False

    # 已删除 _play_tts_audio_only 方法，因为现在在 _play_tts_three_times 中统一处理所有播放逻辑

    def _play_round_hint(self):
        """开始录音（提示音已在TTS播放中一起播放）"""
        try:
            logger.info(f"第{self.current_round}轮提示音已在TTS播放中完成，直接开始录音")
            self.status_updated.emit(f"第{self.current_round}轮练习，请跟读", "#f39c12")
            
            # 等待1秒后开始录音
            QTimer.singleShot(1000, self._start_recording)

        except Exception as e:
            logger.error(f"启动录音失败: {e}")
            # 直接开始录音
            self._start_recording()

    def _start_recording(self):
        """开始录音"""
        try:
            logger.info("准备录音...")
            self.status_updated.emit("请跟读单词...", "#e74c3c")
            self.recording_started.emit()

            # 调用实际录音方法，在那里发送2-1-3指令
            self._record_audio()

        except Exception as e:
            logger.error(f"开始录音失败: {e}")
            self.error_occurred.emit(f"开始录音失败: {e}")
            
            # 录音开始失败时也要发送MQTT指令到esp32/s2/control
            if self.mqtt_handler:
                self.mqtt_handler.send_message("esp32/s2/control", "2-2-0")
                logger.info("录音开始失败，已发送MQTT指令: 2-2-0")

    def _record_audio(self):
        """录制音频"""
        try:
            # 生成录音文件名
            timestamp = int(time.time())
            recording_filename = f"{self.current_word}_round{self.current_round}_{timestamp}.wav"
            recording_path = os.path.join(self.recording_folder, recording_filename)

            logger.info(f"录音文件: {recording_path}")

            # 暂停语音助手以释放麦克风
            logger.info("暂停语音助手以释放麦克风...")
            self._pause_voice_assistant()

            try:
                # 等待一下确保麦克风释放
                time.sleep(0.5)

                # 使用ALSA录音器 - 强制使用USB麦克风，配置为16kHz单声道
                from switchrole.alsa_speech_recognizer import ALSASpeechRecognizer
                recognizer = ALSASpeechRecognizer(card_name="lahainayupikiot", use_usb_mic=True)

                # 修改录音参数 - 使用USB麦克风支持的格式，录音后再转换为腾讯云要求的格式
                recognizer.sample_rate = 48000  # USB麦克风支持的采样率（48000Hz）
                recognizer.channels = 2  # USB麦克风支持的双声道
                recognizer.format = "S16_LE"  # 16位小端格式
                logger.info(f"配置录音参数（USB麦克风支持格式）: {recognizer.sample_rate}Hz, {recognizer.channels}声道, {recognizer.format}")

                if not recognizer.initialize():
                    logger.error("ALSA录音器初始化失败")
                    self.error_occurred.emit("录音器初始化失败")
                    
                    # 录音器初始化失败时也要发送MQTT指令到esp32/s2/control
                    if self.mqtt_handler:
                        self.mqtt_handler.send_message("esp32/s2/control", "2-2-0")
                        logger.info("录音器初始化失败，已发送MQTT指令: 2-2-0")
                    return

                # 发送MQTT指令开始录音 - 在真正开始录音时发送
                if self.mqtt_handler:
                    self.mqtt_handler.send_message("esp32/s2/control", "2-1-3")
                    logger.info("已发送MQTT录音开始指令: 2-1-3")

                # 录制5秒音频
                logger.info(f"录音参数确认: 时长={self.recording_duration}秒, 采样率={recognizer.sample_rate}Hz, 声道={recognizer.channels}, 格式={recognizer.format}")
                logger.info("现在开始真正录音...")
                success = recognizer.record_audio_to_file(self.recording_duration, recording_path)

                if success:
                    logger.info(f"录音完成: {recording_path}")
                    self.recording_completed.emit(recording_path)

                    # 发送MQTT指令结束录音 - 发送到esp32/s2/control主题
                    if self.mqtt_handler:
                        self.mqtt_handler.send_message("esp32/s2/control", "2-2-0")
                        logger.info("已发送MQTT录音结束指令: 2-2-0")

                    # 开始语音评测
                    self._evaluate_pronunciation(recording_path)
                else:
                    logger.error("录音失败")
                    self.error_occurred.emit("录音失败")
                    
                    # 录音失败时也要发送MQTT指令到esp32/s2/control
                    if self.mqtt_handler:
                        self.mqtt_handler.send_message("esp32/s2/control", "2-2-0")
                        logger.info("录音失败，已发送MQTT指令: 2-2-0")

            finally:
                # 恢复语音助手
                logger.info("恢复语音助手...")
                self._resume_voice_assistant()

        except Exception as e:
            logger.error(f"录音过程失败: {e}")
            self.error_occurred.emit(f"录音过程失败: {e}")
            
            # 录音过程异常时也要发送MQTT指令到esp32/s2/control
            if self.mqtt_handler:
                self.mqtt_handler.send_message("esp32/s2/control", "2-2-0")
                logger.info("录音过程异常，已发送MQTT指令: 2-2-0")

    def _pause_voice_assistant(self):
        """暂停语音助手以释放麦克风"""
        try:
            logger.info("暂停语音助手以释放麦克风...")

            # 🔧 修复：使用正确的暂停机制，避免手动停止组件导致卡死
            try:
                # 从主窗口获取语音助手服务实例
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'voice_assistant_service') and widget.voice_assistant_service:
                            logger.info("找到语音助手服务，执行暂停操作...")
                            # 使用正确的暂停方法
                            widget.voice_assistant_service.pause_for_external_audio()
                            logger.info("✅ 语音助手已暂停")

                            # 等待暂停生效
                            time.sleep(1.0)
                            logger.info("✅ 麦克风应已释放")
                            return
            except Exception as e:
                logger.warning(f"通过服务暂停语音助手失败: {e}")

            # 备用方案：等待一段时间让麦克风设备释放
            logger.info("使用备用等待方案释放麦克风...")
            time.sleep(1)  # 等待设备释放
            logger.info("✅ 麦克风设备等待释放完成")

        except Exception as e:
            logger.error(f"暂停语音助手失败: {e}")

    def _resume_voice_assistant(self):
        """恢复语音助手"""
        try:
            logger.info("恢复语音助手...")

            # 🔧 修复：使用正确的恢复机制
            try:
                # 从主窗口获取语音助手服务实例
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'voice_assistant_service') and widget.voice_assistant_service:
                            widget.voice_assistant_service.resume_after_external_audio()
                            logger.info("✅ 语音助手已恢复")
                            return
            except Exception as e:
                logger.warning(f"通过服务恢复语音助手失败: {e}")

        except Exception as e:
            logger.error(f"恢复语音助手失败: {e}")



    def _evaluate_pronunciation(self, audio_path: str):
        """评测发音"""
        try:
            logger.info(f"开始语音评测: {audio_path}")
            self.status_updated.emit("正在评测发音...", "#f39c12")

            # 使用腾讯云语音评测
            score = self._tencent_speech_evaluation(audio_path, self.current_word)

            if score is not None:
                self.current_score = score
                logger.info(f"评测分数: {score}")
                self.score_updated.emit(score, self.current_round)

                # 根据分数决定下一步
                self._handle_evaluation_result(score)
            else:
                logger.error("语音评测失败")
                self.error_occurred.emit("语音评测失败")

        except Exception as e:
            logger.error(f"语音评测异常: {e}")
            self.error_occurred.emit(f"语音评测异常: {e}")

    def _tencent_speech_evaluation(self, audio_path: str, ref_text: str) -> Optional[float]:
        """腾讯云语音评测"""
        try:
            # 读取音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            # 转换为PCM格式（如果需要）
            pcm_data = self._convert_to_pcm(audio_data)

            # 调用腾讯云API
            from tencentcloud.common import credential
            from tencentcloud.soe.v20180724 import soe_client, models

            cred = credential.Credential(self.TENCENT_SECRET_ID, self.TENCENT_SECRET_KEY)
            client = soe_client.SoeClient(cred, self.TENCENT_REGION)
            req = models.TransmitOralProcessWithInitRequest()

            session_id = str(uuid.uuid4())
            params = {
                "SeqId": 1, "IsEnd": 1,
                "VoiceFileType": 1, "VoiceEncodeType": 1,
                "UserVoiceData": base64.b64encode(pcm_data).decode(),
                "SessionId": session_id,
                "RefText": ref_text,
                "WorkMode": 1, "EvalMode": 1,
                "ServerType": 0, "ScoreCoeff": 1.0
            }
            req.from_json_string(json.dumps(params))

            resp = client.TransmitOralProcessWithInit(req)
            result = json.loads(resp.to_json_string())

            logger.info(f"腾讯云API响应: {result}")

            # 提取准确度分数
            overall_acc = result.get("PronAccuracy", -1)

            if overall_acc >= 0:
                logger.info(f"语音评测成功，准确度: {overall_acc}")
                return overall_acc
            else:
                logger.error(f"评测结果无效，完整响应: {result}")
                return None

        except Exception as e:
            logger.error(f"腾讯云语音评测失败: {e}")
            return None

    def _convert_to_pcm(self, audio_data: bytes) -> bytes:
        """转换音频为PCM格式"""
        try:
            import wave
            import io

            # 如果是WAV文件，提取PCM数据
            try:
                # 创建内存中的WAV文件对象
                wav_io = io.BytesIO(audio_data)
                with wave.open(wav_io, 'rb') as wav_file:
                    # 检查音频参数
                    channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    framerate = wav_file.getframerate()

                    logger.info(f"音频参数: 声道={channels}, 位深={sample_width*8}, 采样率={framerate}")

                    # 腾讯云要求: 16kHz, 16bit, 单声道
                    pcm_data = wav_file.readframes(wav_file.getnframes())

                    if sample_width == 2:  # 16位音频
                        import numpy as np

                        # 将字节数据转换为numpy数组
                        audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                        # 处理声道转换
                        if channels == 2:
                            logger.info("转换双声道为单声道")
                            # 重塑为双声道格式
                            stereo_audio = audio_array.reshape(-1, 2)
                            # 取左声道
                            mono_audio = stereo_audio[:, 0]
                        else:
                            logger.info("音频已是单声道格式")
                            mono_audio = audio_array

                        # 处理采样率转换
                        if framerate != 16000:
                            logger.info(f"转换采样率: {framerate}Hz -> 16000Hz")
                            # 简单的重采样：线性插值
                            original_length = len(mono_audio)
                            target_length = int(original_length * 16000 / framerate)

                            # 使用numpy的插值进行重采样
                            original_indices = np.linspace(0, original_length - 1, original_length)
                            target_indices = np.linspace(0, original_length - 1, target_length)
                            resampled_audio = np.interp(target_indices, original_indices, mono_audio.astype(np.float32))
                            mono_audio = resampled_audio.astype(np.int16)
                            logger.info(f"采样率转换完成: {original_length} -> {target_length} 采样点")

                        # 转换回字节
                        pcm_data = mono_audio.tobytes()
                        logger.info(f"音频转换完成，最终大小: {len(pcm_data)} 字节")
                        return pcm_data
                    else:
                        logger.warning(f"不支持的音频位深: {sample_width*8}bit")
                        return pcm_data

            except wave.Error as e:
                logger.warning(f"WAV文件解析失败: {e}，尝试直接使用原始数据")
                return audio_data

        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            return audio_data

    def _handle_evaluation_result(self, score: float):
        """处理评测结果"""
        logger.info(f"处理评测结果: 分数={score}, 轮次={self.current_round}")

        if self.current_round >= self.max_rounds:
            # 第三轮：无论分数如何，都播放bad.wav
            logger.info("第三轮完成，无论分数如何都播放bad.wav")
            self.status_updated.emit(f"第三轮完成，得分: {score:.1f}", "#e74c3c")
            self._play_failure_audio()
        elif score >= self.target_score:
            # 分数达标，播放成功音频并结束
            logger.info("分数达标，流程成功完成")
            self.status_updated.emit(f"太棒了！得分: {score:.1f}", "#27ae60")
            self._play_success_audio()
        else:
            # 分数不达标，进入下一轮
            logger.info("分数不达标，进入下一轮")
            self.status_updated.emit(f"得分: {score:.1f}，再试一次", "#f39c12")
            self.current_round += 1
            QTimer.singleShot(2000, self._start_practice_round)

    def _play_success_audio(self):
        """播放成功音频"""
        try:
            if os.path.exists("good.wav"):
                logger.info("播放成功音频: good.wav")
                from switchrole.audio_player import play_audio_blocking
                play_audio_blocking("good.wav")

            # 流程完成
            self._complete_process(True)

        except Exception as e:
            logger.error(f"播放成功音频失败: {e}")
            self._complete_process(True)

    def _play_failure_audio(self):
        """播放失败音频"""
        try:
            if os.path.exists("bad.wav"):
                logger.info("播放失败音频: bad.wav")
                from switchrole.audio_player import play_audio_blocking
                play_audio_blocking("bad.wav")

            # 流程完成
            self._complete_process(False)

        except Exception as e:
            logger.error(f"播放失败音频失败: {e}")
            self._complete_process(False)

    def _complete_process(self, success: bool):
        """完成流程"""
        logger.info(f"指尖单词学习流程完成: {self.current_word}, 成功: {success}")
        self.is_processing = False
        self.process_completed.emit(self.current_word, success)

        if success:
            self.status_updated.emit("学习完成！", "#27ae60")
        else:
            self.status_updated.emit("学习结束，继续加油！", "#e74c3c")

    def cleanup(self):
        """清理资源"""
        logger.info("开始清理增强版指尖单词处理器资源...")

        # 🔧 修复：确保语音助手被正确恢复
        try:
            # 如果语音助手被暂停了，需要恢复它
            logger.info("检查并恢复语音助手状态...")
            self._resume_voice_assistant()
            logger.info("✅ 语音助手状态已恢复")

        except Exception as e:
            logger.warning(f"恢复语音助手状态失败: {e}")

        # 重置处理状态
        self.is_processing = False
        self.current_word = ""
        self.current_round = 0
        self.current_score = 0.0

        # 清理处理器引用
        self.tts_handler = None
        self.tts_function = None

        logger.info("✅ 增强版指尖单词处理器资源已完全清理")
