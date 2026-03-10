#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表情管理模块
处理AI回答中的表情信息，匹配表情代码，发送MQTT控制指令
"""

import json
import os
import re
import threading
from typing import List, Dict, Optional, Tuple
from mqtt_emotion_sender import send_emotion_code

class EmotionManager:
    def __init__(self, motion_file=None):
        # 🔧 修复路径问题：使用绝对路径避免switchrole/switchrole路径重复
        if motion_file:
            self.motion_file = motion_file
        else:
            # 获取当前脚本所在目录（switchrole目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.motion_file = os.path.join(current_dir, "motion.json")
        
        self.emotion_data = []
        self.status_to_code = {}
        self.keywords_to_code = {}
        self.load_emotion_data()
        self.lock = threading.Lock()
        
    def load_emotion_data(self):
        """加载表情数据"""
        try:
            with open(self.motion_file, 'r', encoding='utf-8') as f:
                self.emotion_data = json.load(f)
            
            # 构建映射表
            self.status_to_code = {}
            self.keywords_to_code = {}
            
            for item in self.emotion_data:
                status = item['status']
                code = item['code']
                keywords = item['keywords']
                
                # 状态到代码的映射
                self.status_to_code[status] = code
                
                # 关键词到代码的映射
                for keyword in keywords:
                    self.keywords_to_code[keyword] = code
            
            print(f"✅ 表情数据加载成功，共 {len(self.emotion_data)} 种表情")
            print(f"📋 支持的表情状态: {list(self.status_to_code.keys())}")
            
        except Exception as e:
            print(f"❌ 加载表情数据失败: {e}")
            # 使用默认数据
            self.emotion_data = []
            self.status_to_code = {}
            self.keywords_to_code = {}
    
    def get_emotion_code_by_status(self, status: str) -> Optional[str]:
        """根据表情状态获取代码"""
        return self.status_to_code.get(status)
    
    def get_emotion_code_by_keyword(self, text: str) -> Optional[str]:
        """根据文本内容匹配表情关键词获取代码"""
        for keyword, code in self.keywords_to_code.items():
            if keyword in text:
                return code
        return None
    
    def parse_ai_response_with_emotions(self, ai_response: str) -> List[Dict]:
        """
        解析带表情的AI回答
        期望格式: [{"text": "你说话真好听。", "status": "脸红"}, ...]
        
        Returns:
            List[Dict]: [{"text": str, "status": str, "code": str}, ...]
        """
        try:
            # 尝试解析JSON格式的回答
            response_data = json.loads(ai_response.strip())
            
            if isinstance(response_data, list):
                result = []
                for item in response_data:
                    if isinstance(item, dict) and 'text' in item and 'status' in item:
                        text = item['text']
                        status = item['status']
                        code = self.get_emotion_code_by_status(status)
                        
                        if code:
                            result.append({
                                'text': text,
                                'status': status,
                                'code': code
                            })
                            print(f"🎭 解析表情: {text[:20]}... -> {status} ({code})")
                        else:
                            # 如果状态不匹配，尝试关键词匹配
                            code = self.get_emotion_code_by_keyword(text)
                            if code:
                                result.append({
                                    'text': text,
                                    'status': '关键词匹配',
                                    'code': code
                                })
                                print(f"🔍 关键词匹配表情: {text[:20]}... -> {code}")
                            else:
                                # 默认表情
                                result.append({
                                    'text': text,
                                    'status': '默认',
                                    'code': '2-2-0'  # 默认结束状态
                                })
                                print(f"📝 使用默认表情: {text[:20]}...")
                
                return result
            else:
                print("❌ AI回答不是预期的列表格式")
                return self.fallback_text_analysis(ai_response)
                
        except json.JSONDecodeError:
            print("⚠️ AI回答不是JSON格式，使用文本分析")
            return self.fallback_text_analysis(ai_response)
        except Exception as e:
            print(f"❌ 解析AI回答异常: {e}")
            return self.fallback_text_analysis(ai_response)
    
    def fallback_text_analysis(self, text: str) -> List[Dict]:
        """
        后备方案：纯文本分析
        将文本按句子分割，并尝试匹配表情关键词
        """
        sentences = self.split_text_to_sentences(text)
        result = []
        
        for sentence in sentences:
            if sentence.strip():
                code = self.get_emotion_code_by_keyword(sentence)
                if not code:
                    code = "2-2-0"  # 默认结束状态
                
                result.append({
                    'text': sentence.strip(),
                    'status': '文本分析',
                    'code': code
                })
        
        print(f"📝 文本分析完成，共 {len(result)} 个句子")
        return result
    
    def split_text_to_sentences(self, text: str) -> List[str]:
        """将文本按句子分割"""
        # 按句号、感叹号、问号分割
        sentences = re.split(r'[。！？.!?]', text)
        
        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def send_emotion_for_response(self, ai_response: str) -> List[str]:
        """
        为AI回答发送对应的表情代码
        
        Returns:
            List[str]: 发送的表情代码列表
        """
        with self.lock:
            parsed_data = self.parse_ai_response_with_emotions(ai_response)
            sent_codes = []
            
            for item in parsed_data:
                code = item['code']
                text = item['text']
                
                # 发送表情代码
                success = send_emotion_code(code)
                if success:
                    sent_codes.append(code)
                    print(f"📤 表情发送成功: {text[:15]}... -> {code}")
                else:
                    print(f"❌ 表情发送失败: {text[:15]}... -> {code}")
            
            return sent_codes
    
    def send_special_emotion(self, code: str, description: str = "") -> bool:
        """
        发送特殊表情代码
        
        Args:
            code: 表情代码
            description: 描述信息
        """
        success = send_emotion_code(code)
        if success:
            print(f"📤 特殊表情发送成功: {description} -> {code}")
        else:
            print(f"❌ 特殊表情发送失败: {description} -> {code}")
        return success
    
    def send_wake_emotion(self) -> bool:
        """发送唤醒表情 (2-1-3)"""
        return self.send_special_emotion("2-1-3", "唤醒表情")
    
    def send_end_emotion(self) -> bool:
        """发送结束表情 (2-2-0)"""
        return self.send_special_emotion("2-2-0", "结束表情")

# 全局表情管理器实例
_global_emotion_manager: Optional[EmotionManager] = None

def get_emotion_manager() -> EmotionManager:
    """获取全局表情管理器实例"""
    global _global_emotion_manager
    if _global_emotion_manager is None:
        _global_emotion_manager = EmotionManager()
    return _global_emotion_manager

def send_emotion_for_ai_response(ai_response: str) -> List[str]:
    """为AI回答发送表情的便捷函数"""
    manager = get_emotion_manager()
    return manager.send_emotion_for_response(ai_response)

def send_wake_emotion() -> bool:
    """发送唤醒表情的便捷函数"""
    manager = get_emotion_manager()
    return manager.send_wake_emotion()

def send_end_emotion() -> bool:
    """发送结束表情的便捷函数"""
    manager = get_emotion_manager()
    return manager.send_end_emotion()

# AI回答的系统提示词
EMOTION_SYSTEM_PROMPT = """
你是一个情感丰富的AI语音助手。在回答用户问题时，请把每一句话拆成一条记录，并为每条语句附上一个合适的表情状态。

⚠️ 你只能从以下状态中选择一个作为 status（不要生成新的状态）：

["脸红", "眨眼", "笑脸", "哭泣", "昏阙", "戳脸", "疲倦", "心心眼"]

请以如下 JSON 数组格式返回，每句话为一项：

[
  {"text": "你说话真好听。", "status": "脸红"},
  {"text": "我已经学会了今天的新知识！", "status": "笑脸"}
]

重要规则：
1. 每句话都要有对应的表情状态
2. 表情要符合语句的情感色彩
3. 必须严格按照JSON格式返回
4. 不要添加任何其他解释性文本
"""

def test_emotion_manager():
    """测试表情管理器"""
    print("🧪 开始测试表情管理器...")
    
    manager = EmotionManager()
    
    # 测试JSON格式解析
    test_json_response = '''[
        {"text": "你说话真好听。", "status": "脸红"},
        {"text": "我很开心能帮助你！", "status": "笑脸"},
        {"text": "这个问题太难了。", "status": "昏阙"}
    ]'''
    
    print("\n📋 测试JSON格式解析:")
    parsed_data = manager.parse_ai_response_with_emotions(test_json_response)
    for item in parsed_data:
        print(f"  文本: {item['text']}")
        print(f"  状态: {item['status']}")
        print(f"  代码: {item['code']}")
        print()
    
    # 测试纯文本解析
    test_text_response = "你好！今天天气真不错。我很开心能和你聊天。"
    
    print("📋 测试纯文本解析:")
    parsed_text = manager.fallback_text_analysis(test_text_response)
    for item in parsed_text:
        print(f"  文本: {item['text']}")
        print(f"  代码: {item['code']}")
        print()
    
    print("🧪 表情管理器测试完成")

if __name__ == "__main__":
    test_emotion_manager() 