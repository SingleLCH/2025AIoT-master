# -*- coding: utf-8 -*-
"""
图书管理处理器
用于管理图书借阅登记的功能
实现逻辑：先进行人脸识别确认身份，然后拍摄图书页面，AI识别图书名称，最后保存到数据库
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from camera_handler import CameraHandler
from database_handler import DatabaseHandler
from book_recognition_thread import BookRecognitionThread

logger = logging.getLogger(__name__)


class BookManagementHandler(QObject):
    """图书管理处理器"""
    
    # 信号定义
    process_started = pyqtSignal(str)  # 流程开始信号
    face_recognition_started = pyqtSignal()  # 人脸识别开始信号
    face_recognition_completed = pyqtSignal(dict)  # 人脸识别完成信号
    face_recognition_failed = pyqtSignal()  # 人脸识别失败信号
    photo_capture_completed = pyqtSignal()  # 拍照完成信号
    analysis_started = pyqtSignal()  # AI分析开始信号
    analysis_progress = pyqtSignal(str)  # AI分析进度信号
    analysis_completed = pyqtSignal(str)  # AI分析完成信号，传递图书名称
    upload_completed = pyqtSignal(dict)  # 上传完成信号，传递结果
    error_occurred = pyqtSignal(str)  # 错误信号
    back_requested = pyqtSignal()  # 返回功能选择页面信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状态控制
        self.is_processing = False
        self.mqtt_ready = False
        self.current_stage = None  # 当前阶段: 'face_recognition', 'photo_book', 'uploading'
        
        # 拍照相关
        self.camera_handler = None
        self.photo_folder = "book_photos"
        self.current_photo_path = None
        
        # 人脸识别结果
        self.student_info = None
        
        # 图书识别结果
        self.book_name = None
        
        # 数据库处理
        self.database_handler = None
        
        # AI分析线程
        self.recognition_thread = None
        
        # 🔧 复用作业批改逻辑：添加人脸预览组件引用（用于释放摄像头资源）
        self.face_preview_widget = None
        
        # 🔧 复用作业批改逻辑：初始化MQTT处理器用于发送8-2-0等指令
        from mqtt_handler import MQTTHandler
        self.mqtt_handler = MQTTHandler()
        
        # 确保照片文件夹存在
        self._ensure_photo_folder()
        
        logger.info("图书管理处理器初始化完成")
    
    def _ensure_photo_folder(self):
        """确保照片文件夹存在"""
        if not os.path.exists(self.photo_folder):
            os.makedirs(self.photo_folder)
            logger.info(f"创建图书照片文件夹: {self.photo_folder}")
    
    def set_camera_handler(self, camera_handler: CameraHandler):
        """设置摄像头处理器"""
        self.camera_handler = camera_handler
        # 🔧 移除旧的信号连接方式，改用直接调用方式（复用作业批改逻辑）
        logger.info("设置摄像头处理器")
    
    def set_face_preview_widget(self, face_preview_widget):
        """🔧 复用作业批改逻辑：设置人脸预览组件（用于释放摄像头资源）"""
        self.face_preview_widget = face_preview_widget
        logger.info("设置人脸预览组件")
    
    def start_book_management_process(self):
        """开始图书管理流程"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始图书管理流程")
        self.is_processing = True
        self.current_stage = 'face_recognition'
        self.student_info = None
        self.book_name = None
        self.current_photo_path = None
        
        # 清理之前的照片
        self._clear_photos()
        
        # 启用MQTT响应
        self.mqtt_ready = True
        
        # 发出流程开始信号
        self.process_started.emit('book_management')
        
        # 等待6-0-1信号开始人脸识别
        self._wait_for_face_recognition_signal()
        
        logger.info("图书管理流程已启动，等待6-0-1信号开始人脸识别")
    
    def _wait_for_face_recognition_signal(self):
        """等待人脸识别信号"""
        self.current_stage = 'waiting_face_recognition'
        logger.info("等待6-0-1信号开始人脸识别...")
    
    def _clear_photos(self):
        """清理照片文件夹中的所有图片"""
        try:
            import glob
            # 清理各种格式的图片文件
            image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
            cleared_count = 0
            
            for ext in image_extensions:
                files = glob.glob(os.path.join(self.photo_folder, ext))
                for file_path in files:
                    try:
                        os.remove(file_path)
                        cleared_count += 1
                        logger.debug(f"删除照片: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.warning(f"删除照片失败 {file_path}: {e}")
            
            if cleared_count > 0:
                logger.info(f"已清理 {cleared_count} 张照片")
            else:
                logger.info("照片文件夹已为空")
                
        except Exception as e:
            logger.error(f"清理照片文件夹失败: {e}")
    
    def _start_face_recognition(self):
        """🔧 复用作业批改逻辑：开始人脸识别"""
        try:
            logger.info("开始人脸识别...")
            # 发出人脸识别开始信号
            self.face_recognition_started.emit()
            
            if not self.camera_handler:
                self.error_occurred.emit("摄像头未初始化")
                return
            
            # 🔧 复用作业批改逻辑：直接调用摄像头处理器的人脸识别功能
            result = self.camera_handler.capture_face_for_recognition()
            # 直接处理结果
            if result:
                self._on_face_recognition_result(result)
            else:
                logger.error("人脸识别返回空结果")
                self.face_recognition_failed.emit()
                self._reset_process()
            
        except Exception as e:
            logger.error(f"人脸识别失败: {e}")
            self.error_occurred.emit(f"人脸识别失败: {e}")
            self._reset_process()
    
    def _on_face_recognition_result(self, result: dict):
        """🔧 复用作业批改逻辑：处理人脸识别结果"""
        if not result.get('success', False):
            logger.warning("人脸识别失败")
            self.face_recognition_failed.emit()
            self._reset_process()
            return
        
        # 🔧 复用作业批改逻辑：使用正确的字段名
        # 人脸识别结果中使用的是best_match字段，不是name字段
        best_match = result.get('best_match', '')
        if not best_match:
            logger.error("人脸识别结果中缺少best_match信息")
            self.face_recognition_failed.emit()
            self._reset_process()
            return
        
        # 从best_match中提取姓名（去掉文件扩展名）
        student_name = best_match.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
        
        # 保存学生信息
        self.student_info = {
            'name': student_name,
            'best_match': best_match,
            'similarity': result.get('best_similarity', 0.0),
            'distance': result.get('best_distance', 1.0),
            'confidence': result.get('best_similarity', 0.0)
        }
        
        logger.info(f"人脸识别成功: {self.student_info['name']}")
        self.face_recognition_completed.emit(self.student_info)
        
        # 🔧 复用作业批改逻辑：人脸识别完成后立即释放人脸摄像头资源
        logger.info("人脸识别完成，立即释放人脸摄像头资源...")
        self._release_face_camera_after_recognition()
        
        # 切换到图书拍照阶段，等待6-0-1指令
        self.current_stage = 'photo_book'
        logger.info("人脸识别完成，等待6-0-1指令拍摄图书")
    
    def _release_face_camera_after_recognition(self):
        """🔧 复用作业批改逻辑：人脸识别完成后释放人脸摄像头资源并确保拍照摄像头可用"""
        try:
            if self.camera_handler and self.camera_handler.face_camera and self.camera_handler.face_camera != "SIMULATED_CAMERA":
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
                
            # 🔧 确保拍照摄像头可用
            self._ensure_photo_camera_ready()
                
        except Exception as e:
            logger.error(f"释放人脸摄像头资源失败: {e}")
    
    def _ensure_photo_camera_ready(self):
        """确保拍照摄像头处于可用状态"""
        try:
            if not self.camera_handler:
                logger.error("摄像头处理器未初始化")
                return False
                
            photo_camera = self.camera_handler.get_photo_camera()
            
            # 检查拍照摄像头状态
            if photo_camera == "SIMULATED_CAMERA":
                logger.info("✅ 拍照摄像头为模拟模式，已就绪")
                return True
            elif photo_camera and hasattr(photo_camera, 'isOpened') and photo_camera.isOpened():
                logger.info("✅ 拍照摄像头已就绪")
                return True
            else:
                logger.warning("⚠️  拍照摄像头未就绪，尝试重新初始化...")
                
                # 使用摄像头处理器的重新初始化方法
                if hasattr(self.camera_handler, '_release_camera_if_needed'):
                    success = self.camera_handler._release_camera_if_needed("photo")
                    if success:
                        logger.info("✅ 拍照摄像头重新初始化成功")
                        return True
                    else:
                        logger.error("❌ 拍照摄像头重新初始化失败")
                        return False
                else:
                    logger.error("❌ 摄像头处理器缺少_release_camera_if_needed方法")
                    return False
                    
        except Exception as e:
            logger.error(f"检查拍照摄像头状态失败: {e}")
            return False
    
    def handle_mqtt_command(self, command: str):
        """处理MQTT控制指令"""
        logger.info(f"图书管理处理器收到MQTT指令: {command} (当前阶段: {self.current_stage}, is_processing: {self.is_processing})")
        
        # 6-0-2（返回）指令始终处理，无论流程状态如何
        if command == '6-0-2':
            logger.info("处理返回指令（优先处理）")
            self._handle_back_command()
            return
        
        # 其他指令只有在流程启动且MQTT响应启用后才处理
        if not self.mqtt_ready or not self.is_processing:
            logger.info(f"MQTT响应未启用或流程未启动，忽略指令: {command}")
            return
        
        if command == '6-0-1':
            # 拍照指令或人脸识别指令
            self._handle_photo_command()
        else:
            logger.info(f"未识别的MQTT指令: {command}")
    
    def _handle_photo_command(self):
        """处理拍照指令"""
        if self.current_stage == 'waiting_face_recognition':
            # 等待人脸识别阶段，开始人脸识别
            logger.info("收到6-0-1信号，开始人脸识别")
            self._start_face_recognition()
        elif self.current_stage == 'photo_book':
            # 图书拍照阶段
            self._capture_book_photo()
        else:
            logger.warning(f"当前阶段 {self.current_stage} 不支持拍照或人脸识别")
    
    def _capture_book_photo(self):
        """拍摄图书照片"""
        logger.info("开始拍摄图书照片...")
        
        try:
            if not self.camera_handler:
                self.error_occurred.emit("摄像头未初始化")
                return
            
            # 获取拍照摄像头
            photo_camera = self.camera_handler.get_photo_camera()
            if not photo_camera:
                self.error_occurred.emit("拍照摄像头未就绪")
                return
            
            # 生成照片文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            photo_filename = f"book_{timestamp}.png"
            photo_path = os.path.join(self.photo_folder, photo_filename)
            
            # 拍照
            success = self._capture_photo(photo_camera, photo_path)
            
            if success:
                self.current_photo_path = photo_path
                self.current_stage = 'uploading'
                logger.info(f"图书拍照成功: {photo_filename}")
                
                # 🔧 复用作业批改逻辑：拍照成功后发送8-0-2 MQTT指令
                if hasattr(self, 'mqtt_handler') and self.mqtt_handler:
                    logger.info("图书拍照完成，发送MQTT指令8-0-2...")
                    self.mqtt_handler.send_esp32_control_command("8-0-2")
                
                self.photo_capture_completed.emit()
                
                # 自动开始AI识别
                self._start_book_recognition()
            else:
                self.error_occurred.emit("图书拍照失败")
                
        except Exception as e:
            logger.error(f"图书拍照过程出错: {e}")
            self.error_occurred.emit(f"图书拍照失败: {e}")
    
    def _capture_photo(self, camera, photo_path: str) -> bool:
        """拍照实现"""
        try:
            import cv2
            
            if camera == "SIMULATED_CAMERA":
                # 模拟摄像头，创建一个测试图片
                import numpy as np
                test_image = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(test_image, f"Book Photo", (400, 360), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(test_image, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                           (400, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.imwrite(photo_path, test_image)
                return True
            else:
                # 真实摄像头拍照
                if hasattr(camera, 'read'):
                    ret, frame = camera.read()
                    if ret and frame is not None:
                        cv2.imwrite(photo_path, frame)
                        return True
                    else:
                        logger.error("无法从摄像头读取图像")
                        return False
                else:
                    logger.error("摄像头对象不支持read方法")
                    return False
                    
        except Exception as e:
            logger.error(f"拍照实现失败: {e}")
            return False
    
    def _start_book_recognition(self):
        """启动图书识别AI分析"""
        try:
            logger.info("启动图书识别AI分析")
            
            # 🔧 在图片上传到AI进行识别时发送8-2-0信号
            if hasattr(self, 'mqtt_handler') and self.mqtt_handler:
                logger.info("开始AI图书识别，发送MQTT指令8-2-0...")
                self.mqtt_handler.send_esp32_control_command("8-2-0")
            
            # 如果之前的线程还在运行，先停止
            if self.recognition_thread and self.recognition_thread.isRunning():
                self.recognition_thread.stop_analysis()
                self.recognition_thread = None
            
            # 创建新的识别线程
            self.recognition_thread = BookRecognitionThread(self.current_photo_path)
            
            # 连接信号
            self.recognition_thread.analysis_started.connect(self._on_analysis_thread_started)
            self.recognition_thread.analysis_progress.connect(self._on_analysis_progress)
            self.recognition_thread.analysis_completed.connect(self._on_analysis_completed)
            self.recognition_thread.analysis_failed.connect(self._on_analysis_failed)
            
            # 启动线程
            self.recognition_thread.start()
            logger.info("图书识别AI分析线程已启动")
            
        except Exception as e:
            logger.error(f"启动图书识别AI分析线程失败: {e}")
            self.error_occurred.emit(f"启动识别失败: {e}")
    
    def _on_analysis_thread_started(self):
        """AI分析线程开始"""
        logger.info("图书识别AI分析线程已开始")
        self.analysis_started.emit()
    
    def _on_analysis_progress(self, progress_msg):
        """AI分析进度更新"""
        logger.info(f"图书识别进度: {progress_msg}")
        self.analysis_progress.emit(progress_msg)
    
    def _on_analysis_completed(self, book_name: str):
        """AI分析完成"""
        try:
            logger.info(f"图书识别完成: {book_name}")
            self.book_name = book_name
            self.analysis_completed.emit(book_name)
            
            # 保存到数据库
            self.analysis_progress.emit("正在保存到数据库...")
            self._save_to_database()
            
        except Exception as e:
            logger.error(f"处理图书识别结果失败: {e}")
            self.error_occurred.emit(f"处理识别结果失败: {e}")
    
    def _on_analysis_failed(self, error_msg):
        """AI分析失败"""
        logger.error(f"图书识别失败: {error_msg}")
        self.error_occurred.emit(f"图书识别失败: {error_msg}")
    
    def _save_to_database(self):
        """保存结果到数据库"""
        try:
            if not self.student_info or not self.book_name:
                self.error_occurred.emit("缺少学生信息或图书信息")
                return
            
            # 初始化数据库处理器
            if not self.database_handler:
                self.database_handler = DatabaseHandler()
            
            # 保存到图书管理数据库
            success = self._save_book_record()
            
            if success:
                logger.info("图书记录已保存到数据库")
                
                # 准备结果数据
                result_data = {
                    'student_name': self.student_info['name'],
                    'book_name': self.book_name,
                    'timestamp': datetime.now().isoformat()
                }
                
                # 发出完成信号
                self.upload_completed.emit(result_data)
                logger.info("图书管理流程完成")
            else:
                self.error_occurred.emit("保存图书记录到数据库失败")
                
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
            self.error_occurred.emit(f"保存数据库失败: {e}")
    
    def _save_book_record(self) -> bool:
        """保存图书记录到数据库"""
        try:
            cursor = self.database_handler.connection.cursor()
            
            # 使用book_management配置
            from config import DATABASE_TABLES
            config = DATABASE_TABLES['book_management']
            
            # 使用对应的数据库
            cursor.execute(f"USE {config['database']}")
            
            # 插入新记录
            insert_sql = f"""
            INSERT INTO {config['table']} (bookname, studentname, time)
            VALUES (%s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_sql, (self.book_name, self.student_info['name'], current_time))
            
            cursor.close()
            logger.info(f"图书记录已保存: 学生={self.student_info['name']}, 图书={self.book_name}")
            return True
            
        except Exception as e:
            logger.error(f"保存图书记录失败: {e}")
            return False
    
    def _handle_back_command(self):
        """处理返回指令"""
        logger.info("收到返回指令，重置流程并返回功能选择页面")
        self._reset_process()
        self.back_requested.emit()
    
    def _reset_process(self):
        """重置处理流程"""
        logger.info("重置图书管理流程")
        self.is_processing = False
        self.mqtt_ready = False
        self.current_stage = None
        self.student_info = None
        self.book_name = None
        self.current_photo_path = None
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理图书管理处理器资源")
        
        # 停止图书识别线程
        if self.recognition_thread and self.recognition_thread.isRunning():
            logger.info("停止图书识别线程")
            self.recognition_thread.stop_analysis()
            self.recognition_thread = None
        
        # 🔧 复用作业批改逻辑：清理MQTT处理器
        if hasattr(self, 'mqtt_handler') and self.mqtt_handler:
            logger.info("清理MQTT处理器")
            self.mqtt_handler.stop()  # 修复：使用stop()而不是close()
            self.mqtt_handler = None
        
        self._reset_process()
        
        if self.database_handler:
            self.database_handler.close()
            self.database_handler = None 