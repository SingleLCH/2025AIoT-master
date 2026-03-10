#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指尖单词处理器 - 集成讯飞指尖单词识别API和TTS功能
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
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GestureWordHandler(QObject):
    """指尖单词处理器"""
    
    # 信号定义
    word_recognized = pyqtSignal(str)  # 单词识别完成信号
    tts_started = pyqtSignal(str)  # TTS开始信号
    tts_completed = pyqtSignal()  # TTS完成信号
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
        
        # 业务参数
        self.BusinessArgs = {
            "ent": "fingerocr",
            "mode": "finger+ocr",
            "method": "dynamic",
            "resize_w": 1088,
            "resize_h": 1632,
        }
        
        # TTS处理器
        self.tts_handler = None
        self.init_tts()
        
        # 状态
        self.is_processing = False
        self.current_word = ""
        
        logger.info("指尖单词处理器初始化完成")
    
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
        """从图片识别指尖单词"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        if not os.path.exists(image_path):
            self.error_occurred.emit(f"图片文件不存在: {image_path}")
            return
        
        self.is_processing = True
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
                
                # 开始TTS朗读
                self.start_tts(recognized_word)
            else:
                self.error_occurred.emit("识别的单词为空")
                self.is_processing = False
                
        except Exception as e:
            error_msg = f"识别过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_processing = False
    
    def start_tts(self, word: str):
        """开始TTS朗读"""
        if not self.tts_handler:
            logger.warning("TTS处理器未初始化，跳过朗读")
            self.is_processing = False
            return
        
        try:
            # 调试：检查传入的单词
            logger.info(f"开始TTS朗读: '{word}' (类型: {type(word)}, 长度: {len(word) if word else 'None'})")
            if not word or not word.strip():
                logger.error("传入TTS的单词为空")
                self.error_occurred.emit("单词为空，无法朗读")
                self.is_processing = False
                return

            self.tts_started.emit(word)
            self.status_updated.emit(f"正在朗读: {word}", "#3498db")
            
            # 使用TTS朗读单词（指尖单词专用longxiaochun声音）
            success = self._tts_with_longxiaochun(word)
            if not success:
                logger.warning("TTS朗读失败")
            
            # 延迟一下再发射完成信号
            QTimer.singleShot(2000, self._on_tts_completed)
            
        except Exception as e:
            error_msg = f"TTS朗读失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_processing = False
    
    def _tts_with_longxiaochun(self, word: str) -> bool:
        """使用longxiaochun声音进行TTS朗读"""
        try:
            import os
            from switchrole.alsa_cosyvoice_tts import ALSACosyVoiceTTS

            # 检查API key
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                logger.error("DASHSCOPE_API_KEY未设置")
                return False

            # 暂停语音助手以释放音频设备
            logger.info("TTS播放前暂停语音助手...")
            self._pause_voice_assistant()

            try:
                # 创建专门的TTS实例，使用longxiaochun声音
                tts = ALSACosyVoiceTTS()
                # 临时设置声音为longxiaochun
                original_voice = tts.voice
                tts.voice = "longxiaochun"

                logger.info(f"使用longxiaochun声音朗读: {word}")
                success = tts.synthesize_and_play_text(word)

                # 恢复原始声音设置
                tts.voice = original_voice

                return success

            finally:
                # 恢复语音助手
                logger.info("TTS播放后恢复语音助手...")
                self._resume_voice_assistant()

        except Exception as e:
            logger.error(f"longxiaochun TTS异常: {e}")
            # 确保在异常情况下也恢复语音助手
            self._resume_voice_assistant()
            return False

    def _on_tts_completed(self):
        """TTS完成处理"""
        logger.info("TTS朗读完成")
        self.tts_completed.emit()
        self.status_updated.emit("朗读完成", "#27ae60")
        self.is_processing = False

    def _pause_voice_assistant(self):
        """暂停语音助手以释放麦克风"""
        try:
            # 尝试获取全局语音助手服务实例
            try:
                # 从主窗口获取语音助手服务实例
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'voice_service') and widget.voice_service:
                            widget.voice_service.pause_for_external_audio()
                            logger.info("通过服务暂停语音助手成功")
                            import time
                            time.sleep(1)  # 等待暂停生效
                            return
            except Exception as e:
                logger.warning(f"通过服务暂停语音助手失败: {e}")

            # 强制停止所有音频进程
            try:
                import subprocess
                import time
                # 停止可能占用麦克风的进程
                subprocess.run(['pkill', '-f', 'arecord'], check=False)
                subprocess.run(['pkill', '-f', 'pulseaudio'], check=False)
                time.sleep(0.5)
                # 重启pulseaudio
                subprocess.run(['pulseaudio', '--start'], check=False)
                logger.info("强制释放音频设备完成")
            except Exception as e:
                logger.warning(f"强制释放音频设备失败: {e}")

        except Exception as e:
            logger.error(f"暂停语音助手失败: {e}")

    def _resume_voice_assistant(self):
        """恢复语音助手"""
        try:
            # 尝试获取全局语音助手服务实例
            try:
                # 从主窗口获取语音助手服务实例
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'voice_service') and widget.voice_service:
                            widget.voice_service.resume_after_external_audio()
                            logger.info("通过服务恢复语音助手成功")
                            return
            except Exception as e:
                logger.warning(f"通过服务恢复语音助手失败: {e}")

        except Exception as e:
            logger.error(f"恢复语音助手失败: {e}")

    def cleanup(self):
        """清理资源"""
        self.is_processing = False
        # TTS使用函数调用，无需清理
        self.tts_handler = None
        self.tts_function = None
        logger.info("指尖单词处理器资源已清理")
