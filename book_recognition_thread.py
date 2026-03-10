# -*- coding: utf-8 -*-
"""
图书识别AI分析线程
专门用于在后台处理图书识别请求，避免阻塞UI线程
"""

import os
import base64
import json
import logging
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal
from openai import OpenAI

logger = logging.getLogger(__name__)


class BookRecognitionThread(QThread):
    """图书识别AI分析线程"""
    
    # 信号定义
    analysis_started = pyqtSignal()  # 分析开始
    analysis_progress = pyqtSignal(str)  # 分析进度更新
    analysis_completed = pyqtSignal(str)  # 分析完成，返回图书名称
    analysis_failed = pyqtSignal(str)  # 分析失败
    
    def __init__(self, photo_path: str):
        super().__init__()
        self.photo_path = photo_path
        self.book_name = None
    
    def run(self):
        """运行图书识别AI分析"""
        try:
            logger.info(f"图书识别线程开始运行，分析照片: {self.photo_path}")
            
            # 发出开始信号
            self.analysis_started.emit()
            
            # 更新进度
            self.analysis_progress.emit("开始识别图书...")
            
            # 检查照片文件是否存在
            if not os.path.exists(self.photo_path):
                raise Exception(f"图书照片文件不存在: {self.photo_path}")
            
            # 调用AI识别图书
            self.analysis_progress.emit("正在连接AI服务...")
            book_name = self._recognize_book_name()
            
            if book_name:
                self.analysis_progress.emit("图书识别完成")
                logger.info(f"图书识别成功: {book_name}")
                
                # 发出完成信号
                self.analysis_completed.emit(book_name)
            else:
                error_msg = "无法识别图书名称"
                logger.error(error_msg)
                self.analysis_failed.emit(error_msg)
                
        except Exception as e:
            error_msg = f"图书识别过程出错: {e}"
            logger.error(error_msg)
            self.analysis_failed.emit(error_msg)
    
    def _recognize_book_name(self) -> Optional[str]:
        """使用阿里大模型识别图书名称"""
        try:
            # 从环境变量获取 API 密钥
            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not api_key:
                logger.error("未设置 DASHSCOPE_API_KEY 环境变量")
                return None
            
            # Base64编码图片，并检测图片格式
            image_format = "png" if self.photo_path.lower().endswith('.png') else "jpeg"
            with open(self.photo_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 创建OpenAI客户端（使用阿里云DashScope兼容接口）
            client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 构建请求消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """识别图片中的图书名称。要求：
1. 只返回书名，不要其他内容
2. 教材要包含年级学科（如：三年级语文）
3. 看不清楚就返回"未能识别"

图书名称："""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            # 发起AI请求
            self.analysis_progress.emit("正在分析图书内容...")
            response = client.chat.completions.create(
                model="qwen-vl-max",  # 🔧 改用更适合图像识别的模型
                messages=messages,
                max_tokens=50,  # 进一步限制输出，只要书名
                temperature=0.0   # 🔧 完全确定性输出，提高准确性
            )
            
            # 提取响应内容
            book_name = response.choices[0].message.content.strip()
            logger.info(f"🔍 AI原始响应: '{book_name}'")
            
            # 清理响应内容，去除可能的多余信息
            if book_name and book_name != "未能识别" and book_name.lower() != "未能识别":
                # 去除可能的引号和多余符号
                book_name = book_name.strip('"\'""''《》')
                # 去除可能的前缀词汇
                prefixes_to_remove = ["图书名称：", "书名：", "名称：", "书籍："]
                for prefix in prefixes_to_remove:
                    if book_name.startswith(prefix):
                        book_name = book_name[len(prefix):].strip()
                
                # 如果返回的内容太长，可能包含多余信息，截取合理长度
                if len(book_name) > 50:
                    book_name = book_name[:50]
                
                # 最终检查是否为有效书名
                if len(book_name.strip()) > 0:
                    logger.info(f"✅ AI识别到的图书名称: '{book_name}'")
                    return book_name
                else:
                    logger.warning("⚠️ AI响应内容为空")
                    return None
            else:
                logger.warning(f"⚠️ AI未能识别图书名称，响应: '{book_name}'")
                return None
                
        except Exception as e:
            logger.error(f"AI图书识别失败: {e}")
            return None
    
    def stop_analysis(self):
        """停止分析（请求线程结束）"""
        logger.info("请求停止图书识别线程")
        self.requestInterruption()
        if self.isRunning():
            self.wait(3000)  # 等待3秒
            if self.isRunning():
                logger.warning("强制终止图书识别线程")
                self.terminate() 