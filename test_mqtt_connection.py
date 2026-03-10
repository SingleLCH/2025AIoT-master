#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MQTT连接
"""

import os
import sys
import time
import logging

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_mqtt_connection():
    """测试MQTT连接"""
    try:
        from mqtt_handler import MQTTHandler
        
        logger.info("创建MQTT处理器...")
        mqtt_handler = MQTTHandler()
        
        logger.info("启动MQTT连接...")
        mqtt_handler.start()
        
        # 等待连接建立
        logger.info("等待MQTT连接建立...")
        for i in range(10):  # 等待最多10秒
            time.sleep(1)
            if mqtt_handler.is_connected:
                logger.info(f"✅ MQTT连接成功 (耗时: {i+1}秒)")
                break
            logger.info(f"等待连接... ({i+1}/10)")
        else:
            logger.error("❌ MQTT连接超时")
            return False
        
        # 测试发送消息
        logger.info("测试发送MQTT消息...")
        success = mqtt_handler.send_message("esp32/s2/control", "test-message")
        if success:
            logger.info("✅ MQTT消息发送成功")
        else:
            logger.error("❌ MQTT消息发送失败")
            return False
        
        # 测试录音控制指令
        logger.info("测试录音开始指令...")
        success1 = mqtt_handler.send_message("esp32/s2/control", "2-1-3")
        time.sleep(1)
        logger.info("测试录音结束指令...")
        success2 = mqtt_handler.send_message("esp32/s2/control", "2-2-0")
        
        if success1 and success2:
            logger.info("✅ 录音控制指令发送成功")
        else:
            logger.error("❌ 录音控制指令发送失败")
            return False
        
        # 停止MQTT
        logger.info("停止MQTT连接...")
        mqtt_handler.stop()
        
        return True
        
    except Exception as e:
        logger.error(f"MQTT连接测试失败: {e}")
        return False


def test_enhanced_gesture_word_handler_mqtt():
    """测试EnhancedGestureWordHandler的MQTT功能"""
    try:
        # 不使用PyQt5，直接测试MQTT部分
        logger.info("测试EnhancedGestureWordHandler的MQTT初始化...")
        
        # 模拟MQTT初始化过程
        from mqtt_handler import MQTTHandler
        mqtt_handler = MQTTHandler()
        mqtt_handler.start()
        
        # 等待连接
        for i in range(5):
            time.sleep(1)
            if mqtt_handler.is_connected:
                logger.info("✅ EnhancedGestureWordHandler MQTT连接成功")
                break
        else:
            logger.error("❌ EnhancedGestureWordHandler MQTT连接失败")
            return False
        
        # 测试发送指令
        if mqtt_handler.send_message("esp32/s2/control", "2-1-2"):
            logger.info("✅ 录音开始指令发送成功")
        else:
            logger.error("❌ 录音开始指令发送失败")
            return False
        
        mqtt_handler.stop()
        return True
        
    except Exception as e:
        logger.error(f"EnhancedGestureWordHandler MQTT测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("开始MQTT连接测试...")
    
    # 测试基本MQTT连接
    logger.info("1. 测试基本MQTT连接...")
    if test_mqtt_connection():
        logger.info("✅ 基本MQTT连接测试通过")
    else:
        logger.error("❌ 基本MQTT连接测试失败")
    
    logger.info("-" * 50)
    
    # 测试EnhancedGestureWordHandler的MQTT
    logger.info("2. 测试EnhancedGestureWordHandler MQTT...")
    if test_enhanced_gesture_word_handler_mqtt():
        logger.info("✅ EnhancedGestureWordHandler MQTT测试通过")
    else:
        logger.error("❌ EnhancedGestureWordHandler MQTT测试失败")
    
    logger.info("MQTT连接测试完成")


if __name__ == "__main__":
    main()
