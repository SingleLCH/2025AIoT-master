#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
姿势检测后台线程
定期拍照并检测用户姿势，提醒用户保持良好坐姿
"""

import os
import cv2
import time
import logging
import threading
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QMutex
from PyQt5.QtWidgets import QApplication

from pose_detector import HeadDownDetector
from camera_handler import CameraHandler
import config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoseDetectionThread(QThread):
    """姿势检测后台线程"""
    
    # 信号定义
    detection_completed = pyqtSignal(dict)  # 检测完成信号
    posture_alert = pyqtSignal(str, int)  # 姿势警告信号 (警告信息, 连续不良姿势次数)
    myopia_risk_alert = pyqtSignal(str, int)  # 近视风险警告信号 (警告信息, 连续近视风险次数)
    error_occurred = pyqtSignal(str)  # 错误信号
    status_changed = pyqtSignal(str)  # 状态变化信号
    latest_photo_ready = pyqtSignal(object, object)  # 最新照片准备信号（传递照片frame对象和时间戳）
    
    def __init__(self):
        super().__init__()
        
        # 检测器和摄像头处理器
        self.pose_detector = None
        self.camera_handler = None
        
        # 线程控制
        self.is_running = False
        self.is_paused = False
        self.mutex = QMutex()
        
        # 检测状态
        self.detection_count = 0
        self.consecutive_bad_posture = 0
        self.consecutive_myopia_risk = 0  # 连续近视风险次数
        self.last_detection_time = 0
        
        # 结果存储
        self.detection_results = []
        self.detection_folder = config.POSE_DETECTION_CONFIG['detection_folder']
        
        # 初始化
        self.init_components()
        self.ensure_detection_folder()
        
    def init_components(self):
        """初始化组件"""
        try:
            # 初始化姿势检测器
            self.pose_detector = HeadDownDetector()
            logger.info("姿势检测器初始化成功")
            
            # 初始化摄像头处理器
            try:
                self.camera_handler = CameraHandler()
                logger.info("摄像头处理器初始化成功")
            except Exception as camera_error:
                logger.warning(f"摄像头处理器初始化失败: {camera_error}")
                # 即使摄像头初始化失败，也继续运行（使用模拟模式）
                self.camera_handler = None
            
            self.status_changed.emit("组件初始化完成")
            
        except Exception as e:
            error_msg = f"初始化组件失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def ensure_detection_folder(self):
        """确保检测结果文件夹存在"""
        try:
            if not os.path.exists(self.detection_folder):
                os.makedirs(self.detection_folder)
                logger.info(f"创建检测结果文件夹: {self.detection_folder}")
        except Exception as e:
            logger.error(f"创建检测结果文件夹失败: {e}")
    
    def start_detection(self):
        """开始检测"""
        self.mutex.lock()
        try:
            if not self.is_running:
                self.is_running = True
                self.is_paused = False
                if not self.isRunning():
                    self.start()
                logger.info("姿势检测已开始")
                self.status_changed.emit("检测中...")
        finally:
            self.mutex.unlock()
    
    def pause_detection(self):
        """暂停检测"""
        self.mutex.lock()
        try:
            self.is_paused = True
            logger.info("姿势检测已暂停")
            self.status_changed.emit("已暂停")
        finally:
            self.mutex.unlock()
    
    def resume_detection(self):
        """恢复检测"""
        self.mutex.lock()
        try:
            self.is_paused = False
            logger.info("姿势检测已恢复")
            self.status_changed.emit("检测中...")
        finally:
            self.mutex.unlock()
    
    def stop_detection(self, close_cameras=True):
        """停止检测"""
        self.mutex.lock()
        try:
            self.is_running = False
            self.is_paused = False
            # 可选择是否关闭摄像头（避免与其他功能冲突）
            if close_cameras and self.camera_handler:
                self.camera_handler.close_cameras()
        finally:
            self.mutex.unlock()
        
        if self.isRunning():
            self.quit()
            self.wait(3000)  # 等待3秒
        
        logger.info("姿势检测已停止")
        self.status_changed.emit("已停止")
    
    def run(self):
        """线程主循环"""
        logger.info("姿势检测线程开始运行")
        
        while self.is_running:
            try:
                # 检查是否暂停
                if self.is_paused:
                    self.msleep(1000)  # 暂停时每秒检查一次
                    continue
                
                # 检查检测间隔
                current_time = time.time()
                detection_interval = config.POSE_DETECTION_CONFIG['detection_interval']
                time_since_last = current_time - self.last_detection_time
                
                if time_since_last < detection_interval:
                    # 计算剩余等待时间
                    remaining_time = detection_interval - time_since_last
                    sleep_time = min(remaining_time * 1000, 1000)  # 最多休眠1秒
                    self.msleep(int(sleep_time))
                    continue
                
                # 执行姿势检测
                print(f"[DEBUG] 开始执行姿势检测，距离上次检测: {time_since_last:.1f}秒")
                self.perform_detection()
                self.last_detection_time = current_time
                
                # 短暂休眠
                self.msleep(100)
                
            except Exception as e:
                error_msg = f"检测循环出错: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                self.msleep(1000)  # 出错后等待1秒再继续
        
        logger.info("姿势检测线程结束")
    
    def perform_detection(self):
        """执行一次姿势检测"""
        try:
            print(f"[DEBUG] perform_detection 开始")
            
            if not self.pose_detector:
                self.error_occurred.emit("姿势检测器未初始化")
                return
            
            # 获取摄像头
            camera = None
            if self.camera_handler:
                camera = self.camera_handler.get_face_camera()
            
            if camera is None:
                logger.warning("摄像头未准备就绪，使用模拟模式")
                camera = "SIMULATED_CAMERA"
            
            # 拍照
            print(f"[DEBUG] 开始拍照")
            frame = self.capture_frame(camera)
            if frame is None:
                print(f"[DEBUG] 拍照失败")
                self.error_occurred.emit("拍照失败")
                return
            
            print(f"[DEBUG] 拍照成功，帧尺寸: {frame.shape}")
            
            # 直接发送最新照片frame对象（不保存为文件）
            current_timestamp = datetime.now()
            print(f"[DEBUG] 发送照片frame对象")
            self.latest_photo_ready.emit(frame, current_timestamp)
            
            # 进行姿势检测（直接使用frame对象）
            print(f"[DEBUG] 开始姿势检测")
            try:
                detection_result = self.pose_detector.analyze_frame(
                    frame, 
                    config.CONFIDENCE_THRESHOLD
                )
                print(f"[DEBUG] 姿势检测完成")
            except Exception as detection_error:
                print(f"[ERROR] 姿势检测失败: {detection_error}")
                # 创建一个失败的检测结果
                detection_result = {
                    'image': frame,  # 使用原始帧
                    'detection': {
                        'valid': False,
                        'message': f"检测失败: {detection_error}",
                        'severity': '检测异常',
                        'is_head_down': False,
                        'head_down_ratio': 0.0,
                        'vertical_distance': 0.0,
                        'myopia_risk_level': '无法判断'
                    },
                    'keypoints': None
                }
            
            # 处理检测结果（传递frame对象而不是文件路径）
            self.process_detection_result(detection_result, frame)
            
        except Exception as e:
            error_msg = f"执行姿势检测失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def capture_frame(self, camera) -> Optional[object]:
        """从摄像头捕获一帧"""
        try:
            if camera == "SIMULATED_CAMERA":
                # 模拟模式：创建一个测试图像
                frame = self.create_simulated_frame()
                return frame
            elif hasattr(camera, 'read'):
                # ret, frame = camera.read()
                for _ in range(10):  # 读取多帧强制刷新缓冲
                    ret, frame = camera.read()
                if ret and frame is not None:
                    return frame
            
            return None
            
        except Exception as e:
            logger.error(f"捕获摄像头帧失败: {e}")
            return None
    
    def create_simulated_frame(self):
        """创建模拟帧（用于测试）"""
        import numpy as np
        
        # 创建一个包含简单人像的测试图像
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # 深灰色背景
        
        # 绘制一个简单的人体轮廓用于姿势检测
        # 头部（圆形）
        cv2.circle(frame, (320, 120), 40, (200, 180, 160), -1)
        
        # 身体（矩形）
        cv2.rectangle(frame, (280, 160), (360, 280), (100, 120, 140), -1)
        
        # 肩膀线（用于低头检测的关键参考线）
        cv2.line(frame, (250, 180), (390, 180), (150, 150, 150), 8)
        
        # 手臂
        cv2.line(frame, (250, 200), (200, 300), (120, 140, 160), 12)
        cv2.line(frame, (390, 200), (440, 300), (120, 140, 160), 12)
        
        # 鼻子位置（关键点，稍微低于肩膀线以模拟轻微低头）
        cv2.circle(frame, (320, 130), 5, (255, 200, 200), -1)
        
        # 眼睛
        cv2.circle(frame, (310, 115), 3, (255, 255, 255), -1)
        cv2.circle(frame, (330, 115), 3, (255, 255, 255), -1)
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"模拟摄像头 {timestamp}", (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, "姿势检测测试", (20, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        return frame
    
    def process_detection_result(self, detection_result: dict, original_frame):
        """处理检测结果"""
        try:
            result_image = detection_result['image']
            detection_data = detection_result['detection']
            
            # 更新检测计数
            self.detection_count += 1
            
            # 构建结果数据
            result_data = {
                'timestamp': datetime.now(),
                'detection_count': self.detection_count,
                'detection_data': detection_data,
                'result_image': result_image,  # 直接传递检测结果图像对象
                'original_frame': original_frame,  # 传递原始帧对象
                'image_path': None  # 不再保存文件，设为None
            }
            
            # 可选：如果仍需要保存检测结果图片到文件（用于调试）
            if config.POSE_DETECTION_CONFIG.get('save_detection_images', False):
                # 使用毫秒级时间戳避免文件名冲突
                timestamp_ms = int(time.time() * 1000)
                result_image_path = os.path.join(
                    self.detection_folder, 
                    f"detection_{self.detection_count}_{timestamp_ms}.jpg"
                )
                print(f"[DEBUG] 保存检测结果图片到: {result_image_path}")
                cv2.imwrite(result_image_path, result_image)
                
                # 验证文件保存
                if os.path.exists(result_image_path) and os.path.getsize(result_image_path) > 0:
                    result_data['image_path'] = result_image_path
                    print(f"[DEBUG] 检测结果图片保存成功")
                else:
                    print(f"[ERROR] 检测结果图片保存失败")
            else:
                print(f"[DEBUG] 配置设置不保存检测图片")
            
            # 添加到结果列表
            self.detection_results.append(result_data)
            
            # 检查不良姿势
            self.check_bad_posture(detection_data)
            
            # 检查近视风险
            self.check_myopia_risk(detection_data)
            
            # 发送检测完成信号
            print(f"[DEBUG] 发送检测完成信号: detection_count={self.detection_count}")
            print(f"[DEBUG] 结果数据包含图像对象")
            self.detection_completed.emit(result_data)
            
            # 清理旧结果
            self.cleanup_old_results()
            
            logger.info(f"姿势检测完成 #{self.detection_count}: {detection_data.get('severity', 'unknown')}")
            
        except Exception as e:
            logger.error(f"处理检测结果失败: {e}")
    
    def check_bad_posture(self, detection_data: dict):
        """检查不良姿势并发送警告"""
        try:
            if not config.POSE_DETECTION_CONFIG['alert_on_bad_posture']:
                return
            
            if not detection_data.get('valid', False):
                return
            
            is_bad_posture = detection_data.get('is_head_down', False)
            
            if is_bad_posture:
                self.consecutive_bad_posture += 1
                logger.warning(f"检测到不良姿势，连续次数: {self.consecutive_bad_posture}")
                
                # 检查是否达到警告阈值
                threshold = config.POSE_DETECTION_CONFIG['consecutive_bad_posture_threshold']
                if self.consecutive_bad_posture >= threshold:
                    severity = detection_data.get('severity', '低头')
                    alert_message = f"检测到连续{self.consecutive_bad_posture}次{severity}，请注意调整坐姿！"
                    self.posture_alert.emit(alert_message, self.consecutive_bad_posture)
            else:
                # 重置连续不良姿势计数
                if self.consecutive_bad_posture > 0:
                    logger.info("姿势已改善，重置不良姿势计数")
                    self.consecutive_bad_posture = 0
            
        except Exception as e:
            logger.error(f"检查不良姿势失败: {e}")
    
    def check_myopia_risk(self, detection_data: dict):
        """检查近视风险并发送警告"""
        try:
            if not config.POSE_DETECTION_CONFIG['alert_on_myopia_risk']:
                return
            
            if not detection_data.get('valid', False):
                return
            
            has_myopia_risk = detection_data.get('myopia_risk', False)
            
            if has_myopia_risk:
                self.consecutive_myopia_risk += 1
                logger.warning(f"检测到近视风险，连续次数: {self.consecutive_myopia_risk}")
                
                # 检查是否达到警告阈值
                threshold = config.POSE_DETECTION_CONFIG['consecutive_myopia_risk_threshold']
                if self.consecutive_myopia_risk >= threshold:
                    myopia_level = detection_data.get('myopia_risk_level', '中等风险')
                    alert_message = f"检测到连续{self.consecutive_myopia_risk}次{myopia_level}，请调整与屏幕的距离！"
                    self.myopia_risk_alert.emit(alert_message, self.consecutive_myopia_risk)
            else:
                # 重置连续近视风险计数
                if self.consecutive_myopia_risk > 0:
                    logger.info("眼睛距离改善，重置近视风险计数")
                    self.consecutive_myopia_risk = 0
            
        except Exception as e:
            logger.error(f"检查近视风险失败: {e}")
    
    def cleanup_old_results(self):
        """清理旧的检测结果"""
        try:
            if not config.POSE_DETECTION_CONFIG['auto_cleanup']:
                return
            
            max_results = config.POSE_DETECTION_CONFIG['max_stored_results']
            
            # 清理内存中的结果
            if len(self.detection_results) > max_results:
                old_results = self.detection_results[:-max_results]
                self.detection_results = self.detection_results[-max_results:]
                
                # 删除对应的图片文件
                for result in old_results:
                    image_path = result.get('image_path')
                    if image_path and os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                        except:
                            pass
                
                logger.info(f"清理了 {len(old_results)} 个旧的检测结果")
            
        except Exception as e:
            logger.error(f"清理旧结果失败: {e}")
    
    def get_detection_statistics(self) -> dict:
        """获取检测统计信息"""
        try:
            if not self.detection_results:
                return {
                    'total_detections': 0,
                    'bad_posture_count': 0,
                    'bad_posture_rate': 0.0,
                    'myopia_risk_count': 0,
                    'myopia_risk_rate': 0.0,
                    'last_detection_time': None,
                    'consecutive_bad_posture': self.consecutive_bad_posture,
                    'consecutive_myopia_risk': self.consecutive_myopia_risk
                }
            
            bad_posture_count = sum(
                1 for result in self.detection_results 
                if result['detection_data'].get('is_head_down', False)
            )
            
            myopia_risk_count = sum(
                1 for result in self.detection_results 
                if result['detection_data'].get('myopia_risk', False)
            )
            
            return {
                'total_detections': len(self.detection_results),
                'bad_posture_count': bad_posture_count,
                'bad_posture_rate': bad_posture_count / len(self.detection_results) * 100,
                'myopia_risk_count': myopia_risk_count,
                'myopia_risk_rate': myopia_risk_count / len(self.detection_results) * 100,
                'last_detection_time': self.detection_results[-1]['timestamp'],
                'consecutive_bad_posture': self.consecutive_bad_posture,
                'consecutive_myopia_risk': self.consecutive_myopia_risk
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def clear_detection_history(self):
        """清除检测历史"""
        try:
            # 删除所有保存的图片
            for result in self.detection_results:
                image_path = result.get('image_path')
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
            
            # 清空结果列表
            self.detection_results.clear()
            self.detection_count = 0
            self.consecutive_bad_posture = 0
            self.consecutive_myopia_risk = 0
            
            logger.info("检测历史已清除")
            self.status_changed.emit("历史已清除")
            
        except Exception as e:
            logger.error(f"清除检测历史失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop_detection()
            if self.camera_handler:
                self.camera_handler.close_cameras()
        except:
            pass
