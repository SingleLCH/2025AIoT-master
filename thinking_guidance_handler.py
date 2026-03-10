# -*- coding: utf-8 -*-
"""
思路解答流程处理器
复用拍照搜题的逻辑，但专门用于提供解题思路指导
"""

import os
import json
import logging
import subprocess
import sys
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from camera_handler import CameraHandler
from database_handler import DatabaseHandler
from mqtt_handler import MQTTHandler
from config import MQTT_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThinkingGuidanceHandler(QObject):
    """思路解答流程处理器"""
    
    # 信号定义
    process_started = pyqtSignal(str)  # 流程开始信号 (mode: 'thinking_guidance')
    face_recognition_completed = pyqtSignal(dict)  # 人脸识别完成信号
    face_recognition_failed = pyqtSignal()  # 人脸识别失败信号
    photo_capture_completed = pyqtSignal(bool)  # 拍照完成信号
    upload_started = pyqtSignal()  # 开始上传分析信号
    upload_completed = pyqtSignal(dict)  # 上传完成信号
    database_saved = pyqtSignal(bool)  # 数据库保存完成信号
    process_completed = pyqtSignal(dict)  # 整个流程完成信号
    back_requested = pyqtSignal()  # 返回请求信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self):
        super().__init__()
        
        # 状态控制
        self.is_processing = False
        self.waiting_for_photo_signal = False
        self.current_mode = None
        self.current_stage = None  # 当前阶段
        
        # 人脸识别相关
        self.student_info = None
        self.face_recognition_attempted = False
        
        # 摄像头处理器
        self.camera_handler = None
        self.mqtt_handler = None
        self.database_handler = None
        
        # 预览组件
        self.face_preview_widget = None
        self.photo_preview_widget = None
        self.current_preview_widget = None
        
        # 上传结果
        self.upload_result = None
        
        logger.info("思路解答处理器初始化完成")
    
    def set_camera_handler(self, camera_handler: CameraHandler):
        """设置摄像头处理器"""
        self.camera_handler = camera_handler
        if self.camera_handler:
            # 连接摄像头信号（使用正确的信号名称）
            self.camera_handler.photo_captured.connect(self._on_photo_captured)
            self.camera_handler.face_recognition_result.connect(self._on_face_recognition_result)
            self.camera_handler.error_occurred.connect(self._on_camera_error)
            self.camera_handler.preview_ready.connect(self._on_preview_ready)
            logger.info("摄像头处理器已设置并连接信号")
    
    def set_mqtt_handler(self, mqtt_handler: MQTTHandler):
        """设置MQTT处理器"""
        self.mqtt_handler = mqtt_handler
        logger.info("MQTT处理器已设置")
    
    def set_database_handler(self, database_handler: DatabaseHandler):
        """设置数据库处理器"""
        self.database_handler = database_handler
        logger.info("数据库处理器已设置")
    
    def start_school_mode_process(self):
        """开始学校模式思路解答流程（需要人脸识别）"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始学校模式思路解答流程")
        self.current_mode = 'school'
        self.is_processing = True
        self.student_info = None
        self.upload_result = None
        self.face_recognition_attempted = False
        
        self.process_started.emit('school')
        
        # 等待界面准备完成后开始流程
        self._wait_for_photo_signal()
        
        # 延迟启用MQTT响应
        QTimer.singleShot(1000, self._enable_mqtt_response)
    
    def start_home_mode_process(self):
        """开始家庭模式思路解答流程（直接拍照）"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始家庭模式思路解答流程")
        self.current_mode = 'home'
        self.is_processing = True
        self.student_info = None
        self.upload_result = None
        
        self.process_started.emit('home')
        
        # 直接开始等待拍照信号
        self._wait_for_photo_signal()
        
        # 延迟启用MQTT响应
        QTimer.singleShot(1000, self._enable_mqtt_response)
    
    def start_thinking_guidance_process(self):
        """开始思路解答流程（为了兼容性保留，实际应使用对应模式的方法）"""
        logger.warning("使用了过时的start_thinking_guidance_process方法，建议使用start_home_mode_process或start_school_mode_process")
        # 默认使用家庭模式
        self.start_home_mode_process()
    
    def _enable_mqtt_response(self):
        """启用MQTT响应（延迟启动以避免初始化时的意外触发）"""
        # 这里不需要设置mqtt_ready标志，因为_on_mqtt_command中已经检查is_processing
        logger.info("MQTT响应已启用，现在可以接收控制指令")
    
    def _start_face_recognition(self):
        """开始人脸识别"""
        try:
            if not self.camera_handler:
                self.error_occurred.emit("摄像头处理器未设置")
                return
            
            logger.info("开始人脸识别...")
            self.current_stage = 'face_recognition'
            self.face_recognition_attempted = True
            
            # 启动人脸识别流程
            result = self.camera_handler.capture_face_for_recognition()
            
            if result is None:
                logger.warning("人脸识别启动失败")
                self.face_recognition_failed.emit()
                
        except Exception as e:
            logger.error(f"人脸识别启动失败: {e}")
            self.error_occurred.emit(f"人脸识别启动失败: {e}")
            self._reset_process()
    
    def _on_face_recognition_result(self, result: dict):
        """处理人脸识别结果"""
        if not result.get('success', False):
            logger.warning("人脸识别失败")
            self.face_recognition_failed.emit()
            
            # 即使人脸识别失败，也可以继续使用默认信息
            self.student_info = {
                'name': '未识别用户',
                'student_id': 'unknown',
                'confidence': 0.0
            }
            
            # 继续后续流程
            self.current_stage = 'ready_for_photo'
            logger.info("人脸识别失败，使用默认信息继续流程")
            return
        
        # 🔧 修复：使用正确的字段名
        best_match = result.get('best_match', '')
        if not best_match:
            logger.error("人脸识别结果中缺少best_match信息")
            self.face_recognition_failed.emit()
            self.current_stage = 'ready_for_photo'
            return
        
        # 从best_match中提取姓名（去掉.jpg扩展名）
        student_name = best_match.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
        
        # 保存学生信息
        self.student_info = {
            'name': student_name,
            'best_match': best_match,
            'similarity': result.get('best_similarity', 0.0),
            'distance': result.get('best_distance', 1.0),
            'confidence': result.get('best_similarity', 0.0)  # 使用相似度作为置信度
        }
        
        logger.info(f"人脸识别成功: {self.student_info['name']}")
        self.face_recognition_completed.emit(self.student_info)
        
        # 人脸识别完成后，准备拍照
        self.current_stage = 'ready_for_photo'
        logger.info("人脸识别完成，准备进入拍照阶段")
        
        # 切换到作业拍照阶段
        self.current_stage = 'photo_homework'
        
        # 等待拍照指令
        self._wait_for_photo_signal()
    
    def _wait_for_photo_signal(self):
        """等待拍照MQTT信号"""
        if self.current_mode == 'school' and self.current_stage is None:
            # 学校模式：等待人脸识别拍照信号
            self.current_stage = 'face_recognition'
            logger.info("等待人脸识别拍照信号...")
        elif self.current_mode == 'home' or self.current_stage == 'photo_homework':
            # 家庭模式或学校模式的拍照阶段：等待作业拍照信号
            self.current_stage = 'photo_homework'
            logger.info("等待作业拍照信号...")
            
            # 发送8-1-0指令，表示进入拍摄作业阶段
            if self.mqtt_handler:
                logger.info("进入拍摄作业阶段，发送MQTT指令8-1-0...")
                self.mqtt_handler.send_esp32_control_command("8-1-0")
            
            # 清除旧照片
            if self.camera_handler:
                self.camera_handler.clear_photos()
        
        self.waiting_for_photo_signal = True
    
    def _on_mqtt_command(self, command: str):
        """处理MQTT指令"""
        logger.info(f"收到MQTT指令: {command} (当前阶段: {self.current_stage})")
        
        if not self.is_processing:
            logger.info(f"系统未在处理流程中，忽略MQTT指令: {command}")
            return
        
        if self.waiting_for_photo_signal and command == 'confirm':
            # 收到拍照确认信号
            self.waiting_for_photo_signal = False
            
            if self.current_stage == 'face_recognition':
                # 人脸识别拍照 - 设置已尝试标志
                self.face_recognition_attempted = True
                logger.info("开始执行人脸识别拍照...")
                self._start_face_recognition()
            elif self.current_stage == 'photo_homework':
                # 作业拍照：先发送8-2-0，然后再拍摄
                if self.mqtt_handler:
                    logger.info("接收到拍摄作业指令，发送MQTT指令8-2-0...")
                    self.mqtt_handler.send_esp32_control_command("8-2-0")
                
                logger.info("开始执行作业拍照...")
                self._start_photo_capture()
                
        elif command == 'back':
            # 收到返回信号，无论在什么状态都可以返回
            logger.info("收到返回信号，取消当前流程")
            if self.is_processing:
                self._reset_process()
                self.back_requested.emit()  # 发送返回信号，让界面处理
            else:
                logger.info("当前没有正在处理的流程，直接发送返回信号")
                self.back_requested.emit()
        else:
            logger.info(f"未识别的MQTT指令: {command}")
    
    def _start_photo_capture(self):
        """开始拍照"""
        try:
            logger.info(f"开始拍照... 当前阶段: {self.current_stage}")
            
            if not self.camera_handler:
                self.error_occurred.emit("摄像头处理器未设置")
                return
            
            # 检查拍照摄像头状态
            logger.info(f"拍照摄像头就绪状态: {self.camera_handler.is_photo_camera_ready()}")
            logger.info(f"拍照摄像头索引: {self.camera_handler.photo_camera_index}")
            
            # 确保拍照摄像头可用
            if not self.camera_handler.is_photo_camera_ready():
                error_msg = "拍照摄像头未就绪，无法进行拍照"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                self._reset_process()
                return
            
            success = self.camera_handler.capture_single_photo()
            logger.info(f"拍照方法直接返回结果: {success}")
            # 结果也会通过信号返回到 _on_photo_captured
            
        except Exception as e:
            logger.error(f"拍照失败: {e}")
            import traceback
            logger.error(f"拍照失败详细信息: {traceback.format_exc()}")
            self.error_occurred.emit(f"拍照失败: {e}")
            self._reset_process()
    
    def _on_photo_captured(self, success: bool):
        """处理拍照结果"""
        logger.info(f"拍照完成，成功: {success}")
        
        if not success:
            self.error_occurred.emit("拍照失败，请重试")
            self._reset_process()
            return
        
        self.photo_capture_completed.emit(True)
        
        if self.current_stage == 'photo_homework':
            # 作业拍照完成，发送MQTT指令8-0-2
            logger.info("作业拍照完成，发送MQTT指令8-0-2...")
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-0-2")
            
            # 延迟启动上传和分析，让UI有时间更新拍照完成的状态
            logger.info("拍照完成，等待UI更新后开始上传和分析...")
            QTimer.singleShot(500, self._start_upload_and_analysis)
    
    def _on_camera_error(self, error_msg: str):
        """处理摄像头错误"""
        logger.error(f"摄像头错误: {error_msg}")
        self.error_occurred.emit(f"摄像头错误: {error_msg}")
        self._reset_process()

    def _on_preview_ready(self, camera_type: str, camera_object):
        """处理预览就绪信号"""
        try:
            logger.info(f"预览就绪: {camera_type}")
            
            # 这里可以根据需要设置预览
            if camera_type == "face" and self.face_preview_widget:
                # 设置人脸识别预览
                pass
            elif camera_type == "photo" and self.photo_preview_widget:
                # 设置拍照预览
                pass
                
        except Exception as e:
            logger.error(f"处理预览就绪信号失败: {e}")

    def set_preview_widgets(self, face_widget=None, photo_widget=None):
        """设置预览组件"""
        if face_widget:
            self.face_preview_widget = face_widget
            logger.info("已设置人脸识别预览组件")
            
        if photo_widget:
            self.photo_preview_widget = photo_widget
            logger.info("已设置拍照预览组件")

    def set_current_preview_widget(self, preview_widget):
        """设置当前预览组件"""
        self.current_preview_widget = preview_widget
        logger.info("已设置当前预览组件")

    def _start_upload_and_analysis(self):
        """开始上传和分析"""
        try:
            logger.info("开始上传和思路分析...")
            
            # 发送开始上传分析信号，让界面更新流程状态
            self.upload_started.emit()
            
            # 检查是否有照片
            photo_count = self.camera_handler.get_photo_count()
            if photo_count == 0:
                self.error_occurred.emit("没有找到可上传的照片")
                self._reset_process()
                return
            
            # 调用思路解答专用的上传脚本
            result = self._call_thinking_guidance_upload_script()
            
            if result:
                self.upload_result = result
                self.upload_completed.emit(result)
                
                # 保存到数据库
                self._save_to_database()
            else:
                self.error_occurred.emit("思路分析失败")
                self._reset_process()
                
        except Exception as e:
            logger.error(f"上传分析失败: {e}")
            self.error_occurred.emit(f"上传分析失败: {e}")
            self._reset_process()
    
    def _call_thinking_guidance_upload_script(self) -> Optional[Dict[str, Any]]:
        """调用思路解答专用上传脚本"""
        try:
            # 运行thinking_guidance_upload.py脚本
            result = subprocess.run([sys.executable, 'thinking_guidance_upload.py'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"thinking_guidance_upload.py执行失败: {result.stderr}")
                return None
            
            # 尝试读取结果文件
            upload_result = None
            analysis_content = None
            
            if os.path.exists('result.json'):
                with open('result.json', 'r', encoding='utf-8') as f:
                    upload_result = json.load(f)
                logger.info(f"思路解答结果: {upload_result}")
            else:
                logger.error("未找到结果文件 result.json")
                return None
            
            # 尝试读取完整分析内容
            if os.path.exists('analysis.json'):
                with open('analysis.json', 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                    analysis_content = analysis_data.get('full_analysis', '')
                logger.info("成功读取完整分析内容")
            else:
                logger.warning("未找到分析文件 analysis.json")
                analysis_content = "暂无详细分析内容"
            
            # 合并结果
            result_data = upload_result.copy()
            result_data['analysis_content'] = analysis_content
            
            return result_data
                
        except subprocess.TimeoutExpired:
            logger.error("thinking_guidance_upload.py执行超时")
            return None
        except Exception as e:
            logger.error(f"调用thinking_guidance_upload.py失败: {e}")
            return None
    
    def _save_to_database(self):
        """跳过数据库保存，直接完成流程"""
        try:
            # 思路解答功能不需要保存到数据库，直接完成流程
            logger.info("思路解答功能跳过数据库保存")
            self.database_saved.emit(True)
            
            # 完成整个流程
            self._complete_process()
            
        except Exception as e:
            logger.error(f"完成流程时出错: {e}")
            self.database_saved.emit(False)
            self._complete_process()

    def _complete_process(self):
        """完成整个流程"""
        try:
            # 构建完整的结果信息
            result_data = {
                'mode': self.current_mode,
                'student_info': self.student_info,
                'upload_result': self.upload_result,
                'success': True
            }
            
            logger.info(f"思路解答流程完成: {result_data}")
            self.process_completed.emit(result_data)
            
            # 重置状态
            self._reset_process()
            
        except Exception as e:
            logger.error(f"完成流程时出错: {e}")
            self.error_occurred.emit(f"完成流程时出错: {e}")
            self._reset_process()
    
    def _reset_process(self):
        """重置流程状态"""
        self.is_processing = False
        self.waiting_for_photo_signal = False
        self.current_mode = None
        self.current_stage = None
        self.student_info = None
        self.upload_result = None
        self.face_recognition_attempted = False  # 重置人脸识别状态
        
        logger.info("思路解答流程状态已重置")
    
    def get_analysis_content(self) -> Optional[str]:
        """获取思路解答内容"""
        try:
            if self.upload_result:
                # 从结果中提取思路解答内容
                thinking_process = self.upload_result.get('thinking_process', '')
                key_points = self.upload_result.get('key_points', [])
                tips = self.upload_result.get('tips', [])
                
                content = f"解题思路:\n{thinking_process}\n\n"
                if key_points:
                    content += "关键步骤:\n" + "\n".join(f"• {point}" for point in key_points) + "\n\n"
                if tips:
                    content += "解题提示:\n" + "\n".join(f"• {tip}" for tip in tips)
                
                return content
            return None
        except Exception as e:
            logger.error(f"获取思路内容失败: {e}")
            return None
    
    def stop(self):
        """停止处理器"""
        try:
            logger.info("停止思路解答处理器...")
            self._reset_process()
            
            # 断开信号连接
            if self.camera_handler:
                try:
                    self.camera_handler.photo_captured.disconnect(self._on_photo_captured)
                    self.camera_handler.face_recognition_result.disconnect(self._on_face_recognition_result)
                    self.camera_handler.error_occurred.disconnect(self._on_camera_error)
                    self.camera_handler.preview_ready.disconnect(self._on_preview_ready)
                except:
                    pass  # 忽略断开连接的错误
            
            logger.info("思路解答处理器已停止")
            
        except Exception as e:
            logger.error(f"停止思路解答处理器失败: {e}")