#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
嵌入式Linux摄像头拍照模块
专为UNIQUESKY_CAR_CAMERA USB摄像头设计
支持多路径存储和标志位控制
"""

import cv2
import os
import time
import logging
import subprocess
import re
from datetime import datetime
from typing import Tuple, Optional, Dict

# =============================================================================
# 配置参数 - 可根据需要修改
# =============================================================================
class CameraConfig:
    """摄像头配置类"""
    
    # 存储路径配置（可修改）
    PATH_MODE_0 = "/home/fibo/code/pyqt5/face_photos"      # 标志位=0时的存储路径
    PATH_MODE_1 = "/home/fibo/code/pyqt5/paper_photos"     # 标志位=1时的存储路径
    
    # 摄像头名字配置（根据USB设备名字匹配）
    CAMERA_NAME_MODE_0 = "UNIQUESKY_CAR_CAMERA"           # 标志位=0时使用的摄像头（人脸拍照）
    CAMERA_NAME_MODE_1 = "DECXIN"                         # 标志位=1时使用的摄像头（试卷拍照）
    
    # 摄像头参数
    FRAME_WIDTH = 1280                  # 图像宽度
    FRAME_HEIGHT = 720                  # 图像高度
    FPS = 30                           # 帧率
    
    # 拍照参数
    IMAGE_FORMAT = "png"               # 图像格式
    JPEG_QUALITY = 95                  # JPEG质量（如果使用jpg格式）
    
    # 超时设置
    CAMERA_INIT_TIMEOUT = 5            # 摄像头初始化超时（秒）
    CAPTURE_TIMEOUT = 3                # 拍照超时（秒）

# =============================================================================
# 摄像头检测和识别功能
# =============================================================================

def detect_camera_devices() -> Dict[str, int]:
    """
    检测并识别可用的摄像头设备
    
    Returns:
        Dict[str, int]: 摄像头名字到设备索引的映射
    """
    camera_mapping = {}
    
    try:
        # 方法1: 使用v4l2-ctl检测摄像头
        for i in range(10):  # 检查 /dev/video0 到 /dev/video9
            device_path = f"/dev/video{i}"
            if not os.path.exists(device_path):
                continue
                
            try:
                # 获取设备信息
                result = subprocess.run(
                    ['v4l2-ctl', '--device', device_path, '--info'],
                    capture_output=True, text=True, timeout=3
                )
                
                if result.returncode == 0:
                    info_text = result.stdout
                    
                    # 解析设备名字，优先选择视频流设备（偶数索引）
                    if 'UNIQUESKY_CAR_CAMERA' in info_text:
                        # 如果是偶数索引（视频流设备）或者还没有找到该摄像头，则记录
                        if 'UNIQUESKY_CAR_CAMERA' not in camera_mapping or i % 2 == 0:
                            camera_mapping['UNIQUESKY_CAR_CAMERA'] = i
                            print(f"✅ 找到UNIQUESKY_CAR_CAMERA摄像头: /dev/video{i}")
                        
                    elif 'DECXIN' in info_text:
                        # 如果是偶数索引（视频流设备）或者还没有找到该摄像头，则记录
                        if 'DECXIN' not in camera_mapping or i % 2 == 0:
                            camera_mapping['DECXIN'] = i
                            print(f"✅ 找到DECXIN摄像头: /dev/video{i}")
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # v4l2-ctl失败，尝试其他方法
                continue
                
    except Exception as e:
        print(f"⚠️  v4l2-ctl检测失败: {e}")
    
    # 方法2: 如果v4l2-ctl失败，使用OpenCV测试
    if not camera_mapping:
        print("🔍 使用OpenCV方法检测摄像头...")
        try:
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 简单的启发式识别（基于索引顺序）
                    if i == 2:  # 之前测试的工作索引
                        camera_mapping['UNIQUESKY_CAR_CAMERA'] = i
                        print(f"✅ 推测UNIQUESKY_CAR_CAMERA摄像头: /dev/video{i}")
                    elif i == 0 or i == 1:
                        camera_mapping['DECXIN'] = i
                        print(f"✅ 推测DECXIN摄像头: /dev/video{i}")
                    cap.release()
        except Exception as e:
            print(f"❌ OpenCV检测失败: {e}")
    
    return camera_mapping

def get_camera_index_by_name(camera_name: str) -> Optional[int]:
    """
    根据摄像头名字获取设备索引
    
    Args:
        camera_name: 摄像头名字
        
    Returns:
        Optional[int]: 设备索引，如果未找到返回None
    """
    camera_mapping = detect_camera_devices()
    return camera_mapping.get(camera_name)

# =============================================================================
# 双摄像头管理类
# =============================================================================

class DualCameraManager:
    """双摄像头管理器"""
    
    def __init__(self, enable_logging: bool = True):
        """
        初始化双摄像头管理器
        
        Args:
            enable_logging: 是否启用日志记录
        """
        self.config = CameraConfig()
        self.camera_mapping = {}
        self.cameras = {}  # 存储已初始化的摄像头对象
        
        # 设置日志
        if enable_logging:
            self._setup_logging()
        
        # 创建存储目录
        self._create_directories()
        
        # 检测摄像头设备
        self._detect_cameras()
    
    def _setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/tmp/dual_camera.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _create_directories(self):
        """创建存储目录"""
        try:
            os.makedirs(self.config.PATH_MODE_0, exist_ok=True)
            os.makedirs(self.config.PATH_MODE_1, exist_ok=True)
            if hasattr(self, 'logger'):
                self.logger.info(f"存储目录已创建: {self.config.PATH_MODE_0}, {self.config.PATH_MODE_1}")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"创建存储目录失败: {e}")
            print(f"创建存储目录失败: {e}")
    
    def _detect_cameras(self):
        """检测摄像头设备"""
        print("🔍 检测摄像头...")
        self.camera_mapping = detect_camera_devices()
        
        # 检查必要的摄像头是否存在
        if self.config.CAMERA_NAME_MODE_0 in self.camera_mapping:
            print(f"✅ 人脸摄像头: {self.config.CAMERA_NAME_MODE_0}")
        else:
            print(f"⚠️  未找到: {self.config.CAMERA_NAME_MODE_0}")
            
        if self.config.CAMERA_NAME_MODE_1 in self.camera_mapping:
            print(f"✅ 试卷摄像头: {self.config.CAMERA_NAME_MODE_1}")
        else:
            print(f"⚠️  未找到: {self.config.CAMERA_NAME_MODE_1}")
    
    def capture_photo(self, mode_flag: int) -> bool:
        """
        根据标志位使用对应的摄像头拍照
        
        Args:
            mode_flag: 标志位 (0 或 1)
                      0: 使用UNIQUESKY_CAR_CAMERA进行人脸拍照
                      1: 使用DECXIN进行试卷拍照
        
        Returns:
            bool: 拍照是否成功
        """
        try:
            # 确定使用的摄像头和存储路径
            if mode_flag == 0:
                camera_name = self.config.CAMERA_NAME_MODE_0
                save_path = self.config.PATH_MODE_0
                prefix = "face"
                description = "人脸拍照"
            elif mode_flag == 1:
                camera_name = self.config.CAMERA_NAME_MODE_1
                save_path = self.config.PATH_MODE_1
                prefix = "paper"
                description = "试卷拍照"
            else:
                print(f"❌ 无效的标志位: {mode_flag}, 应为0或1")
                return False
            
            # 检查摄像头是否可用
            if camera_name not in self.camera_mapping:
                print(f"❌ 摄像头 {camera_name} 不可用，无法进行{description}")
                return False
            
            camera_index = self.camera_mapping[camera_name]
            
            # 初始化摄像头（如果还没有初始化）
            if camera_index not in self.cameras:
                print(f"📷 初始化摄像头 {camera_name} (/dev/video{camera_index})...")
                camera = cv2.VideoCapture(camera_index)
                
                if not camera.isOpened():
                    print(f"❌ 无法打开摄像头 {camera_name}")
                    return False
                
                # 根据摄像头类型设置不同的参数
                if camera_name == "DECXIN":
                    print(f"🔧 配置DECXIN摄像头...")
                    # 使用MJPG+4K分辨率配置（摄像头支持的最大分辨率）
                    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
                    width_result = camera.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                    height_result = camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                    
                    # 如果4K失败，尝试备用配置640x480
                    if not (width_result and height_result):
                        print(f"   4K配置失败，使用备用配置640x480...")
                        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y','U','Y','V'))
                        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                else:
                    # UNIQUESKY_CAR_CAMERA使用标准配置
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
                
                camera.set(cv2.CAP_PROP_FPS, self.config.FPS)
                camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 等待摄像头稳定
                if camera_name == "DECXIN":
                    import time
                    time.sleep(0.5)  # 减少等待时间
                
                # 快速测试读取（减少尝试次数）
                frame = None
                for attempt in range(3):  # 减少尝试次数
                    ret, frame = camera.read()
                    if ret and frame is not None:
                        break
                    else:
                        import time
                        time.sleep(0.1)  # 减少等待时间
                
                if not ret or frame is None:
                    print(f"❌ 摄像头 {camera_name} 读取失败")
                    camera.release()
                    return False
                
                self.cameras[camera_index] = camera
                print(f"✅ 摄像头 {camera_name} 初始化成功")
            
            # 使用已初始化的摄像头拍照
            camera = self.cameras[camera_index]
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{prefix}_{timestamp}.{self.config.IMAGE_FORMAT}"
            full_path = os.path.join(save_path, filename)
            
            if hasattr(self, 'logger'):
                self.logger.info(f"开始{description} - 摄像头: {camera_name}, 路径: {full_path}")
            
            print(f"📸 正在进行{description} (使用 {camera_name})...")
            
            # 清空缓冲区，获取最新帧
            for _ in range(3):
                ret, frame = camera.read()
                if not ret:
                    continue
            
            # 最终拍照
            ret, frame = camera.read()
            
            if not ret or frame is None:
                print(f"❌ {camera_name} 读取帧失败")
                return False
            
            # 保存图像
            if self.config.IMAGE_FORMAT.lower() == 'png':
                success = cv2.imwrite(full_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            elif self.config.IMAGE_FORMAT.lower() in ['jpg', 'jpeg']:
                success = cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, self.config.JPEG_QUALITY])
            else:
                success = cv2.imwrite(full_path, frame)
            
            if success:
                file_size = os.path.getsize(full_path)
                if hasattr(self, 'logger'):
                    self.logger.info(f"{description}成功 - 文件: {full_path}, 大小: {file_size} bytes")
                print(f"✅ {description}成功!")
                print(f"   摄像头: {camera_name}")
                print(f"   文件: {filename}")
                print(f"   路径: {save_path}")
                print(f"   大小: {file_size / 1024:.1f} KB")
                return True
            else:
                print(f"❌ 保存图像失败: {full_path}")
                return False
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"{description}过程中发生错误: {e}")
            print(f"❌ {description}失败: {e}")
            return False
    
    def get_camera_info(self) -> dict:
        """
        获取双摄像头信息
        
        Returns:
            dict: 摄像头信息
        """
        info = {
            "camera_mapping": self.camera_mapping,
            "config": {
                "face_camera": self.config.CAMERA_NAME_MODE_0,
                "paper_camera": self.config.CAMERA_NAME_MODE_1,
                "face_path": self.config.PATH_MODE_0,
                "paper_path": self.config.PATH_MODE_1,
                "image_format": self.config.IMAGE_FORMAT
            },
            "initialized_cameras": list(self.cameras.keys())
        }
        return info
    
    def release_cameras(self):
        """释放所有摄像头资源"""
        try:
            for camera_index, camera in self.cameras.items():
                camera.release()
                print(f"📷 摄像头 /dev/video{camera_index} 资源已释放")
            
            self.cameras.clear()
            
            if hasattr(self, 'logger'):
                self.logger.info("所有摄像头资源已释放")
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"释放摄像头资源失败: {e}")
            print(f"❌ 释放摄像头资源失败: {e}")
    
    def __del__(self):
        """析构函数，自动释放资源"""
        self.release_cameras()

class LinuxCameraModule:
    """Linux摄像头拍照模块"""
    
    def __init__(self, enable_logging: bool = True, camera_index: int = None):
        """
        初始化摄像头模块
        
        Args:
            enable_logging: 是否启用日志记录
            camera_index: 摄像头设备索引，如果为None则自动检测
        """
        self.camera = None
        self.is_initialized = False
        self.config = CameraConfig()
        self.camera_index = camera_index  # 存储摄像头索引
        
        # 设置日志
        if enable_logging:
            self._setup_logging()
        
        # 创建存储目录
        self._create_directories()
        
        # 如果没有指定摄像头索引，自动检测第一个可用的摄像头
        if self.camera_index is None:
            self.camera_index = self._detect_default_camera()
    
    def _setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/tmp/camera_module.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _create_directories(self):
        """创建存储目录"""
        try:
            os.makedirs(self.config.PATH_MODE_0, exist_ok=True)
            os.makedirs(self.config.PATH_MODE_1, exist_ok=True)
            if hasattr(self, 'logger'):
                self.logger.info(f"存储目录已创建: {self.config.PATH_MODE_0}, {self.config.PATH_MODE_1}")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"创建存储目录失败: {e}")
            print(f"创建存储目录失败: {e}")
    
    def _detect_default_camera(self) -> int:
        """
        检测默认可用的摄像头设备索引
        
        Returns:
            int: 摄像头设备索引
        """
        try:
            # 首先尝试获取UNIQUESKY_CAR_CAMERA的索引
            camera_mapping = detect_camera_devices()
            if self.config.CAMERA_NAME_MODE_0 in camera_mapping:
                return camera_mapping[self.config.CAMERA_NAME_MODE_0]
            elif self.config.CAMERA_NAME_MODE_1 in camera_mapping:
                return camera_mapping[self.config.CAMERA_NAME_MODE_1]
            else:
                # 如果找不到特定摄像头，则使用第一个可用的
                for i in range(10):
                    test_cap = cv2.VideoCapture(i)
                    if test_cap.isOpened():
                        test_cap.release()
                        return i
                # 默认返回0
                return 0
        except Exception as e:
            print(f"检测默认摄像头失败: {e}")
            return 0
    
    def initialize_camera(self) -> bool:
        """
        初始化摄像头
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            if hasattr(self, 'logger'):
                self.logger.info(f"正在初始化摄像头 /dev/video{self.camera_index}...")
            
            # 创建摄像头对象
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                if hasattr(self, 'logger'):
                    self.logger.error(f"无法打开摄像头设备 /dev/video{self.camera_index}")
                return False
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, self.config.FPS)
            
            # 设置缓冲区大小为1，减少延迟
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 测试读取一帧
            ret, frame = self.camera.read()
            if not ret or frame is None:
                if hasattr(self, 'logger'):
                    self.logger.error("摄像头测试读取失败")
                self.camera.release()
                return False
            
            self.is_initialized = True
            if hasattr(self, 'logger'):
                self.logger.info(f"摄像头初始化成功 - 分辨率: {frame.shape[1]}x{frame.shape[0]}")
            
            print(f"✅ 摄像头初始化成功 - 设备: /dev/video{self.camera_index}")
            print(f"✅ 分辨率: {frame.shape[1]}x{frame.shape[0]}")
            
            return True
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"摄像头初始化失败: {e}")
            print(f"❌ 摄像头初始化失败: {e}")
            return False
    
    def capture_photo(self, mode_flag: int) -> bool:
        """
        拍照功能
        
        Args:
            mode_flag: 标志位 (0 或 1)
                      0: 存储到 PATH_MODE_0 (人脸照片路径)
                      1: 存储到 PATH_MODE_1 (试卷照片路径)
        
        Returns:
            bool: 拍照是否成功
        """
        if not self.is_initialized:
            print("❌ 摄像头未初始化，正在尝试初始化...")
            if not self.initialize_camera():
                return False
        
        try:
            # 确定存储路径
            if mode_flag == 0:
                save_path = self.config.PATH_MODE_0
                prefix = "face"
            elif mode_flag == 1:
                save_path = self.config.PATH_MODE_1
                prefix = "paper"
            else:
                if hasattr(self, 'logger'):
                    self.logger.error(f"无效的标志位: {mode_flag}, 应为0或1")
                print(f"❌ 无效的标志位: {mode_flag}, 应为0或1")
                return False
            
            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
            filename = f"{prefix}_{timestamp}.{self.config.IMAGE_FORMAT}"
            full_path = os.path.join(save_path, filename)
            
            if hasattr(self, 'logger'):
                self.logger.info(f"开始拍照 - 模式: {mode_flag}, 路径: {full_path}")
            
            # 清空缓冲区，获取最新帧
            for _ in range(3):
                ret, frame = self.camera.read()
                if not ret:
                    continue
            
            # 最终拍照
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                if hasattr(self, 'logger'):
                    self.logger.error("读取摄像头帧失败")
                print("❌ 读取摄像头帧失败")
                return False
            
            # 保存图像
            if self.config.IMAGE_FORMAT.lower() == 'png':
                # PNG格式，无损压缩
                success = cv2.imwrite(full_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            elif self.config.IMAGE_FORMAT.lower() in ['jpg', 'jpeg']:
                # JPEG格式，指定质量
                success = cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, self.config.JPEG_QUALITY])
            else:
                # 其他格式，默认参数
                success = cv2.imwrite(full_path, frame)
            
            if success:
                file_size = os.path.getsize(full_path)
                if hasattr(self, 'logger'):
                    self.logger.info(f"拍照成功 - 文件: {full_path}, 大小: {file_size} bytes")
                print(f"✅ 拍照成功!")
                print(f"   文件: {filename}")
                print(f"   路径: {save_path}")
                print(f"   大小: {file_size / 1024:.1f} KB")
                return True
            else:
                if hasattr(self, 'logger'):
                    self.logger.error(f"保存图像失败: {full_path}")
                print(f"❌ 保存图像失败: {full_path}")
                return False
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"拍照过程中发生错误: {e}")
            print(f"❌ 拍照失败: {e}")
            return False
    
    def get_camera_info(self) -> dict:
        """
        获取摄像头信息
        
        Returns:
            dict: 摄像头信息
        """
        if not self.is_initialized:
            return {"error": "摄像头未初始化"}
        
        try:
            info = {
                "device_index": self.camera_index,
                "width": int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": int(self.camera.get(cv2.CAP_PROP_FPS)),
                "format": self.config.IMAGE_FORMAT,
                "path_mode_0": self.config.PATH_MODE_0,
                "path_mode_1": self.config.PATH_MODE_1,
                "is_opened": self.camera.isOpened()
            }
            return info
        except Exception as e:
            return {"error": str(e)}
    
    def release_camera(self):
        """释放摄像头资源"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.is_initialized = False
                if hasattr(self, 'logger'):
                    self.logger.info("摄像头资源已释放")
                print("📷 摄像头资源已释放")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"释放摄像头资源失败: {e}")
            print(f"❌ 释放摄像头资源失败: {e}")
    
    def __del__(self):
        """析构函数，自动释放资源"""
        self.release_camera()

# =============================================================================
# 便捷函数接口
# =============================================================================

def quick_capture(mode_flag: int) -> bool:
    """
    快速拍照函数（使用双摄像头管理器）
    
    Args:
        mode_flag: 标志位 (0 或 1)
                  0: 使用UNIQUESKY_CAR_CAMERA进行人脸拍照
                  1: 使用DECXIN进行试卷拍照
    
    Returns:
        bool: 拍照是否成功
    """
    dual_camera = DualCameraManager(enable_logging=False)
    
    try:
        return dual_camera.capture_photo(mode_flag)
    finally:
        dual_camera.release_cameras()

def quick_capture_legacy(mode_flag: int) -> bool:
    """
    旧版快速拍照函数（使用单摄像头模块，向后兼容）
    
    Args:
        mode_flag: 标志位 (0 或 1)
    
    Returns:
        bool: 拍照是否成功
    """
    camera_module = LinuxCameraModule(enable_logging=False)
    
    try:
        if camera_module.initialize_camera():
            return camera_module.capture_photo(mode_flag)
        else:
            return False
    finally:
        camera_module.release_camera()

# =============================================================================
# 测试和演示代码
# =============================================================================

def test_dual_camera_module():
    """测试双摄像头模块功能"""
    print("🔍 开始测试嵌入式Linux双摄像头模块...")
    print("=" * 50)
    
    # 创建双摄像头管理器实例
    dual_camera = DualCameraManager()
    
    try:
        # 显示摄像头信息
        info = dual_camera.get_camera_info()
        print(f"\n📋 双摄像头信息:")
        print(f"   摄像头映射: {info['camera_mapping']}")
        print(f"   人脸摄像头: {info['config']['face_camera']}")
        print(f"   试卷摄像头: {info['config']['paper_camera']}")
        print(f"   人脸照片路径: {info['config']['face_path']}")
        print(f"   试卷照片路径: {info['config']['paper_path']}")
        
        # 测试拍照
        print(f"\n📸 测试双摄像头拍照功能...")
        
        # 测试模式0（人脸照片）
        print("\n   测试模式0（人脸拍照）...")
        success_0 = dual_camera.capture_photo(0)
        print(f"   结果: {'✅ 成功' if success_0 else '❌ 失败'}")
        
        time.sleep(2)  # 等待2秒
        
        # 测试模式1（试卷照片）
        print("\n   测试模式1（试卷拍照）...")
        success_1 = dual_camera.capture_photo(1)
        print(f"   结果: {'✅ 成功' if success_1 else '❌ 失败'}")
        
        print(f"\n🏁 双摄像头测试完成!")
        print(f"   人脸拍照 (UNIQUESKY_CAR_CAMERA): {'✅ 成功' if success_0 else '❌ 失败'}")
        print(f"   试卷拍照 (DECXIN): {'✅ 成功' if success_1 else '❌ 失败'}")
        
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
    finally:
        dual_camera.release_cameras()

def test_camera_module():
    """测试摄像头模块功能（向后兼容）"""
    print("🔍 开始测试嵌入式Linux摄像头模块（旧版兼容模式）...")
    print("=" * 50)
    
    # 创建摄像头模块实例
    camera = LinuxCameraModule()
    
    try:
        # 测试初始化
        print("\n📷 测试摄像头初始化...")
        if not camera.initialize_camera():
            print("❌ 摄像头初始化失败，测试终止")
            return
        
        # 显示摄像头信息
        info = camera.get_camera_info()
        print(f"\n📋 摄像头信息:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # 测试拍照
        print(f"\n📸 测试拍照功能...")
        
        # 测试模式0（人脸照片）
        print("   测试模式0（人脸照片）...")
        success_0 = camera.capture_photo(0)
        print(f"   结果: {'✅ 成功' if success_0 else '❌ 失败'}")
        
        time.sleep(1)  # 等待1秒
        
        # 测试模式1（试卷照片）
        print("   测试模式1（试卷照片）...")
        success_1 = camera.capture_photo(1)
        print(f"   结果: {'✅ 成功' if success_1 else '❌ 失败'}")
        
        print(f"\n🏁 测试完成!")
        print(f"   模式0拍照: {'✅ 成功' if success_0 else '❌ 失败'}")
        print(f"   模式1拍照: {'✅ 成功' if success_1 else '❌ 失败'}")
        
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
    finally:
        camera.release_camera()

if __name__ == "__main__":
    # 运行双摄像头测试
    test_dual_camera_module()
    
    print("\n" + "=" * 60)
    print("💡 双摄像头使用示例:")
    print("   from linux_camera_module import DualCameraManager, quick_capture")
    print("   ")
    print("   # 方法1: 使用双摄像头管理器（推荐）")
    print("   dual_camera = DualCameraManager()")
    print("   success = dual_camera.capture_photo(0)  # 使用UNIQUESKY_CAR_CAMERA拍人脸照片")
    print("   success = dual_camera.capture_photo(1)  # 使用DECXIN拍试卷照片")
    print("   dual_camera.release_cameras()")
    print("   ")
    print("   # 方法2: 快速拍照（一次性，自动选择摄像头）")
    print("   success = quick_capture(0)  # 快速人脸拍照 (UNIQUESKY_CAR_CAMERA)")
    print("   success = quick_capture(1)  # 快速试卷拍照 (DECXIN)")
    print("   ")
    print("📱 摄像头分配:")
    print("   标志位 0: UNIQUESKY_CAR_CAMERA → 人脸拍照")
    print("   标志位 1: DECXIN → 试卷拍照") 