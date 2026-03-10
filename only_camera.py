#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单摄像头拍照程序（嵌入式Linux版本）
只用于摄像头拍照并存储照片，不进行人脸识别
适用于无GUI的嵌入式Linux系统
"""

import cv2
import os
import time
import threading
import subprocess
import numpy as np
from datetime import datetime
from typing import Optional, List
import sys
import select

class SimpleCameraCapture:
    """简单摄像头拍照类"""
    
    def __init__(self, camera_name: str = "UNIQUESKY_CAR_CAMERA", output_dir: str = "./face_photos"):
        """
        初始化摄像头拍照系统
        
        Args:
            camera_name: 摄像头名称
            output_dir: 照片保存目录
        """
        self.camera_name = camera_name
        self.output_dir = output_dir
        self.camera = None
        self.camera_index = None
        self.photo_count = 0
        self.running = False
        self.continuous_mode = False
        
        # 创建输出目录
        self._ensure_output_dir()
        
        # 查找摄像头
        self._find_camera()
        
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"创建照片存储目录: {self.output_dir}")
    
    def _find_camera(self):
        """查找指定名称的摄像头"""
        print(f"正在查找摄像头: {self.camera_name}")
        
        # 方法1: 通过v4l2-ctl查找摄像头
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if self.camera_name in line:
                        # 寻找下一行的设备路径
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip().startswith('/dev/video'):
                                device_path = lines[j].strip()
                                self.camera_index = int(device_path.split('video')[1])
                                print(f"找到摄像头 {self.camera_name} 在索引 {self.camera_index}")
                                return
        except Exception as e:
            print(f"v4l2-ctl查找摄像头失败: {e}")
        
        # 方法2: 遍历所有可用摄像头
        print("正在遍历所有可用摄像头...")
        for i in range(10):  # 检查索引0-9
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 尝试获取摄像头信息
                    ret, frame = cap.read()
                    if ret:
                        print(f"发现摄像头索引 {i}")
                        if self.camera_index is None:
                            self.camera_index = i  # 使用第一个可用的
                cap.release()
            except Exception as e:
                continue
        
        # 如果没有找到指定名称的摄像头，使用默认索引
        if self.camera_index is None:
            self.camera_index = 0
            print(f"未找到指定摄像头，使用默认索引: {self.camera_index}")
        
    def _init_camera(self) -> bool:
        """初始化摄像头"""
        try:
            print(f"正在初始化摄像头索引 {self.camera_index}...")
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                print(f"无法打开摄像头索引 {self.camera_index}")
                return False
                
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # 获取实际参数
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.camera.get(cv2.CAP_PROP_FPS))
            
            print(f"摄像头初始化成功")
            print(f"分辨率: {width}x{height}, 帧率: {fps}")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False
    
    def _save_photo(self, frame: np.ndarray) -> str:
        """保存照片"""
        timestamp = int(time.time())
        self.photo_count += 1
        filename = f"photo_{timestamp}_{self.photo_count:03d}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        # 保存照片
        success = cv2.imwrite(filepath, frame)
        
        if success:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 照片已保存: {filename} (第{self.photo_count}张)")
            return filepath
        else:
            print(f"保存照片失败: {filename}")
            return None
    
    def _print_status(self):
        """打印当前状态"""
        mode_text = "连续拍照模式" if self.continuous_mode else "手动拍照模式"
        print(f"\r状态: {mode_text} | 照片计数: {self.photo_count} | 输入命令: ", end="", flush=True)
    
    def _input_thread(self):
        """输入处理线程"""
        print("\n可用命令:")
        print("  s - 拍照")
        print("  c - 切换连续拍照模式")
        print("  r - 重置照片计数")
        print("  q - 退出程序")
        print("  h - 显示帮助")
        print("-" * 50)
        
        while self.running:
            try:
                self._print_status()
                # 使用select来检查是否有输入，避免阻塞
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    command = sys.stdin.readline().strip().lower()
                    self._process_command(command)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"\n输入处理错误: {e}")
                break
    
    def _process_command(self, command: str):
        """处理用户命令"""
        if command == 's':
            if not self.continuous_mode:
                print(f"\n手动拍照命令已接收...")
                self._capture_single_photo()
            else:
                print(f"\n连续拍照模式下，无需手动拍照")
        elif command == 'c':
            self.continuous_mode = not self.continuous_mode
            mode_status = "开启" if self.continuous_mode else "关闭"
            print(f"\n连续拍照模式: {mode_status}")
        elif command == 'r':
            self.photo_count = 0
            print(f"\n照片计数已重置")
        elif command == 'q':
            print(f"\n正在退出程序...")
            self.running = False
        elif command == 'h':
            print(f"\n可用命令:")
            print("  s - 拍照")
            print("  c - 切换连续拍照模式")
            print("  r - 重置照片计数")
            print("  q - 退出程序")
            print("  h - 显示帮助")
        elif command == '':
            pass  # 空命令，忽略
        else:
            print(f"\n未知命令: {command}，输入 'h' 查看帮助")
    
    def _capture_single_photo(self):
        """拍摄单张照片"""
        if self.camera is None:
            print("摄像头未初始化")
            return
        
        ret, frame = self.camera.read()
        if ret:
            self._save_photo(frame)
        else:
            print("无法读取摄像头数据")
    
    def start_capture(self):
        """开始拍照"""
        if not self._init_camera():
            return
        
        print("=" * 50)
        print("简单摄像头拍照程序已启动（嵌入式Linux版本）")
        print("=" * 50)
        
        self.running = True
        
        # 启动输入处理线程
        input_thread = threading.Thread(target=self._input_thread)
        input_thread.daemon = True
        input_thread.start()
        
        try:
            last_continuous_capture = time.time()
            
            while self.running:
                # 检查摄像头状态
                if not self.camera.isOpened():
                    print("摄像头连接断开")
                    break
                
                # 连续拍照模式
                if self.continuous_mode:
                    current_time = time.time()
                    if current_time - last_continuous_capture >= 0.5:  # 0.5秒间隔
                        self._capture_single_photo()
                        last_continuous_capture = current_time
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n程序被中断")
            self.running = False
        
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        self.running = False
        if self.camera:
            self.camera.release()
        print("\n摄像头资源已释放")
    
    def list_all_cameras(self):
        """列出所有可用摄像头"""
        print("正在扫描所有可用摄像头...")
        
        # 使用v4l2-ctl列出设备
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print("v4l2-ctl检测到的设备:")
                print(result.stdout)
        except Exception as e:
            print(f"v4l2-ctl不可用: {e}")
        
        # 遍历检查
        available_cameras = []
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        available_cameras.append(i)
                        print(f"摄像头索引 {i}: 可用")
                    else:
                        print(f"摄像头索引 {i}: 无法读取")
                else:
                    print(f"摄像头索引 {i}: 无法打开")
                cap.release()
            except Exception as e:
                print(f"摄像头索引 {i}: 错误 - {e}")
        
        return available_cameras

def main():
    """主函数"""
    print("简单摄像头拍照程序（嵌入式Linux版本）")
    print("=" * 40)
    
    # 创建拍照系统
    capture_system = SimpleCameraCapture(camera_name="UNIQUESKY_CAR_CAMERA")
    
    # 询问用户是否需要列出所有摄像头
    list_cameras = input("是否列出所有可用摄像头？(y/n，默认n): ").strip().lower()
    if list_cameras == 'y':
        available = capture_system.list_all_cameras()
        print(f"可用摄像头索引: {available}")
        
        # 让用户选择摄像头
        camera_input = input("请输入要使用的摄像头索引（直接回车使用自动检测）: ").strip()
        if camera_input.isdigit():
            capture_system.camera_index = int(camera_input)
            print(f"使用摄像头索引: {capture_system.camera_index}")
    
    # 开始拍照
    capture_system.start_capture()

if __name__ == "__main__":
    main()
