#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
阿里云百炼平台API调用模块
用于生成教案内容
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv("xiaoxin.env")

logger = logging.getLogger(__name__)

class BailianTeachingPlanGenerator:
    """阿里云百炼教案生成器"""
    
    def __init__(self):
        self.app_id = "1c82397ad4cd41f0b06d6b3cefa6c5bc"
        self.api_key = os.environ.get("DASHSCOPE_API_KEY")
        
        if not self.api_key:
            raise ValueError("未找到DASHSCOPE_API_KEY环境变量")
        
        # 阿里云百炼应用接口URL
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/apps/{}/completion".format(self.app_id)
        
        logger.info(f"✅ 阿里云百炼教案生成器初始化完成，应用ID: {self.app_id}")
    
    def generate_teaching_plan(self, topic: str) -> Optional[str]:
        """
        生成教案
        
        Args:
            topic: 教案主题
            
        Returns:
            str: 生成的教案内容，失败时返回None
        """
        try:
            logger.info(f"📚 开始生成关于'{topic}'的教案")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-DashScope-SSE": "disable"  # 禁用流式输出
            }
            
            # 构建请求数据
            data = {
                "input": {
                    "prompt": f"请为我生成一个关于'{topic}'的详细教案，包括教学目标、教学重点、教学难点、教学过程和教学总结。"
                },
                "parameters": {
                    "result_format": "message"
                },
                "debug": {}
            }
            
            logger.info(f"🚀 发送请求到阿里云百炼平台...")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 解析响应
                if "output" in result and "text" in result["output"]:
                    teaching_plan = result["output"]["text"]
                    logger.info(f"✅ 教案生成成功，长度: {len(teaching_plan)} 字符")
                    return teaching_plan
                else:
                    logger.error(f"❌ 响应格式异常: {result}")
                    return None
            else:
                logger.error(f"❌ API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 生成教案异常: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info("🔍 测试阿里云百炼API连接...")
            
            # 使用简单的测试主题
            result = self.generate_teaching_plan("数学")
            
            if result:
                logger.info("✅ API连接测试成功")
                return True
            else:
                logger.warning("⚠️ API连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ API连接测试异常: {e}")
            return False

# 全局实例
_generator_instance = None

def get_bailian_generator() -> BailianTeachingPlanGenerator:
    """获取教案生成器实例"""
    global _generator_instance
    
    if _generator_instance is None:
        _generator_instance = BailianTeachingPlanGenerator()
    
    return _generator_instance

def generate_teaching_plan_api(topic: str) -> Optional[str]:
    """
    生成教案的便捷函数
    
    Args:
        topic: 教案主题
        
    Returns:
        str: 生成的教案内容
    """
    generator = get_bailian_generator()
    return generator.generate_teaching_plan(topic)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    generator = get_bailian_generator()
    
    # 测试连接
    if generator.test_connection():
        print("✅ 阿里云百炼API连接正常")
    else:
        print("❌ 阿里云百炼API连接失败")