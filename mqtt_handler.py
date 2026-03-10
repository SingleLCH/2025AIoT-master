# -*- coding: utf-8 -*-
"""
MQTT处理模块
"""

import json
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import paho.mqtt.client as mqtt
from config import MQTT_CONFIG, CONTROL_COMMANDS, SETTINGS_COMMANDS, GESTURE_COMMANDS

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MQTTHandler(QThread):
    """MQTT处理线程"""
    
    # 信号定义
    control_command_received = pyqtSignal(str)  # 控制指令信号（统一使用gesture主题）
    notification_received = pyqtSignal(str, dict)  # 通知信号 (topic, data)
    room_invitation_received = pyqtSignal(str)  # 房间邀请信号
    room_close_received = pyqtSignal()  # 房间关闭信号
    
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        
    def run(self):
        """线程运行方法"""
        try:
            logger.info(f"正在连接MQTT服务器: {MQTT_CONFIG['broker']}:{MQTT_CONFIG['port']}")
            self.client.connect(MQTT_CONFIG['broker'], MQTT_CONFIG['port'], 60)
            self.client.loop_forever()
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        """连接成功回调"""
        if rc == 0:
            logger.info("MQTT连接成功")
            self.is_connected = True
            
            # 统一订阅gesture主题作为主控制主题
            client.subscribe(MQTT_CONFIG['gesture_topic'])
            logger.info(f"已订阅gesture主题: {MQTT_CONFIG['gesture_topic']}")
            
            # 订阅通知主题
            for topic in MQTT_CONFIG['notification_topics']:
                client.subscribe(topic)
                logger.info(f"已订阅通知主题: {topic}")
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
            self.is_connected = False
    
    def on_message(self, client, userdata, msg):
        """消息接收回调"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        logger.info(f"收到消息 - 主题: {topic}, 内容: {payload}")
        
        try:
            if topic == MQTT_CONFIG['gesture_topic']:
                # 统一处理gesture主题消息作为控制指令
                self.handle_control_command(payload)
            elif topic == 'nf':
                # 处理通知消息
                self.handle_notification(payload)
            elif topic == 'room':
                # 处理房间邀请
                self.handle_room_invitation(payload)
            elif topic == 'roomclose':
                # 处理房间关闭
                self.handle_room_close(payload)
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        logger.info("MQTT连接已断开")
        self.is_connected = False
    
    def handle_control_command(self, payload):
        """处理控制指令（统一从gesture主题接收）"""
        command = payload.strip()
        logger.info(f"接收到控制指令: {command}")
        
        # 直接发送原始指令，让各个界面自己判断如何处理
        self.control_command_received.emit(command)
    
    def handle_notification(self, payload):
        """处理通知消息"""
        try:
            data = json.loads(payload)
            if data.get('type') == 'notification':
                logger.info(f"接收到通知: {data.get('message', '')}")
                self.notification_received.emit('nf', data)
            elif data.get('type') == 'teacher_connect_request':
                # 处理发送到nf主题的房间邀请消息
                room_id = data.get('room_id', '')
                from_teacher = data.get('from', '老师')
                logger.info(f"接收到来自{from_teacher}的房间邀请: {room_id}")
                # 发送房间邀请信号
                self.room_invitation_received.emit(room_id)
                # 同时发送通知信号用于显示通知窗口
                self.notification_received.emit('room', data)
        except json.JSONDecodeError:
            logger.error(f"通知消息JSON解析失败: {payload}")
    
    def handle_room_invitation(self, payload):
        """处理房间邀请"""
        try:
            data = json.loads(payload)
            if data.get('type') == 'teacher_connect_request' and 'room_id' in data:
                room_id = data['room_id']
                logger.info(f"接收到房间邀请: {room_id}")
                self.room_invitation_received.emit(room_id)
                # 同时发送通知信号
                self.notification_received.emit('room', data)
        except json.JSONDecodeError:
            logger.error(f"房间邀请消息JSON解析失败: {payload}")
    
    def handle_room_close(self, payload):
        """处理房间关闭"""
        try:
            if payload.strip().lower() == 'exit':
                logger.info("接收到房间关闭指令")
                self.room_close_received.emit()
            else:
                # 尝试解析JSON
                data = json.loads(payload)
                if data.get('action') == 'exit' or data.get('type') == 'exit':
                    logger.info("接收到房间关闭指令")
                    self.room_close_received.emit()
        except json.JSONDecodeError:
            logger.warning(f"房间关闭消息格式不匹配: {payload}")
    
    def send_message(self, topic, message):
        """发送消息"""
        if self.is_connected:
            try:
                self.client.publish(topic, message)
                logger.info(f"消息已发送 - 主题: {topic}, 内容: {message}")
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
        else:
            logger.error("MQTT未连接，无法发送消息")
            return False
    
    def send_sa_command(self, command):
        """发送SA指令"""
        return self.send_message(MQTT_CONFIG['sa_topic'], command)
    
    def send_gesture_switch_command(self, command):
        """发送手势模式切换指令"""
        return self.send_message(MQTT_CONFIG['gesture_switch_topic'], command)
    
    def send_esp32_control_command(self, command):
        """发送ESP32控制指令"""
        return self.send_message(MQTT_CONFIG['hardware_control_topic'], command)
    
    def stop(self):
        """停止MQTT客户端"""
        if self.is_connected:
            self.client.disconnect()
        self.quit()
        self.wait() 