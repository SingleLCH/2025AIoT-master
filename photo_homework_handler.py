# -*- coding: utf-8 -*-
"""
拍照搜题流程处理器
整合摄像头、人脸识别、MQTT、上传和数据库功能
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


class PhotoHomeworkHandler(QObject):
    """拍照搜题流程处理器"""
    
    # 信号定义
    process_started = pyqtSignal(str)  # 流程开始信号 (mode: 'school'/'home')
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
        
        # 流程状态（一些标志位或状态）
        self.is_processing = False
        self.current_mode = None  # 'school' 或 'home'
        self.current_stage = None  # 'face_recognition' 或 'photo_homework'
        self.waiting_for_photo_signal = False
        self.face_recognition_attempted = False  # 避免重复人脸识别
        
        # 数据存储（用于存储的相关变量）
        self.student_info = None
        self.upload_result = None
        
        # 延迟启用MQTT响应，避免初始化时的意外触发
        self.mqtt_ready = False
        QTimer.singleShot(5000, self._enable_mqtt_response)  # 5秒延迟
        
        # 预览组件管理
        self.current_preview_widget = None
        self.face_preview_widget = None
        self.photo_preview_widget = None
        
        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        try:
            # 创建摄像头处理器
            self.camera_handler = CameraHandler()
            
            # 连接信号
            self.camera_handler.face_recognition_result.connect(self._on_face_recognition_result)
            self.camera_handler.photo_captured.connect(self._on_photo_captured)
            self.camera_handler.error_occurred.connect(self._on_camera_error)
            # 连接预览就绪信号
            self.camera_handler.preview_ready.connect(self._on_preview_ready)
            
            # 创建MQTT处理器
            self.mqtt_handler = MQTTHandler()
            self.mqtt_handler.control_command_received.connect(self._on_mqtt_command)
            self.mqtt_handler.start()
            
            # 初始化数据库处理器
            self.database_handler = DatabaseHandler()
            
            logger.info("拍照搜题处理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            self.error_occurred.emit(f"初始化组件失败: {e}")
    
    def _enable_mqtt_response(self):
        """启用MQTT响应（延迟启动以避免初始化时的意外触发）"""
        self.mqtt_ready = True
        logger.info("MQTT响应已启用，现在可以接收控制指令")
    
    def start_school_mode_process(self):
        """开始学校模式流程（需要人脸识别）"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始学校模式拍照搜题流程")
        self.current_mode = 'school'
        self.current_stage = None  # 🔧 重置阶段状态，确保从人脸识别开始
        self.is_processing = True
        self.student_info = None
        self.upload_result = None
        self.face_recognition_attempted = False  # 重置人脸识别状态
        self.waiting_for_photo_signal = False  # 🔧 重置等待信号状态
        
        self.process_started.emit('school')
        
        # 等待界面准备完成后开始流程
        self._wait_for_photo_signal()
    
    def start_home_mode_process(self):
        """开始家庭模式流程（直接拍照）"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始家庭模式拍照搜题流程")
        self.current_mode = 'home'
        self.current_stage = None  # 🔧 重置阶段状态
        self.is_processing = True
        self.student_info = None
        self.upload_result = None
        self.waiting_for_photo_signal = False  # 🔧 重置等待信号状态
        
        self.process_started.emit('home')
        
        # 直接开始等待拍照信号
        self._wait_for_photo_signal()
    
    def _start_face_recognition(self):
        """开始人脸识别"""
        try:
            logger.info("开始人脸识别...")
            result = self.camera_handler.capture_face_for_recognition()
            # 结果将通过信号返回到 _on_face_recognition_result
            
        except Exception as e:
            logger.error(f"人脸识别失败: {e}")
            self.error_occurred.emit(f"人脸识别失败: {e}")
            self._reset_process()
    
    def _on_face_recognition_result(self, result: dict):
        """处理人脸识别结果"""
        if not result.get('success', False):
            logger.warning("人脸识别失败")
            self.face_recognition_failed.emit()
            self._reset_process()
            return
        
        # 🔧 修复：使用正确的字段名
        # 人脸识别结果中使用的是best_match字段，不是name字段
        best_match = result.get('best_match', '')
        if not best_match:
            logger.error("人脸识别结果中缺少best_match信息")
            self.face_recognition_failed.emit()
            self._reset_process()
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
        
        # 🔧 关键修复：人脸识别完成后立即释放人脸摄像头资源
        logger.info("人脸识别完成，立即释放人脸摄像头资源...")
        self._release_face_camera_after_recognition()
        
        # 切换到作业拍照阶段
        self.current_stage = 'photo_homework'
        
        # 💡 增加延迟确保系统状态稳定后再开始等待拍照指令
        logger.info("人脸识别完成，等待系统状态稳定...")
        QTimer.singleShot(2000, self._delayed_wait_for_photo_signal)
    
    def _release_face_camera_after_recognition(self):
        """人脸识别完成后释放人脸摄像头资源"""
        try:
            if self.camera_handler.face_camera and self.camera_handler.face_camera != "SIMULATED_CAMERA":
                logger.info("正在释放人脸摄像头资源...")
                self.camera_handler.face_camera.release()
                self.camera_handler.face_camera = None
                logger.info("✅ 人脸摄像头资源已完全释放")
                
                # 停止人脸预览组件
                if self.face_preview_widget and hasattr(self.face_preview_widget, 'stop_preview'):
                    self.face_preview_widget.stop_preview()
                    logger.info("人脸预览组件已停止")
                    
            else:
                logger.info("人脸摄像头为模拟模式或已释放，无需额外处理")
                
        except Exception as e:
            logger.error(f"释放人脸摄像头资源失败: {e}")
    
    def _delayed_wait_for_photo_signal(self):
        """延迟等待拍照信号（确保系统状态稳定）"""
        logger.info("系统状态已稳定，开始等待拍照指令...")
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
            logger.info("进入拍摄作业阶段，发送MQTT指令8-1-0...")
            self.mqtt_handler.send_esp32_control_command("8-1-0")
            
            # 清除旧照片
            self.camera_handler.clear_photos()
        
        self.waiting_for_photo_signal = True
    
    def _on_mqtt_command(self, command: str):
        """处理MQTT控制指令"""
        logger.info(f"收到MQTT指令: {command} (当前阶段: {self.current_stage})")
        
        # 第一层安全检查：只有在MQTT响应启用后才处理指令
        if not self.mqtt_ready:
            logger.info(f"MQTT响应未启用，忽略指令: {command}")
            return
        
        # 第二层安全检查：只有在正在处理流程时才响应MQTT指令
        if not self.is_processing:
            logger.info(f"系统未在处理流程中，忽略MQTT指令: {command}")
            return
        
        # 第三层安全检查：验证当前阶段状态
        if self.current_stage is None:
            logger.warning(f"当前阶段状态为空，忽略MQTT指令: {command}")
            return
            
        # 第四层安全检查：防止重复操作
        if command == 'confirm':
            if self.current_stage == 'face_recognition' and self.face_recognition_attempted:
                logger.warning("人脸识别已经尝试过，忽略重复confirm指令")
                return
            if (self.current_stage == 'photo_homework' and 
                not self.waiting_for_photo_signal):
                logger.warning("当前不在等待confirm指令的状态，忽略指令")
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
                logger.info("接收到拍摄作业指令，发送MQTT指令8-2-0...")
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                
                logger.info("开始执行作业拍照...")
                self._start_photo_capture()
                
        # 已移除等待上传信号的处理逻辑，现在拍照完成后直接上传
            
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
            logger.warning(f"未处理的MQTT指令: {command} (当前状态不匹配或指令无效)")
    
    def _start_photo_capture(self):
        """开始拍照"""
        try:
            logger.info(f"开始拍照... 当前阶段: {self.current_stage}")
            
            # 🔧 修复：只检查拍照摄像头状态，因为人脸摄像头已在识别完成后释放
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
        """处理摄像头预览就绪信号"""
        logger.info(f"收到{camera_type}摄像头预览就绪信号")
        
        try:
            if camera_type == "face" and self.face_preview_widget:
                logger.info("更新人脸识别摄像头预览组件")
                self.face_preview_widget.set_camera(camera_object)
                if hasattr(self.face_preview_widget, 'start_preview'):
                    self.face_preview_widget.start_preview()
                    logger.info("人脸识别摄像头预览已重新启动")
                    
            elif camera_type == "photo" and self.photo_preview_widget:
                logger.info("更新拍照摄像头预览组件")
                self.photo_preview_widget.set_camera(camera_object)
                if hasattr(self.photo_preview_widget, 'start_preview'):
                    self.photo_preview_widget.start_preview()
                    logger.info("拍照摄像头预览已重新启动")
                    
            # 更新当前预览组件
            if self.current_preview_widget:
                if ((camera_type == "face" and self.current_preview_widget == self.face_preview_widget) or
                    (camera_type == "photo" and self.current_preview_widget == self.photo_preview_widget)):
                    self.current_preview_widget.set_camera(camera_object)
                    if hasattr(self.current_preview_widget, 'start_preview'):
                        self.current_preview_widget.start_preview()
                        logger.info(f"当前预览组件已更新为{camera_type}摄像头")
                        
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
            logger.info("开始上传和分析作业...")
            
            # 发送开始上传分析信号，让界面更新流程状态
            self.upload_started.emit()
            
            # 检查是否有照片
            photo_count = self.camera_handler.get_photo_count()
            if photo_count == 0:
                self.error_occurred.emit("没有找到可上传的照片")
                self._reset_process()
                return
            
            # 调用upload.py进行上传分析
            result = self._call_upload_script()
            
            if result:
                self.upload_result = result
                self.upload_completed.emit(result)
                
                # 保存到数据库
                self._save_to_database()
            else:
                self.error_occurred.emit("上传分析失败")
                self._reset_process()
                
        except Exception as e:
            logger.error(f"上传分析失败: {e}")
            self.error_occurred.emit(f"上传分析失败: {e}")
            self._reset_process()
    
    def _call_upload_script(self) -> Optional[Dict[str, Any]]:
        """调用upload.py脚本进行上传分析"""
        try:
            # 运行upload.py脚本
            result = subprocess.run([sys.executable, 'upload.py'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"upload.py执行失败: {result.stderr}")
                return None
            
            # 尝试读取结果文件
            upload_result = None
            analysis_content = None
            
            if os.path.exists('result.json'):
                with open('result.json', 'r', encoding='utf-8') as f:
                    upload_result = json.load(f)
                logger.info(f"上传分析结果: {upload_result}")
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
            logger.error("upload.py执行超时")
            return None
        except Exception as e:
            logger.error(f"调用upload.py失败: {e}")
            return None
    
    def _save_to_database(self):
        """保存结果到数据库"""
        if not self.upload_result:
            self.error_occurred.emit("没有上传结果可保存")
            self._reset_process()
            return
        
        try:
            error_numbers = self.upload_result.get('error_numbers', [])
            weak_areas = self.upload_result.get('weak_areas', [])
            
            if self.current_mode == 'school':
                # 学校模式：保存到student表
                if not self.student_info:
                    self.error_occurred.emit("缺少学生信息")
                    self._reset_process()
                    return
                
                success = self.database_handler.save_school_result(
                    student_name=self.student_info['name'],
                    weak_areas=weak_areas
                )
            
            elif self.current_mode == 'home':
                # 家庭模式：保存到error_details表
                success = self.database_handler.save_home_result(
                    error_numbers=error_numbers,
                    weak_areas=weak_areas
                )
            
            else:
                self.error_occurred.emit("未知的模式")
                self._reset_process()
                return
            
            if success:
                logger.info("数据库保存成功")
                self.database_saved.emit(True)
                self._complete_process()
            else:
                self.error_occurred.emit("数据库保存失败")
                self._reset_process()
                
        except Exception as e:
            logger.error(f"保存数据库失败: {e}")
            self.error_occurred.emit(f"保存数据库失败: {e}")
            self._reset_process()
    
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
            
            logger.info(f"拍照搜题流程完成: {result_data}")
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
        
        logger.info("流程状态已重置")
    
    def get_analysis_content(self) -> Optional[str]:
        """获取解题分析内容（从upload.py的输出中提取）"""
        try:
            # 这里可以从upload.py的输出中提取思考过程
            # 目前返回一个示例，实际应该从上传结果中获取
            if self.upload_result:
                return "这里应该显示详细的解题分析过程..."
            return None
        except Exception as e:
            logger.error(f"获取分析内容失败: {e}")
            return None
    
    def stop(self):
        """停止处理器"""
        try:
            self._reset_process()
            
            if hasattr(self, 'camera_handler') and self.camera_handler:
                self.camera_handler.close_cameras()
            
            if hasattr(self, 'database_handler') and self.database_handler:
                self.database_handler.close()
                self.database_handler = None
            
            if hasattr(self, 'mqtt_handler') and self.mqtt_handler:
                self.mqtt_handler.stop()
            
            logger.info("拍照搜题处理器已停止")
            
        except Exception as e:
            logger.error(f"停止处理器失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop()
        except Exception as e:
            logger.warning(f"析构函数执行时出现异常: {e}") 