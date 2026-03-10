# -*- coding: utf-8 -*-
"""
摄像头处理模块
用于管理双摄像头的拍照和人脸识别功能
"""

import cv2
import os
import glob
import re
import time
import logging
import subprocess
import numpy as np
from typing import Optional, Tuple, List, Dict
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from face_rec import FaceRecognizer
from config import CAMERA_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraPreviewWidget(QWidget):
    """摄像头预览窗口"""
    
    def __init__(self, title: str = "摄像头预览", parent=None):
        super().__init__(parent)
        self.title = title
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle(self.title)
        self.setFixedSize(CAMERA_CONFIG['preview_width'], CAMERA_CONFIG['preview_height'] + 80)
        
        layout = QVBoxLayout()
        
        # 视频显示标签
        self.video_label = QLabel()
        self.video_label.setFixedSize(CAMERA_CONFIG['preview_width'], CAMERA_CONFIG['preview_height'])
        self.video_label.setStyleSheet("border: 2px solid #333; background-color: #000;")
        layout.addWidget(self.video_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始预览")
        self.start_btn.clicked.connect(self.start_preview)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止预览")
        self.stop_btn.clicked.connect(self.stop_preview)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.capture_btn = QPushButton("拍照")
        self.capture_btn.clicked.connect(self.capture_photo)
        self.capture_btn.setEnabled(False)
        button_layout.addWidget(self.capture_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def set_camera(self, camera):
        """设置摄像头"""
        self.camera = camera
        
    def start_preview(self):
        """开始预览"""
        if self.camera and self.camera.isOpened():
            self.timer.start(30)  # 30ms刷新间隔
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.capture_btn.setEnabled(True)
            
    def stop_preview(self):
        """停止预览"""
        self.timer.stop()
        self.video_label.clear()
        self.video_label.setText("预览已停止")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.capture_btn.setEnabled(False)
        
    def update_frame(self):
        """更新帧"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # 转换为RGB格式
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                # 创建QImage
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # 缩放到预览窗口大小
                scaled_image = qt_image.scaled(
                    CAMERA_CONFIG['preview_width'], 
                    CAMERA_CONFIG['preview_height']
                )
                
                # 显示图像
                self.video_label.setPixmap(QPixmap.fromImage(scaled_image))
                
    def capture_photo(self):
        """拍照"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                timestamp = int(time.time())
                filename = f"preview_capture_{timestamp}.png"
                cv2.imwrite(filename, frame)
                logger.info(f"预览拍照保存: {filename}")
                
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_preview()
        event.accept()


class CameraHandler(QThread):
    """摄像头处理器"""
    
    # 信号定义
    face_recognition_result = pyqtSignal(dict)  # 人脸识别结果信号
    photo_captured = pyqtSignal(bool)  # 拍照完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    preview_ready = pyqtSignal(str, object)  # 预览准备就绪信号 (类型, 摄像头对象)
    
    def __init__(self):
        super().__init__()
        self.photo_folder = "paper_photos"  # 拍照保存文件夹
        
        # 摄像头对象
        self.face_camera = None
        self.photo_camera = None
        self.face_camera_index = -1
        self.photo_camera_index = -1
        

        
        # 人脸识别器
        self.face_recognizer = None
        
        # 初始化
        self._find_cameras()
        self._init_cameras()
        self._init_face_recognizer()
        self._ensure_photo_folder()

    def is_main_video_device(self, dev, timeout=1.0):
        """检查设备是否是主视频捕获设备"""
        try:
            # 检查 Video Capture
            info = subprocess.run(
                ['v4l2-ctl', '--device', dev, '--all'],
                capture_output=True, text=True, timeout=timeout
            )
            if 'Video Capture' not in info.stdout:
                return False

            # 检查常见的图像格式
            formats = subprocess.run(
                ['v4l2-ctl', '--device', dev, '--list-formats-ext'],
                capture_output=True, text=True, timeout=timeout
            ).stdout

            return bool(re.search(r'YUYV|MJPG|RGB3|NV12', formats))

        except subprocess.TimeoutExpired:
            # 设备响应太慢，跳过
            print(f'{dev} 响应超时，跳过')
            return False
        except subprocess.CalledProcessError:
            # v4l2-ctl 返回非零时也跳过
            print(f'{dev} 调用失败，跳过')
            return False
        except Exception as e:
            print(f'{dev} 检查失败: {e}')
            return False
        
    def _find_cameras(self):
        """根据设备名称查找摄像头索引"""
        try:
            # 使用v4l2-ctl列出摄像头设备
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                    capture_output=True, text=True)
            print(result)
            
            # 获取输出内容
            output = result.stdout
            if not output:
                logger.warning("v4l2-ctl命令没有输出，尝试使用索引查找摄像头")
                self._find_cameras_by_index()
                return
            
            lines = output.split('\n')
            
            current_device = ""
            device_paths = {}
            print(lines)

            # 查找目标摄像头
            face_camera_name = CAMERA_CONFIG['face_camera_name']
            photo_camera_name = CAMERA_CONFIG['photo_camera_name']

            for line in lines:
                line = line.strip()
                if line and not line.startswith('/dev/'):
                    # 设备名称行
                    current_device = line.split(' (')[0]

                elif line.startswith('/dev/video'):
                    # 设备路径行
                    print(f"检查设备: {current_device}")
                    # 检查当前设备是否是我们需要的摄像头（使用in操作符进行部分匹配）
                    if (current_device and 
                        (face_camera_name in current_device or photo_camera_name in current_device)):
                        print(f"找到目标设备: {line}")
                        if self.is_main_video_device(line):
                            device_paths[current_device] = line
                            print(f'{current_device} ✅ 主摄像头接口: {line}')
                        else:
                            print(f'{current_device} ❌ 非主接口或跳过: {line}')
            print(device_paths)
            logger.info(f"找到摄像头设备: {device_paths}")
            

            
            found_face_camera = False
            found_photo_camera = False
            
            for device_name, device_path in device_paths.items():
                if face_camera_name in device_name:
                    # 提取设备索引
                    self.face_camera_index = int(device_path.split('video')[1])
                    logger.info(f"找到人脸识别摄像头: {device_name} -> {device_path} (索引: {self.face_camera_index})")
                    found_face_camera = True
                
                if photo_camera_name in device_name:
                    # 提取设备索引
                    self.photo_camera_index = int(device_path.split('video')[1])
                    logger.info(f"找到拍照摄像头: {device_name} -> {device_path} (索引: {self.photo_camera_index})")
                    found_photo_camera = True
            
            # 检查是否找到了我们需要的摄像头
            if found_face_camera and found_photo_camera:
                logger.info("✅ 成功检测到所有需要的摄像头")
            elif found_face_camera or found_photo_camera:
                logger.warning(f"⚠️ 部分摄像头检测成功 - 人脸识别:{found_face_camera}, 拍照:{found_photo_camera}")
                # 继续使用检测到的摄像头，对于未检测到的尝试使用索引查找
                if not found_face_camera or not found_photo_camera:
                    logger.info("尝试使用索引查找未检测到的摄像头...")
                    self._find_cameras_by_index()
            else:
                logger.warning("❌ 未找到指定名称的摄像头，尝试使用默认索引")
                self._find_cameras_by_index()
                
        except Exception as e:
            logger.error(f"查找摄像头设备失败: {e}")
            self._find_cameras_by_index()
    
    def _find_cameras_by_index(self):
        """通过索引查找可用摄像头"""
        logger.info("通过索引查找可用摄像头...")
        
        # 获取配置的摄像头名称
        face_camera_name = CAMERA_CONFIG['face_camera_name']
        photo_camera_name = CAMERA_CONFIG['photo_camera_name']
        
        # 已知的摄像头索引映射（基于v4l2-ctl检测结果）
        known_mapping = {
            "UNIQUESKY_CAR_CAMERA: Integrate": 4,  # 人脸识别摄像头
            "DECXIN: DECXIN": 2                   # 试卷拍照摄像头
        }
        
        # 优先使用已知映射
        if self.face_camera_index == -1 and face_camera_name in known_mapping:
            test_index = known_mapping[face_camera_name]
            if self._test_camera_index(test_index):
                self.face_camera_index = test_index
                logger.info(f"根据已知映射分配索引 {test_index} 给人脸识别摄像头 ({face_camera_name})")
        
        if self.photo_camera_index == -1 and photo_camera_name in known_mapping:
            test_index = known_mapping[photo_camera_name]
            if self._test_camera_index(test_index):
                self.photo_camera_index = test_index
                logger.info(f"根据已知映射分配索引 {test_index} 给拍照摄像头 ({photo_camera_name})")
        
        # 如果已知映射失败，只测试有限的常用索引
        if self.face_camera_index == -1 or self.photo_camera_index == -1:
            available_indices = []
            # 只测试常用的摄像头索引，避免大量无效测试
            common_indices = [0, 1, 2, 3, 4]
            logger.info("测试常用摄像头索引...")
            
            for i in common_indices:
                if self._test_camera_index(i):
                    available_indices.append(i)
                    logger.info(f"找到可用摄像头索引: {i}")
            
            # 根据配置意图分配剩余的摄像头
            if self.face_camera_index == -1 and available_indices:
                # 为人脸识别摄像头选择索引（优先使用较大的索引，通常是UNIQUESKY_CAR_CAMERA）
                self.face_camera_index = max(available_indices)
                available_indices.remove(self.face_camera_index)
                logger.info(f"分配索引 {self.face_camera_index} 给人脸识别摄像头")
                
            if self.photo_camera_index == -1 and available_indices:
                # 为拍照摄像头选择剩余的索引
                self.photo_camera_index = min(available_indices)
                logger.info(f"分配索引 {self.photo_camera_index} 给拍照摄像头")
        
        # 如果没有找到任何摄像头，启用模拟模式
        if self.face_camera_index == -1 and self.photo_camera_index == -1:
            logger.warning("未找到任何可用摄像头，启用模拟模式")
            self.face_camera_index = -99  # 使用特殊索引表示模拟模式
            self.photo_camera_index = -99
        # 如果只找到一个摄像头，两个功能使用同一个
        elif self.face_camera_index != -1 and self.photo_camera_index == -1:
            self.photo_camera_index = self.face_camera_index
            logger.info(f"只找到一个摄像头，人脸识别和拍照使用同一个摄像头: {self.face_camera_index}")
        elif self.face_camera_index == -1 and self.photo_camera_index != -1:
            self.face_camera_index = self.photo_camera_index
            logger.info(f"只找到一个摄像头，人脸识别和拍照使用同一个摄像头: {self.photo_camera_index}")
    
    def _test_camera_index(self, index: int) -> bool:
        """测试指定索引的摄像头是否可用"""
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                # 尝试读取一帧，确保摄像头真的可用
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    return True
                else:
                    logger.debug(f"摄像头索引 {index} 可以打开但无法读取画面")
                    return False
            else:
                return False
        except Exception as e:
            logger.debug(f"测试摄像头索引 {index} 失败: {e}")
            return False
    
    def _init_cameras(self):
        """初始化摄像头"""
        try:
            # 检查必要的配置项
            required_keys = ['frame_width', 'frame_height', 'fps']
            missing_keys = [key for key in required_keys if key not in CAMERA_CONFIG]
            
            if missing_keys:
                error_msg = f"缺少必要的摄像头配置项: {missing_keys}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return
            
            # 初始化人脸识别摄像头
            if self.face_camera_index == -99:
                # 模拟模式
                self.face_camera = "SIMULATED_CAMERA"
                logger.info("人脸识别摄像头初始化为模拟模式")
            elif self.face_camera_index != -1:
                self.face_camera = cv2.VideoCapture(self.face_camera_index)
                if self.face_camera.isOpened():
                    # 设置摄像头参数
                    self.face_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['frame_width'])
                    self.face_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['frame_height'])
                    self.face_camera.set(cv2.CAP_PROP_FPS, CAMERA_CONFIG['fps'])
                    logger.info(f"人脸识别摄像头 {self.face_camera_index} 初始化成功")
                else:
                    logger.warning(f"人脸识别摄像头 {self.face_camera_index} 无法打开")
                    self.face_camera = None
            else:
                logger.warning("未找到人脸识别摄像头")
            
            # 初始化拍照摄像头
            if self.photo_camera_index == -99:
                # 模拟模式
                self.photo_camera = "SIMULATED_CAMERA"
                logger.info("拍照摄像头初始化为模拟模式")
            elif self.photo_camera_index != -1:
                if self.photo_camera_index == self.face_camera_index:
                    # 使用同一个摄像头
                    self.photo_camera = self.face_camera
                    logger.info("拍照摄像头使用人脸识别摄像头")
                else:
                    self.photo_camera = cv2.VideoCapture(self.photo_camera_index)
                    if self.photo_camera.isOpened():
                        # 设置摄像头参数
                        self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['frame_width'])
                        self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['frame_height'])
                        self.photo_camera.set(cv2.CAP_PROP_FPS, CAMERA_CONFIG['fps'])
                        logger.info(f"拍照摄像头 {self.photo_camera_index} 初始化成功")
                    else:
                        logger.warning(f"拍照摄像头 {self.photo_camera_index} 无法打开")
                        self.photo_camera = None
            else:
                logger.warning("未找到拍照摄像头")
                
        except Exception as e:
            logger.error(f"初始化摄像头失败: {e}")
            self.error_occurred.emit(f"初始化摄像头失败: {e}")
    
    def get_face_camera(self):
        """获取人脸识别摄像头对象"""
        return self.face_camera
        
    def get_photo_camera(self):
        """获取拍照摄像头对象"""
        return self.photo_camera
        
    def is_face_camera_ready(self) -> bool:
        """检查人脸识别摄像头是否就绪"""
        if self.face_camera == "SIMULATED_CAMERA":
            return True
        return self.face_camera is not None and self.face_camera.isOpened()
        
    def is_photo_camera_ready(self) -> bool:
        """检查拍照摄像头是否就绪"""
        if self.photo_camera == "SIMULATED_CAMERA":
            return True
        return self.photo_camera is not None and self.photo_camera.isOpened()
    
    def _init_face_recognizer(self):
        """初始化人脸识别器"""
        try:
            self.face_recognizer = FaceRecognizer()
            logger.info("人脸识别器初始化成功")
        except Exception as e:
            logger.error(f"初始化人脸识别器失败: {e}")
            self.error_occurred.emit(f"初始化人脸识别器失败: {e}")
    
    def _ensure_photo_folder(self):
        """确保拍照文件夹存在"""
        try:
            if not os.path.exists(self.photo_folder):
                os.makedirs(self.photo_folder)
                logger.info(f"创建拍照文件夹: {self.photo_folder}")
        except Exception as e:
            logger.error(f"创建拍照文件夹失败: {e}")
    
    def clear_photos(self):
        """清除拍照文件夹中的所有PNG图片"""
        try:
            png_files = glob.glob(os.path.join(self.photo_folder, "*.png"))
            for file_path in png_files:
                os.remove(file_path)
                logger.info(f"删除图片: {file_path}")
            
            logger.info(f"清除了 {len(png_files)} 张PNG图片")
            return True
            
        except Exception as e:
            logger.error(f"清除图片失败: {e}")
            self.error_occurred.emit(f"清除图片失败: {e}")
            return False
    
    def capture_face_for_recognition(self) -> Optional[dict]:
        """
        使用人脸识别摄像头拍照并进行人脸识别
        
        Returns:
            人脸识别结果字典或None
        """
        if not self.is_face_camera_ready():
            error_msg = f"人脸识别摄像头未准备就绪 - 摄像头索引: {self.face_camera_index}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
        
        try:
            logger.info("开始人脸识别拍照...")
            
            frame = None
            
            if self.face_camera == "SIMULATED_CAMERA":
                # 模拟模式：创建一个虚拟人脸图片（高分辨率）
                import numpy as np
                frame = np.zeros((CAMERA_CONFIG['face_photo_height'], CAMERA_CONFIG['face_photo_width'], 3), dtype=np.uint8)
                # 添加一个简单的"人脸"模拟
                face_w = CAMERA_CONFIG['face_photo_width'] // 3
                face_h = CAMERA_CONFIG['face_photo_height'] // 3
                start_x = CAMERA_CONFIG['face_photo_width'] // 3
                start_y = CAMERA_CONFIG['face_photo_height'] // 3
                cv2.rectangle(frame, (start_x, start_y), (start_x + face_w, start_y + face_h), (100, 150, 200), -1)
                cv2.putText(frame, "SIMULATED FACE", (start_x + 50, start_y + face_h//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
                logger.info(f"生成模拟人脸图片 ({CAMERA_CONFIG['face_photo_width']}x{CAMERA_CONFIG['face_photo_height']})")
                
                # 模拟人脸识别结果
                result = {
                    'best_match': '测试学生',
                    'best_similarity': 0.95,
                    'best_distance': 0.3,
                    'success': True
                }
                
            else:
                # 🔧 真实摄像头模式 - 临时设置高分辨率进行人脸识别拍照
                original_width = self.face_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                original_height = self.face_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(f"原始摄像头分辨率: {int(original_width)}x{int(original_height)}")
                
                # 设置人脸识别专用高分辨率
                self.face_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['face_photo_width'])
                self.face_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['face_photo_height'])
                logger.info(f"设置人脸识别拍照分辨率: {CAMERA_CONFIG['face_photo_width']}x{CAMERA_CONFIG['face_photo_height']}")
                
                # 等待摄像头适应新分辨率
                time.sleep(0.5)
                
                # 连续拍摄几帧，确保图像稳定
                for _ in range(5):
                    ret, temp_frame = self.face_camera.read()
                    if not ret:
                        continue
                    time.sleep(0.1)
                
                # 获取最终高分辨率帧
                ret, frame = self.face_camera.read()
                # 提取九宫格中心区域（对所有图像都应用）
                if frame is not None:
                    height, width = frame.shape[:2]
                    # print(f"原始帧尺寸: {width}x{height}")
                    # 计算九宫格每格的尺寸
                    grid_height = height * 4 // 10
                    grid_width = width // 5
                    # print(f"九宫格尺寸: {grid_width}x{grid_height}")
                    
                    # 提取中心格（第2行第2列，索引为1,1）
                    center_y = (height - grid_height)//2 - height//4
                    center_x = (width - grid_width)//2
                    # print(f"中心区域位置: {center_x}, {center_y}")
                    
                    # 切片获取中心区域
                    frame = frame[center_y:center_y + grid_height, 
                                center_x:center_x + grid_width]
                    # print(f"提取九宫格中心区域，位置: {center_x}-{center_x + grid_width}, {center_y}-{center_y + grid_height}, 新尺寸: {frame.shape[1]}x{frame.shape[0]}")
                    # logger.info(f"提取九宫格中心区域，新尺寸: {frame.shape[1]}x{frame.shape[0]}")
                
                # 🔧 恢复原始预览分辨率
                self.face_camera.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
                self.face_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)
                logger.info(f"恢复摄像头预览分辨率: {int(original_width)}x{int(original_height)}")
                
                if not ret:
                    error_msg = "无法从人脸识别摄像头获取图像"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    return None
                
                logger.info(f"获取人脸识别图像，分辨率: {frame.shape[1]}x{frame.shape[0]}")
                
                # 进行真实人脸识别
                logger.info("正在进行人脸识别...")
                if not self.face_recognizer:
                    error_msg = "人脸识别器未初始化"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    return None
                    
                result = self.face_recognizer.recognize_image_array(frame, "face_capture")
            
            # 保存识别用的图片（可选，用于调试）
            face_image_path = os.path.join("face_photos", f"face_capture_{int(time.time())}.jpg")
            if not os.path.exists("face_photos"):
                os.makedirs("face_photos")
            cv2.imwrite(face_image_path, frame)
            
            logger.info(f"人脸识别完成: {result}")
            self.face_recognition_result.emit(result)
            
            return result
            
        except Exception as e:
            error_msg = f"人脸识别过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def capture_photos_for_homework(self, photo_count: int = 1) -> bool:
        """
        使用拍照摄像头拍摄作业照片
        
        Args:
            photo_count: 拍照数量
            
        Returns:
            是否拍照成功
        """
        if not self.is_photo_camera_ready():
            error_msg = f"拍照摄像头未准备就绪 - 摄像头索引: {self.photo_camera_index}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        try:
            logger.info(f"开始拍摄 {photo_count} 张作业照片...")
            logger.info(f"拍照摄像头状态: {self.photo_camera}")
            logger.info(f"拍照文件夹: {self.photo_folder}")
            
            # 确保文件夹存在
            self._ensure_photo_folder()
            
            # 先清除旧照片
            clear_success = self.clear_photos()
            logger.info(f"清除旧照片结果: {clear_success}")
            
            successful_photos = 0
            
            for i in range(photo_count):
                frame = None
                
                if self.photo_camera == "SIMULATED_CAMERA":
                    # 模拟模式：创建一个虚拟4K图片
                    try:
                        import numpy as np
                        frame = np.zeros((CAMERA_CONFIG['photo_height'], CAMERA_CONFIG['photo_width'], 3), dtype=np.uint8)
                        # 添加渐变背景
                        for y in range(CAMERA_CONFIG['photo_height']):
                            frame[y, :] = [50 + y//50, 100 + y//75, 150 + y//100]
                        
                        # 添加一些文字表示这是模拟图片（适应4K分辨率）
                        text_scale = 3.0
                        cv2.putText(frame, "SIMULATED 4K HOMEWORK IMAGE", (800, 800), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 255), 6)
                        timestamp_text = f"Time: {int(time.time())}"
                        cv2.putText(frame, timestamp_text, (900, 1000), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.8, (200, 200, 200), 5)
                        cv2.putText(frame, f"4K Photo #{i+1}", (1000, 1200), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.8, (255, 255, 0), 5)
                        cv2.putText(frame, f"Resolution: {CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']}", 
                                   (700, 1400), cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.6, (0, 255, 255), 4)
                        logger.info(f"成功生成4K模拟照片 {i+1} ({CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']})")
                    except Exception as e:
                        logger.error(f"生成模拟照片失败: {e}")
                        continue
                else:
                    # # 真实摄像头模式 - 临时设置1080P分辨率
                    # original_width = self.photo_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    # original_height = self.photo_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    
                    # # 设置1080P拍照分辨率（DECXIN支持的最大分辨率）
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['photo_width'])
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['photo_height'])
                    # logger.info(f"设置1080P拍照分辨率: {CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']}")
                    
                    # # 🔧 修复：添加对焦设置，解决画面模糊问题
                    # try:
                    #     # 设置自动对焦
                    #     self.photo_camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                    #     # 设置对焦模式
                    #     self.photo_camera.set(cv2.CAP_PROP_FOCUS, 0)  # 自动对焦
                    #     logger.info("已启用自动对焦设置")
                    # except Exception as focus_e:
                    #     logger.warning(f"设置对焦失败，可能摄像头不支持: {focus_e}")
                    
                    # # 等待摄像头适应新分辨率和对焦设置
                    # time.sleep(1.5)  # 增加等待时间让对焦稳定
                    
                    # # 连续拍摄更多帧，确保图像稳定
                    # stable_frame = None
                    # for attempt in range(10):  # 增加尝试次数
                    #     ret, temp_frame = self.photo_camera.read()
                    #     if ret and temp_frame is not None:
                    #         stable_frame = temp_frame
                    #         time.sleep(0.1)
                    #     else:
                    #         logger.warning(f"拍照尝试 {attempt+1}/10 失败")
                    #         time.sleep(0.2)  # 失败时等待更长时间
                    
                    # frame = stable_frame
                    
                    # # 恢复原始分辨率（用于预览）
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)
                    
                    # 🔧 修复：尝试多次读取摄像头，确保获取有效图像
                    frame = None
                    for attempt in range(5):  # 尝试5次
                        ret, temp_frame = self.photo_camera.read()
                        if ret and temp_frame is not None:
                            frame = temp_frame
                            logger.info(f"拍照摄像头读取成功，尝试次数: {attempt + 1}")
                            break
                        else:
                            logger.warning(f"拍照摄像头读取失败，尝试 {attempt + 1}/5")
                            time.sleep(0.1)  # 短暂等待再试
                    
                    if frame is None:
                        logger.error(f"无法从拍照摄像头获取第 {i+1} 张图像，所有尝试都失败")
                        continue
                    
                    # 提取九宫格中心区域（对所有图像都应用）
                    if frame is not None:
                        height, width = frame.shape[:2]
                        logger.info(f"原始拍照图像分辨率: {width}x{height}")
                        
                        # 计算九宫格每格的尺寸
                        grid_height = height
                        grid_width = width // 3
                        
                        # 提取中心格（第2行第2列，索引为1,1）
                        center_y = grid_height
                        center_x = grid_width
                        
                        # 切片获取中心区域
                        frame = frame[:, 
                                    center_x:center_x + grid_width]
                        
                        logger.info(f"提取九宫格中心区域，新尺寸: {frame.shape[1]}x{frame.shape[0]}")
                    
                    logger.info(f"获取拍照图像成功，最终分辨率: {frame.shape[1]}x{frame.shape[0]}")
                
                # 保存照片
                if frame is None:
                    logger.error(f"第 {i+1} 张照片帧为空，跳过")
                    continue
                    
                timestamp = int(time.time() * 1000)  # 使用毫秒时间戳避免重名
                photo_path = os.path.join(self.photo_folder, f"homework_{timestamp}_{i+1}.png")
                
                logger.info(f"正在保存照片到: {photo_path}")
                logger.info(f"照片尺寸: {frame.shape if frame is not None else 'None'}")
                
                try:
                    if cv2.imwrite(photo_path, frame):
                        # 验证文件是否真的被创建
                        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                            logger.info(f"成功保存照片: {photo_path} (大小: {os.path.getsize(photo_path)} 字节)")
                            successful_photos += 1
                        else:
                            logger.error(f"照片保存后验证失败: {photo_path}")
                    else:
                        logger.error(f"cv2.imwrite返回False: {photo_path}")
                except Exception as e:
                    logger.error(f"保存照片异常: {photo_path}, 错误: {e}")
                
                # 拍照间隔
                if i < photo_count - 1:
                    time.sleep(0.5)
            
            success = successful_photos > 0
            logger.info(f"拍照完成，成功 {successful_photos}/{photo_count} 张")
            
            self.photo_captured.emit(success)
            return success
            
        except Exception as e:
            error_msg = f"拍照过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def capture_photos_for_gesture(self, photo_count: int = 1) -> bool:
        """
        使用拍照摄像头拍摄作业照片
        
        Args:
            photo_count: 拍照数量
            
        Returns:
            是否拍照成功
        """
        if not self.is_photo_camera_ready():
            error_msg = f"拍照摄像头未准备就绪 - 摄像头索引: {self.photo_camera_index}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        try:
            logger.info(f"开始拍摄 {photo_count} 张作业照片...")
            logger.info(f"拍照摄像头状态: {self.photo_camera}")
            logger.info(f"拍照文件夹: {self.photo_folder}")
            
            # 确保文件夹存在
            self._ensure_photo_folder()
            
            # 先清除旧照片
            clear_success = self.clear_photos()
            logger.info(f"清除旧照片结果: {clear_success}")
            
            successful_photos = 0
            
            for i in range(photo_count):
                frame = None
                
                if self.photo_camera == "SIMULATED_CAMERA":
                    # 模拟模式：创建一个虚拟4K图片
                    try:
                        import numpy as np
                        frame = np.zeros((CAMERA_CONFIG['photo_height'], CAMERA_CONFIG['photo_width'], 3), dtype=np.uint8)
                        # 添加渐变背景
                        for y in range(CAMERA_CONFIG['photo_height']):
                            frame[y, :] = [50 + y//50, 100 + y//75, 150 + y//100]
                        
                        # 添加一些文字表示这是模拟图片（适应4K分辨率）
                        text_scale = 3.0
                        cv2.putText(frame, "SIMULATED 4K HOMEWORK IMAGE", (800, 800), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 255), 6)
                        timestamp_text = f"Time: {int(time.time())}"
                        cv2.putText(frame, timestamp_text, (900, 1000), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.8, (200, 200, 200), 5)
                        cv2.putText(frame, f"4K Photo #{i+1}", (1000, 1200), 
                                   cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.8, (255, 255, 0), 5)
                        cv2.putText(frame, f"Resolution: {CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']}", 
                                   (700, 1400), cv2.FONT_HERSHEY_SIMPLEX, text_scale*0.6, (0, 255, 255), 4)
                        logger.info(f"成功生成4K模拟照片 {i+1} ({CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']})")
                    except Exception as e:
                        logger.error(f"生成模拟照片失败: {e}")
                        continue
                else:
                    # # 真实摄像头模式 - 临时设置1080P分辨率
                    # original_width = self.photo_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    # original_height = self.photo_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    
                    # # 设置1080P拍照分辨率（DECXIN支持的最大分辨率）
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['photo_width'])
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['photo_height'])
                    # logger.info(f"设置1080P拍照分辨率: {CAMERA_CONFIG['photo_width']}x{CAMERA_CONFIG['photo_height']}")
                    
                    # # 🔧 修复：添加对焦设置，解决画面模糊问题
                    # try:
                    #     # 设置自动对焦
                    #     self.photo_camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                    #     # 设置对焦模式
                    #     self.photo_camera.set(cv2.CAP_PROP_FOCUS, 0)  # 自动对焦
                    #     logger.info("已启用自动对焦设置")
                    # except Exception as focus_e:
                    #     logger.warning(f"设置对焦失败，可能摄像头不支持: {focus_e}")
                    
                    # # 等待摄像头适应新分辨率和对焦设置
                    # time.sleep(1.5)  # 增加等待时间让对焦稳定
                    
                    # # 连续拍摄更多帧，确保图像稳定
                    # stable_frame = None
                    # for attempt in range(10):  # 增加尝试次数
                    #     ret, temp_frame = self.photo_camera.read()
                    #     if ret and temp_frame is not None:
                    #         stable_frame = temp_frame
                    #         time.sleep(0.1)
                    #     else:
                    #         logger.warning(f"拍照尝试 {attempt+1}/10 失败")
                    #         time.sleep(0.2)  # 失败时等待更长时间
                    
                    # frame = stable_frame
                    
                    # # 恢复原始分辨率（用于预览）
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
                    # self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)
                    
                    # 🔧 修复：尝试多次读取摄像头（第二处相同问题）
                    frame = None
                    for attempt in range(5):  # 尝试5次
                        ret, temp_frame = self.photo_camera.read()
                        if ret and temp_frame is not None:
                            frame = temp_frame
                            logger.info(f"拍照摄像头读取成功（第二处），尝试次数: {attempt + 1}")
                            break
                        else:
                            logger.warning(f"拍照摄像头读取失败（第二处），尝试 {attempt + 1}/5")
                            time.sleep(0.1)  # 短暂等待再试
                    
                    if frame is None:
                        logger.error(f"无法从拍照摄像头获取第 {i+1} 张图像，所有尝试都失败")
                        continue
                    
                    # 提取九宫格中心区域（对所有图像都应用）
                    height, width = frame.shape[:2]
                    logger.info(f"原始拍照图像分辨率（第二处）: {width}x{height}")
                    
                    # 计算九宫格每格的尺寸
                    grid_height = height // 3
                    grid_width = width // 3
                    
                    # 提取中心格（第2行第2列，索引为1,1）
                    center_y = grid_height
                    center_x = grid_width
                    
                    # 切片获取中心区域
                    frame = frame[center_y:center_y + grid_height, 
                                center_x:center_x + grid_width]
                    
                    logger.info(f"提取九宫格中心区域（第二处），新尺寸: {frame.shape[1]}x{frame.shape[0]}")
                
                
                
                # 保存照片
                if frame is None:
                    logger.error(f"第 {i+1} 张照片帧为空，跳过")
                    continue
                    
                timestamp = int(time.time() * 1000)  # 使用毫秒时间戳避免重名
                photo_path = os.path.join(self.photo_folder, f"gesture_{timestamp}_{i+1}.png")
                
                logger.info(f"正在保存照片到: {photo_path}")
                logger.info(f"照片尺寸: {frame.shape if frame is not None else 'None'}")
                
                try:
                    if cv2.imwrite(photo_path, frame):
                        # 验证文件是否真的被创建
                        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                            logger.info(f"成功保存照片: {photo_path} (大小: {os.path.getsize(photo_path)} 字节)")
                            successful_photos += 1
                        else:
                            logger.error(f"照片保存后验证失败: {photo_path}")
                    else:
                        logger.error(f"cv2.imwrite返回False: {photo_path}")
                except Exception as e:
                    logger.error(f"保存照片异常: {photo_path}, 错误: {e}")
                
                # 拍照间隔
                if i < photo_count - 1:
                    time.sleep(0.5)
            
            success = successful_photos > 0
            logger.info(f"拍照完成，成功 {successful_photos}/{photo_count} 张")
            
            self.photo_captured.emit(success)
            return success
            
        except Exception as e:
            error_msg = f"拍照过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def capture_single_photo(self) -> bool:
        """
        拍摄单张照片（响应MQTT信号）
        
        Returns:
            是否拍照成功
        """
        return self.capture_photos_for_homework(1)
    
    def get_photo_count(self) -> int:
        """
        获取当前拍照文件夹中的PNG图片数量
        
        Returns:
            图片数量
        """
        try:
            png_files = glob.glob(os.path.join(self.photo_folder, "*.png"))
            return len(png_files)
        except Exception as e:
            logger.error(f"获取图片数量失败: {e}")
            return 0
    
    def get_photo_paths(self) -> List[str]:
        """
        获取当前拍照文件夹中所有PNG图片的路径
        
        Returns:
            图片路径列表
        """
        try:
            png_files = glob.glob(os.path.join(self.photo_folder, "*.png"))
            png_files.sort()  # 按文件名排序
            return png_files
        except Exception as e:
            logger.error(f"获取图片路径失败: {e}")
            return []
    
    def get_latest_photo_paths(self) -> List[str]:
        """
        获取最新拍摄的照片路径（按修改时间排序）
        
        Returns:
            最新照片路径列表
        """
        try:
            png_files = glob.glob(os.path.join(self.photo_folder, "*.png"))
            if not png_files:
                return []
            
            # 按修改时间排序，最新的在前
            png_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return png_files
        except Exception as e:
            logger.error(f"获取最新照片路径失败: {e}")
            return []
    
    def close_cameras(self):
        """关闭所有摄像头"""
        try:
            if self.face_camera and self.face_camera != "SIMULATED_CAMERA":
                self.face_camera.release()
                self.face_camera = None
                logger.info("人脸识别摄像头已关闭")
            
            if self.photo_camera and self.photo_camera != "SIMULATED_CAMERA":
                self.photo_camera.release()
                self.photo_camera = None
                logger.info("拍照摄像头已关闭")
                
        except Exception as e:
            logger.error(f"关闭摄像头失败: {e}")
    
    def restart_cameras(self):
        """重启摄像头"""
        try:
            logger.info("重启摄像头...")
            # 先关闭现有摄像头
            self.close_cameras()
            
            # 重新查找和初始化摄像头
            self._find_cameras()
            self._init_cameras()
            
            logger.info("摄像头重启完成")
            return True
            
        except Exception as e:
            logger.error(f"重启摄像头失败: {e}")
            self.error_occurred.emit(f"重启摄像头失败: {e}")
            return False
    
    def _release_camera_if_needed(self, camera_type: str) -> bool:
        """
        重新初始化指定类型的摄像头
        :param camera_type: 摄像头类型 ("face" 或 "photo")
        :return: 是否成功
        """
        try:
            logger.info(f"准备重新初始化{camera_type}摄像头...")
            
            if camera_type == "face":
                # 释放人脸识别摄像头
                if self.face_camera and self.face_camera != "SIMULATED_CAMERA":
                    self.face_camera.release()
                    self.face_camera = None
                    logger.info("人脸识别摄像头已释放")
                
                # 重新初始化人脸识别摄像头
                if self.face_camera_index == -99:
                    # 模拟模式
                    self.face_camera = "SIMULATED_CAMERA"
                    logger.info("人脸识别摄像头重新初始化为模拟模式")
                elif self.face_camera_index != -1:
                    self.face_camera = cv2.VideoCapture(self.face_camera_index)
                    if self.face_camera.isOpened():
                        # 设置摄像头参数
                        self.face_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['frame_width'])
                        self.face_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['frame_height'])
                        self.face_camera.set(cv2.CAP_PROP_FPS, CAMERA_CONFIG['fps'])
                        logger.info(f"人脸识别摄像头 {self.face_camera_index} 重新初始化成功")
                    else:
                        logger.error(f"人脸识别摄像头 {self.face_camera_index} 重新初始化失败")
                        return False
                
                # 发送预览就绪信号
                self.preview_ready.emit("face", self.face_camera)
                return True
                
            elif camera_type == "photo":
                # 🔧 只释放拍照摄像头，保持人脸摄像头独立工作
                if self.photo_camera and self.photo_camera != "SIMULATED_CAMERA":
                    self.photo_camera.release()
                    self.photo_camera = None
                    logger.info("拍照摄像头已释放")
                
                # 🛠️ 增加短暂延迟确保资源完全释放
                import time
                time.sleep(0.2)
                
                # 重新初始化拍照摄像头
                if self.photo_camera_index == -99:
                    # 模拟模式
                    self.photo_camera = "SIMULATED_CAMERA"
                    logger.info("拍照摄像头重新初始化为模拟模式")
                elif self.photo_camera_index != -1:
                    self.photo_camera = cv2.VideoCapture(self.photo_camera_index)
                    if self.photo_camera.isOpened():
                        # 设置摄像头参数
                        self.photo_camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG['frame_width'])
                        self.photo_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG['frame_height'])
                        self.photo_camera.set(cv2.CAP_PROP_FPS, CAMERA_CONFIG['fps'])
                        logger.info(f"拍照摄像头 {self.photo_camera_index} 重新初始化成功")
                    else:
                        logger.error(f"拍照摄像头 {self.photo_camera_index} 重新初始化失败")
                        return False
                
                # 发送预览就绪信号
                self.preview_ready.emit("photo", self.photo_camera)
                return True
            
            else:
                logger.error(f"未知的摄像头类型: {camera_type}")
                return False
                
        except Exception as e:
            logger.error(f"重新初始化{camera_type}摄像头失败: {e}")
            return False

    def __del__(self):
        """析构函数"""
        self.close_cameras() 