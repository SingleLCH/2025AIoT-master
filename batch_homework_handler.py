# -*- coding: utf-8 -*-
"""
批量批改处理器
用于老师批量批改作业的功能
复用现有拍照逻辑，但不需要人脸识别
"""

import os
import glob
import json
import logging
import shutil
import subprocess
from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from camera_handler import CameraHandler
from database_handler import DatabaseHandler
from config import DATABASE_TABLES
from batch_homework_analysis_thread import BatchHomeworkAnalysisThread

logger = logging.getLogger(__name__)


class BatchHomeworkHandler(QObject):
    """批量批改处理器"""
    
    # 信号定义
    process_started = pyqtSignal(str)  # 流程开始信号
    photo_captured = pyqtSignal()  # 拍照完成信号
    analysis_started = pyqtSignal()    # AI分析开始信号
    analysis_progress = pyqtSignal(str)  # AI分析进度信号
    upload_completed = pyqtSignal(dict)  # 上传完成信号，传递分析结果
    error_occurred = pyqtSignal(str)  # 错误信号
    back_requested = pyqtSignal()  # 返回功能选择页面信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状态控制
        self.is_processing = False
        self.mqtt_ready = False
        self.current_stage = None  # 当前阶段: 'waiting', 'photo_captured', 'uploading'
        
        # 拍照相关
        self.camera_handler = None
        self.photo_folder = "batch_homework_photos"
        self.photo_paths = []
        
        # 数据库处理
        self.database_handler = None
        
        # AI分析线程
        self.analysis_thread = None
        
        # 分析结果
        self.analysis_result = None
        
        # 确保照片文件夹存在
        self._ensure_photo_folder()
        
        logger.info("批量批改处理器初始化完成")
    
    def _ensure_photo_folder(self):
        """确保照片文件夹存在"""
        if not os.path.exists(self.photo_folder):
            os.makedirs(self.photo_folder)
            logger.info(f"创建批量批改照片文件夹: {self.photo_folder}")
    
    def set_camera_handler(self, camera_handler: CameraHandler):
        """设置摄像头处理器"""
        self.camera_handler = camera_handler
        logger.info("设置摄像头处理器")
    
    def start_batch_homework_process(self):
        """开始批量批改流程"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始批量批改流程")
        self.is_processing = True
        self.current_stage = 'waiting'
        self.analysis_result = None
        self.photo_paths = []
        
        # 清理照片文件夹
        self._clear_photos()
        
        # 启用MQTT响应
        self.mqtt_ready = True
        
        # 发出流程开始信号
        self.process_started.emit('batch_homework')
        
        logger.info("批量批改流程已启动，等待拍照指令 6-0-1")
    
    def _clear_photos(self):
        """清理照片文件夹中的所有图片"""
        try:
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
    
    def handle_mqtt_command(self, command: str):
        """处理MQTT控制指令"""
        logger.info(f"批量批改处理器收到MQTT指令: {command} (当前阶段: {self.current_stage})")
        
        # 只有在流程启动且MQTT响应启用后才处理指令
        if not self.mqtt_ready or not self.is_processing:
            logger.info(f"MQTT响应未启用或流程未启动，忽略指令: {command}")
            return
        
        if command == '6-0-1':
            # 拍照指令
            self._handle_photo_command()
        elif command == '6-0-2':
            # 返回功能选择页面指令
            self._handle_back_command()
        elif command == '6-0-3':
            # 上传指令
            self._handle_upload_command()
        else:
            logger.info(f"未识别的MQTT指令: {command}")
    
    def _handle_photo_command(self):
        """处理拍照指令"""
        if self.current_stage not in ['waiting', 'photo_captured']:
            logger.warning(f"当前阶段 {self.current_stage} 不支持拍照")
            return
        
        logger.info("开始拍照...")
        
        try:
            if not self.camera_handler:
                self.error_occurred.emit("摄像头未初始化")
                return
            
            # 复用现有的拍照逻辑，但不使用人脸识别
            photo_camera = self.camera_handler.get_photo_camera()
            if not photo_camera:
                self.error_occurred.emit("拍照摄像头未就绪")
                return
            
            # 生成照片文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            photo_filename = f"batch_homework_{timestamp}.png"
            photo_path = os.path.join(self.photo_folder, photo_filename)
            
            # 拍照（复用camera_handler的拍照逻辑）
            success = self._capture_photo(photo_camera, photo_path)
            
            if success:
                self.photo_paths.append(photo_path)
                self.current_stage = 'photo_captured'
                logger.info(f"拍照成功: {photo_filename}, 当前照片总数: {len(self.photo_paths)}")
                self.photo_captured.emit()
                logger.info("已发出photo_captured信号")
            else:
                self.error_occurred.emit("拍照失败")
                
        except Exception as e:
            logger.error(f"拍照过程出错: {e}")
            self.error_occurred.emit(f"拍照失败: {e}")
    
    def _capture_photo(self, camera, photo_path: str) -> bool:
        """拍照实现"""
        try:
            import cv2
            
            if camera == "SIMULATED_CAMERA":
                # 模拟摄像头，创建一个测试图片
                import numpy as np
                test_image = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(test_image, f"Batch Homework Photo", (400, 360), 
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
    
    def _handle_back_command(self):
        """处理返回指令"""
        logger.info("收到返回指令，重置流程并返回功能选择页面")
        self._reset_process()
        self.back_requested.emit()
    
    def _handle_upload_command(self):
        """处理上传指令"""
        logger.info(f"处理上传指令 - 当前阶段: {self.current_stage}, 照片数量: {len(self.photo_paths)}")
        
        # 放宽条件：只要有照片就可以上传，不限制阶段
        if not self.photo_paths:
            logger.error("没有可上传的照片")
            self.error_occurred.emit("没有可上传的照片")
            return
        
        logger.info(f"开始上传和分析 {len(self.photo_paths)} 张照片...")
        self.current_stage = 'uploading'
        
        # 先发出分析开始信号，更新UI
        self.analysis_started.emit()
        
        # 使用线程进行AI分析
        self._start_analysis_thread()
    
    def _start_analysis_thread(self):
        """启动AI分析线程"""
        try:
            logger.info("启动AI分析线程")
            
            # 如果之前的线程还在运行，先停止
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.stop_analysis()
                self.analysis_thread = None
            
            # 创建新的分析线程
            self.analysis_thread = BatchHomeworkAnalysisThread(self.photo_paths.copy())
            
            # 连接信号
            self.analysis_thread.analysis_started.connect(self._on_analysis_thread_started)
            self.analysis_thread.analysis_progress.connect(self._on_analysis_progress)
            self.analysis_thread.analysis_completed.connect(self._on_analysis_completed)
            self.analysis_thread.analysis_failed.connect(self._on_analysis_failed)
            
            # 启动线程
            self.analysis_thread.start()
            logger.info("AI分析线程已启动")
            
        except Exception as e:
            logger.error(f"启动AI分析线程失败: {e}")
            self.error_occurred.emit(f"启动分析失败: {e}")
    
    def _on_analysis_thread_started(self):
        """AI分析线程开始"""
        logger.info("AI分析线程已开始")
        self.analysis_progress.emit("正在连接AI服务...")
    
    def _on_analysis_progress(self, progress_msg):
        """AI分析进度更新"""
        logger.info(f"AI分析进度: {progress_msg}")
        self.analysis_progress.emit(progress_msg)
    
    def _on_analysis_completed(self, analysis_result):
        """AI分析完成"""
        try:
            logger.info("AI分析线程完成")
            self.analysis_result = analysis_result
            
            # 保存到数据库
            self.analysis_progress.emit("正在保存到数据库...")
            self._save_to_database()
            
            # 发出完成信号
            logger.info("准备发出upload_completed信号")
            self.upload_completed.emit(self.analysis_result)
            logger.info("批量分析完成，已发出upload_completed信号")
            
        except Exception as e:
            logger.error(f"处理AI分析结果失败: {e}")
            self.error_occurred.emit(f"处理分析结果失败: {e}")
    
    def _on_analysis_failed(self, error_msg):
        """AI分析失败"""
        logger.error(f"AI分析失败: {error_msg}")
        self.error_occurred.emit(f"AI分析失败: {error_msg}")
    
    def _find_latest_analysis_result(self) -> Optional[str]:
        """查找最新的分析结果文件"""
        try:
            pattern = "homework_analysis_result_*.json"
            result_files = glob.glob(pattern)
            
            if result_files:
                # 按修改时间排序，获取最新的文件
                latest_file = max(result_files, key=os.path.getmtime)
                return latest_file
            else:
                return None
                
        except Exception as e:
            logger.error(f"查找分析结果文件失败: {e}")
            return None
    
    def _save_to_database(self):
        """保存分析结果到数据库"""
        try:
            if not self.analysis_result:
                logger.warning("没有分析结果可保存")
                return
            
            # 初始化数据库处理器
            if not self.database_handler:
                self.database_handler = DatabaseHandler()
            
            # 提取分析结果的各个部分
            error_analysis = self.analysis_result.get('error_analysis', {})
            common_mistakes = error_analysis.get('common_mistakes', [])
            weak_points = error_analysis.get('class_weak_points', [])
            teaching_advice = self.analysis_result.get('ai_teaching_advice', {})
            
            # 转换为JSON字符串用于数据库存储
            analysis_json = json.dumps(self.analysis_result, ensure_ascii=False, indent=2)
            common_mistakes_json = json.dumps(common_mistakes, ensure_ascii=False)
            weak_points_json = json.dumps(weak_points, ensure_ascii=False)
            teaching_advice_json = json.dumps(teaching_advice, ensure_ascii=False)
            
            # 保存到批量批改专用数据库
            success = self._save_batch_homework_result(
                analysis_json, common_mistakes_json, weak_points_json, teaching_advice_json
            )
            
            if success:
                logger.info("分析结果已保存到数据库")
            else:
                logger.error("保存分析结果到数据库失败")
                
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
    
    def _save_batch_homework_result(self, analysis_result: str, common_mistakes: str, 
                                  weak_points: str, teaching_advice: str) -> bool:
        """保存批量批改结果到数据库"""
        try:
            cursor = self.database_handler.connection.cursor()
            config = DATABASE_TABLES['batch_homework']
            
            # 使用对应的数据库
            cursor.execute(f"USE {config['database']}")
            
            # 将所有分析结果合并到info字段中
            info_data = {
                'analysis_result': json.loads(analysis_result),
                'common_mistakes': json.loads(common_mistakes),
                'weak_points': json.loads(weak_points),
                'teaching_advice': json.loads(teaching_advice)
            }
            info_json = json.dumps(info_data, ensure_ascii=False, indent=2)
            
            # 插入新记录 - 只使用实际存在的字段：id, info, time
            insert_sql = f"""
            INSERT INTO {config['table']} (time, info)
            VALUES (%s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_sql, (current_time, info_json))
            
            cursor.close()
            logger.info("批量批改结果已保存到数据库")
            return True
            
        except Exception as e:
            logger.error(f"保存批量批改结果失败: {e}")
            return False
    
    def _reset_process(self):
        """重置处理流程"""
        logger.info("重置批量批改流程")
        self.is_processing = False
        self.mqtt_ready = False
        self.current_stage = None
        self.analysis_result = None
        self.photo_paths = []
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理批量批改处理器资源")
        
        # 停止AI分析线程
        if self.analysis_thread and self.analysis_thread.isRunning():
            logger.info("停止AI分析线程")
            self.analysis_thread.stop_analysis()
            self.analysis_thread = None
        
        self._reset_process()
        
        if self.database_handler:
            self.database_handler.close()
            self.database_handler = None 