#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MQTT表情发送模块
发送表情代码到ESP32控制设备
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
from typing import Optional

class MQTTEmotionSender:
    def __init__(self, broker_host="117.72.8.255", broker_port=1883, topic="esp32/s2/control"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client = None
        self.connected = False
        self.lock = threading.Lock()
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.connected = True
            print(f"✅ MQTT连接成功: {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            print(f"❌ MQTT连接失败，返回码: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.connected = False
        print(f"📡 MQTT连接断开，返回码: {rc}")
    
    def on_publish(self, client, userdata, mid):
        """MQTT发布消息回调"""
        print(f"📤 消息发送成功，消息ID: {mid}")
    
    def connect(self) -> bool:
        """连接到MQTT服务器"""
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_publish = self.on_publish
            
            print(f"🔌 正在连接MQTT服务器: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # 启动网络循环
            self.client.loop_start()
            
            # 等待连接建立
            timeout = 5
            while timeout > 0 and not self.connected:
                time.sleep(0.1)
                timeout -= 0.1
            
            return self.connected
            
        except Exception as e:
            print(f"❌ MQTT连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开MQTT连接"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("📡 MQTT连接已断开")
    
    def send_emotion_code(self, code: str) -> bool:
        """
        发送表情代码
        
        Args:
            code: 表情代码，如 "2-0-4", "2-1-3", "2-2-0"
        
        Returns:
            bool: 发送是否成功
        """
        with self.lock:
            if not self.connected:
                print("❌ MQTT未连接，尝试重新连接...")
                if not self.connect():
                    return False
            
            try:
                # 准备发送的消息
                message = code
                
                # 发送JSON格式消息
                
                result = self.client.publish(self.topic, message, qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"📤 表情代码发送成功: {code} -> {self.topic}")
                    return True
                else:
                    print(f"❌ 表情代码发送失败: {code}, 错误码: {result.rc}")
                    return False
                    
            except Exception as e:
                print(f"❌ 发送表情代码异常: {e}")
                return False

# 全局MQTT发送器实例
_global_mqtt_sender: Optional[MQTTEmotionSender] = None

def get_mqtt_sender() -> MQTTEmotionSender:
    """获取全局MQTT发送器实例"""
    global _global_mqtt_sender
    if _global_mqtt_sender is None:
        _global_mqtt_sender = MQTTEmotionSender()
        _global_mqtt_sender.connect()
    return _global_mqtt_sender

def send_emotion_code(code: str) -> bool:
    """
    快速发送表情代码的便捷函数
    
    Args:
        code: 表情代码，如 "2-0-4", "2-1-3", "2-2-0"
    
    Returns:
        bool: 发送是否成功
    """
    sender = get_mqtt_sender()
    return sender.send_emotion_code(code)

def cleanup_mqtt():
    """清理MQTT连接"""
    global _global_mqtt_sender
    if _global_mqtt_sender:
        _global_mqtt_sender.disconnect()
        _global_mqtt_sender = None

# 测试函数
def test_mqtt_sender():
    """测试MQTT发送功能"""
    print("🧪 开始测试MQTT表情发送...")
    
    # 测试发送不同的表情代码
    test_codes = ["2-0-4", "2-1-3", "2-2-0"]
    
    for code in test_codes:
        print(f"\n📤 测试发送代码: {code}")
        success = send_emotion_code(code)
        if success:
            print(f"✅ 发送成功: {code}")
        else:
            print(f"❌ 发送失败: {code}")
        time.sleep(1)  # 间隔1秒
    
    cleanup_mqtt()
    print("\n🧪 MQTT测试完成")

if __name__ == "__main__":
    test_mqtt_sender() 