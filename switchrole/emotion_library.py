#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表情库系统 - 为AI回复匹配合适的表情状态

功能：
1. 定义表情库数据结构
2. 根据文本内容智能匹配表情
3. 集成MQTT表情发送功能
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

# 配置日志
logger = logging.getLogger(__name__)

# 🎭 表情库定义 - 根据用户需求
EMOTION_LIBRARY = [
    {"status": "脸红", "code": "2-0-4", "keywords": ["收到夸奖", "不好意思", "害羞", "表扬", "夸奖", "谢谢你", "太好了"]},
    {"status": "眨眼", "code": "2-0-5", "keywords": ["卖萌", "吸引注意", "可爱", "俏皮", "眨眨眼", "嘿嘿"]},
    {"status": "笑脸", "code": "2-0-6", "keywords": ["有点开心", "有点喜悦", "开心", "高兴", "快乐", "真棒", "好的", "没问题"]},
    {"status": "哭泣", "code": "2-0-7", "keywords": ["被骂了", "难过", "有点复杂", "做错事情", "对不起", "抱歉", "伤心", "难过"]},
    {"status": "昏阙", "code": "2-0-8", "keywords": ["太难了", "难到了", "太复杂了", "好复杂", "不懂", "晕了", "头大"]},
    {"status": "戳脸", "code": "2-0-9", "keywords": ["可爱", "漂亮", "开心", "无聊", "好玩", "有趣", "逗你玩"]},
    {"status": "疲倦", "code": "2-0-10", "keywords": ["好累", "困了", "疲倦", "想睡觉", "太晚了", "累了", "休息"]},
    {"status": "心心眼", "code": "2-0-11", "keywords": ["喜欢", "爱你", "羡慕", "超级爱你", "好可爱", "喜欢你", "爱心"]}
]

class EmotionLibrary:
    """表情库管理器"""
    
    def __init__(self):
        self.emotions = EMOTION_LIBRARY
        self.default_emotion = {"status": "笑脸", "code": "2-0-6", "keywords": []}
        logger.info(f"📚 表情库已加载，包含 {len(self.emotions)} 种表情")
    
    def analyze_text_emotion(self, text: str) -> Dict[str, str]:
        """
        分析文本并返回最合适的表情
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict: 包含status和code的表情信息
        """
        if not text or not text.strip():
            return self.default_emotion
        
        text_lower = text.lower().strip()
        
        # 计算每种表情的匹配分数
        emotion_scores = []
        
        for emotion in self.emotions:
            score = 0
            matched_keywords = []
            
            for keyword in emotion["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                emotion_scores.append({
                    "emotion": emotion,
                    "score": score,
                    "matched_keywords": matched_keywords
                })
        
        # 选择得分最高的表情
        if emotion_scores:
            best_emotion = max(emotion_scores, key=lambda x: x["score"])
            logger.debug(f"🎭 文本匹配表情: '{text}' -> {best_emotion['emotion']['status']} (关键词: {best_emotion['matched_keywords']})")
            return best_emotion["emotion"]
        
        # 没有匹配到关键词，使用默认表情
        logger.debug(f"🎭 使用默认表情: '{text}' -> {self.default_emotion['status']}")
        return self.default_emotion
    
    def get_emotion_code(self, text: str) -> str:
        """
        获取文本对应的表情代码
        
        Args:
            text: 要分析的文本
            
        Returns:
            str: 表情代码（如 "2-0-6"）
        """
        emotion = self.analyze_text_emotion(text)
        return emotion["code"]
    
    def get_emotion_status(self, text: str) -> str:
        """
        获取文本对应的表情状态
        
        Args:
            text: 要分析的文本
            
        Returns:
            str: 表情状态（如 "笑脸"）
        """
        emotion = self.analyze_text_emotion(text)
        return emotion["status"]
    
    def send_emotion_for_text(self, text: str) -> bool:
        """
        为文本发送对应的表情到MQTT
        
        Args:
            text: 要分析的文本
            
        Returns:
            bool: 是否发送成功
        """
        try:
            emotion = self.analyze_text_emotion(text)
            code = emotion["code"]
            status = emotion["status"]
            
            from mqtt_emotion_sender import send_emotion_code
            success = send_emotion_code(code)
            
            if success:
                logger.info(f"🎭 表情发送成功: '{text[:30]}...' -> {status}({code})")
            else:
                logger.warning(f"⚠️ 表情发送失败: {status}({code})")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 表情发送异常: {e}")
            return False
    
    def get_all_emotions(self) -> List[Dict]:
        """获取所有可用表情"""
        return self.emotions.copy()
    
    def add_emotion(self, status: str, code: str, keywords: List[str]) -> bool:
        """
        添加新表情
        
        Args:
            status: 表情状态名称
            code: 表情代码
            keywords: 关键词列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 检查代码是否已存在
            for emotion in self.emotions:
                if emotion["code"] == code:
                    logger.warning(f"⚠️ 表情代码已存在: {code}")
                    return False
            
            new_emotion = {
                "status": status,
                "code": code,
                "keywords": keywords
            }
            
            self.emotions.append(new_emotion)
            logger.info(f"✅ 新表情已添加: {status}({code})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加表情失败: {e}")
            return False

# 全局表情库实例
_emotion_library_instance = None

def get_emotion_library() -> EmotionLibrary:
    """获取全局表情库实例"""
    global _emotion_library_instance
    if _emotion_library_instance is None:
        _emotion_library_instance = EmotionLibrary()
    return _emotion_library_instance

def analyze_text_emotion(text: str) -> Dict[str, str]:
    """快速分析文本表情的便捷函数"""
    library = get_emotion_library()
    return library.analyze_text_emotion(text)

def send_emotion_for_text(text: str) -> bool:
    """快速发送文本表情的便捷函数"""
    library = get_emotion_library()
    return library.send_emotion_for_text(text)

def get_emotion_code_for_text(text: str) -> str:
    """快速获取文本表情代码的便捷函数"""
    library = get_emotion_library()
    return library.get_emotion_code(text)

if __name__ == "__main__":
    # 测试表情库
    library = get_emotion_library()
    
    test_texts = [
        "谢谢你的夸奖，我有点不好意思呢！",
        "这个问题太难了，我有点晕了",
        "哈哈，你真可爱！",
        "对不起，我做错了",
        "我好累啊，想睡觉了",
        "我超级喜欢你！",
        "今天天气真好，我很开心"
    ]
    
    print("🎭 表情库测试")
    print("=" * 50)
    
    for text in test_texts:
        emotion = library.analyze_text_emotion(text)
        print(f"文本: {text}")
        print(f"表情: {emotion['status']} ({emotion['code']})")
        print("-" * 30) 