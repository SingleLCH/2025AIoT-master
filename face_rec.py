#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人脸识别脚本占位文件
实际使用时，这里应该实现真正的人脸识别功能
"""

import sys
import json
import time


"""
实时人脸识别系统 - 基于类封装
============================

功能特点:
1. 类封装设计，便于调用和扩展
2. 预加载已知人脸特征，快速匹配识别
3. 特征向量文件缓存，避免重复计算
4. 按键模拟拍照和照片写入触发
5. 详细的时间统计和结果输出


"""

import os
import glob
import numpy as np
import cv2
import time
import pickle
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from insightface.app import FaceAnalysis
from numpy.linalg import norm

# 尝试导入按键监听库
# keyboard库在拍照搜题系统中不需要，已移除相关功能
KEYBOARD_AVAILABLE = False


class FaceRecognizer:
    """高性能人脸识别器"""
    
    def __init__(self, 
                 known_dir: str = "./known",
                 cache_file: str = "./face_features_cache.pkl",
                 threshold: float = 1.2,
                 model_name: str = 'buffalo_s',
                 detect_size: Tuple[int, int] = (640, 640)):
        """
        初始化人脸识别器
        
        Args:
            known_dir: 已知人脸图片目录
            cache_file: 特征向量缓存文件路径
            threshold: 识别阈值
            model_name: InsightFace模型名称
            detect_size: 检测尺寸
        """
        self.known_dir = known_dir
        self.cache_file = cache_file
        self.threshold = threshold
        self.model_name = model_name
        self.detect_size = detect_size
        
        # 已知人脸数据
        self.known_names: List[str] = []
        self.known_embeddings: Optional[np.ndarray] = None
        
        # 统计信息
        self.init_time = 0
        self.load_time = 0
        
        # 初始化
        self._init_model()
        self._load_or_build_cache()
        
    def _init_model(self):
        """初始化InsightFace模型"""
        start_time = time.time()
        
        print("🚀 正在初始化人脸识别模型...")
        self.app = FaceAnalysis(name=self.model_name)
        self.app.prepare(ctx_id=0, det_size=self.detect_size)
        
        self.init_time = time.time() - start_time
        
        print(f"✓ 模型初始化完成 (耗时: {self.init_time:.2f}s)")
        print(f"  模型: {self.model_name}")
        print(f"  检测尺寸: {self.detect_size}")
        print(f"  阈值: {self.threshold}")
        print("-" * 50)
    
    def _get_face_embedding(self, img_path: str) -> Optional[np.ndarray]:
        """提取单张图片的人脸特征向量"""
        img = cv2.imread(img_path)
        if img is None:
            return None
            
        faces = self.app.get(img)
        if not faces:
            return None
        
        # 获取第一个人脸的特征向量并L2归一化
        embedding = faces[0].embedding
        normalized_embedding = embedding / norm(embedding)
        
        return normalized_embedding
    
    def _get_face_embedding_from_image(self, img: np.ndarray) -> Optional[np.ndarray]:
        """从图像数组提取人脸特征向量"""
        faces = self.app.get(img)
        if not faces:
            return None
        
        # 获取第一个人脸的特征向量并L2归一化
        embedding = faces[0].embedding
        normalized_embedding = embedding / norm(embedding)
        
        return normalized_embedding
    
    def _build_cache(self) -> bool:
        """构建特征向量缓存"""
        print("📁 正在构建特征向量缓存...")
        
        if not os.path.exists(self.known_dir):
            print(f"❌ 已知人脸目录不存在: {self.known_dir}")
            return False
        
        # 获取所有图片文件
        supported_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_files = []
        for ext in supported_extensions:
            image_files.extend(glob.glob(os.path.join(self.known_dir, ext)))
            image_files.extend(glob.glob(os.path.join(self.known_dir, ext.upper())))
        
        if not image_files:
            print(f"❌ 在目录 {self.known_dir} 中未找到图片文件")
            return False
        
        print(f"发现 {len(image_files)} 张已知人脸图片")
        
        known_faces = {}
        start_time = time.time()
        
        for i, file_path in enumerate(image_files, 1):
            name = os.path.basename(file_path)
            print(f"[{i}/{len(image_files)}] 处理: {name}")
            
            embedding = self._get_face_embedding(file_path)
            if embedding is not None:
                known_faces[name] = embedding
                print(f"  ✓ 成功提取特征")
            else:
                print(f"  ✗ 未检测到人脸")
        
        build_time = time.time() - start_time
        
        if not known_faces:
            print("❌ 未能提取到任何有效的人脸特征")
            return False
        
        # 保存缓存
        cache_data = {
            'known_faces': known_faces,
            'threshold': self.threshold,
            'model_name': self.model_name,
            'created_time': time.time(),
            'build_time': build_time
        }
        
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            print(f"✓ 特征缓存已保存: {self.cache_file}")
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")
            return False
        
        # 更新内部数据
        self.known_names = list(known_faces.keys())
        self.known_embeddings = np.array(list(known_faces.values()))
        
        print(f"✓ 缓存构建完成 (耗时: {build_time:.2f}s)")
        print(f"  成功加载 {len(known_faces)} 个人脸特征")
        print(f"  特征矩阵形状: {self.known_embeddings.shape}")
        
        return True
    
    def _load_cache(self) -> bool:
        """加载特征向量缓存"""
        if not os.path.exists(self.cache_file):
            return False
        
        try:
            start_time = time.time()
            
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.load_time = time.time() - start_time
            
            # 验证缓存有效性
            if (cache_data.get('model_name') != self.model_name or 
                cache_data.get('threshold') != self.threshold):
                print("⚠️  缓存参数不匹配，需要重新构建")
                return False
            
            known_faces = cache_data['known_faces']
            self.known_names = list(known_faces.keys())
            self.known_embeddings = np.array(list(known_faces.values()))
            
            print(f"✓ 特征缓存加载成功 (耗时: {self.load_time:.3f}s)")
            print(f"  加载 {len(known_faces)} 个人脸特征")
            print(f"  特征矩阵形状: {self.known_embeddings.shape}")
            print(f"  缓存创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cache_data['created_time']))}")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载缓存失败: {e}")
            return False
    
    def _load_or_build_cache(self):
        """加载或构建特征向量缓存"""
        print("📚 正在加载已知人脸特征...")
        
        # 先尝试加载缓存
        if self._load_cache():
            return
        
        # 缓存不存在或无效，重新构建
        if not self._build_cache():
            raise RuntimeError("无法构建特征向量缓存，请检查已知人脸目录")
    
    def recognize_image(self, img_path: str) -> Dict:
        """
        识别单张图片
        
        Args:
            img_path: 图片路径
            
        Returns:
            识别结果字典
        """
        result = {
            'success': False,
            'filename': os.path.basename(img_path),
            'matched': False,
            'best_match': None,
            'best_distance': float('inf'),
            'best_similarity': 0.0,
            'all_results': [],
            'feature_time': 0.0,
            'match_time': 0.0,
            'total_time': 0.0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            # 特征提取
            feature_start = time.time()
            embedding = self._get_face_embedding(img_path)
            result['feature_time'] = time.time() - feature_start
            
            if embedding is None:
                result['error'] = "未检测到人脸"
                result['total_time'] = time.time() - start_time
                return result
            
            # 检查是否有已知人脸数据
            if self.known_embeddings is None:
                result['error'] = "未加载已知人脸数据"
                result['total_time'] = time.time() - start_time
                return result
            
            # 匹配计算
            match_start = time.time()
            distances = np.linalg.norm(self.known_embeddings - embedding, axis=1)
            similarities = np.dot(self.known_embeddings, embedding)
            result['match_time'] = time.time() - match_start
            
            # 处理结果
            for name, distance, similarity in zip(self.known_names, distances, similarities):
                result['all_results'].append({
                    'name': name,
                    'distance': float(distance),
                    'similarity': float(similarity),
                    'matched': bool(distance < self.threshold)
                })
                
                # 记录最佳匹配
                if distance < self.threshold and distance < result['best_distance']:
                    result['matched'] = True
                    result['best_match'] = name
                    result['best_distance'] = float(distance)
                    result['best_similarity'] = float(similarity)
            
            # 只有找到匹配时才认为识别成功
            if result['matched']:
                result['success'] = True
            else:
                result['success'] = False
                result['error'] = "未找到匹配的人脸"
            
            result['total_time'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            result['total_time'] = time.time() - start_time
        
        return result
    
    def recognize_image_array(self, img: np.ndarray, img_name: str = "photo") -> Dict:
        """
        识别图像数组
        
        Args:
            img: 图像数组
            img_name: 图像名称
            
        Returns:
            识别结果字典
        """
        result = {
            'success': False,
            'filename': img_name,
            'matched': False,
            'best_match': None,
            'best_distance': float('inf'),
            'best_similarity': 0.0,
            'all_results': [],
            'feature_time': 0.0,
            'match_time': 0.0,
            'total_time': 0.0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            # 特征提取
            feature_start = time.time()
            embedding = self._get_face_embedding_from_image(img)
            result['feature_time'] = time.time() - feature_start
            
            if embedding is None:
                result['error'] = "未检测到人脸"
                result['total_time'] = time.time() - start_time
                return result
            
            # 检查是否有已知人脸数据
            if self.known_embeddings is None:
                result['error'] = "未加载已知人脸数据"
                result['total_time'] = time.time() - start_time
                return result
            
            # 匹配计算
            match_start = time.time()
            distances = np.linalg.norm(self.known_embeddings - embedding, axis=1)
            similarities = np.dot(self.known_embeddings, embedding)
            result['match_time'] = time.time() - match_start
            
            # 处理结果
            for name, distance, similarity in zip(self.known_names, distances, similarities):
                result['all_results'].append({
                    'name': name,
                    'distance': float(distance),
                    'similarity': float(similarity),
                    'matched': bool(distance < self.threshold)
                })
                
                # 记录最佳匹配
                if distance < self.threshold and distance < result['best_distance']:
                    result['matched'] = True
                    result['best_match'] = name
                    result['best_distance'] = float(distance)
                    result['best_similarity'] = float(similarity)
            
            # 只有找到匹配时才认为识别成功
            if result['matched']:
                result['success'] = True
            else:
                result['success'] = False
                result['error'] = "未找到匹配的人脸"
            
            result['total_time'] = time.time() - start_time
            
        except Exception as e:
            result['error'] = str(e)
            result['total_time'] = time.time() - start_time
        
        return result
    
    def print_result(self, result: Dict):
        """打印识别结果"""
        print(f"\n📸 识别结果: {result['filename']}")
        print("-" * 40)
        
        if not result['success']:
            print(f"❌ 错误: {result['error']}")
            print(f"⏱️  耗时: {result['total_time']*1000:.1f}ms")
            return
        
        # 时间统计
        print(f"⏱️  时间统计:")
        print(f"  特征提取: {result['feature_time']*1000:.1f}ms")
        print(f"  匹配计算: {result['match_time']*1000:.1f}ms")
        print(f"  总耗时: {result['total_time']*1000:.1f}ms")
        
        # 匹配结果
        print(f"\n🎯 匹配结果:")
        if result['matched']:
            print(f"  🎉 匹配成功: {result['best_match']}")
            print(f"  📏 距离: {result['best_distance']:.3f}")
            print(f"  🎯 相似度: {result['best_similarity']:.3f}")
        else:
            print(f"  ❌ 未找到匹配 (阈值: {self.threshold})")
        
        # 详细结果
        print(f"\n📊 详细对比:")
        for item in result['all_results']:
            status = "✓" if item['matched'] else "✗"
            print(f"  {status} {item['name']}: 距离={item['distance']:.3f}, 相似度={item['similarity']:.3f}")
    
    def rebuild_cache(self):
        """重新构建缓存"""
        print("\n🔄 重新构建特征缓存...")
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        self._build_cache()


class CameraSimulator:
    """相机模拟器"""
    
    def __init__(self, capture_dir: str = "./capture", output_dir: str = "./captured"):
        self.capture_dir = capture_dir  # 读取图片的目录
        self.output_dir = output_dir    # 保存图片的目录
        self.captured_image = None
        self.photo_count = 0
        
        # 创建目录
        Path(self.capture_dir).mkdir(exist_ok=True)
        Path(self.output_dir).mkdir(exist_ok=True)
    
    def capture_photo(self) -> bool:
        """模拟拍照 - 实际可以连接真实摄像头"""
        print("\n📷 模拟拍照...")
        
        # 这里可以连接真实摄像头
        # 目前模拟生成一张随机图片
        height, width = 480, 640
        self.captured_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        print("✓ 拍照完成 (模拟)")
        return True
    
    def get_latest_capture_image(self) -> Optional[Tuple[np.ndarray, str]]:
        """从capture目录获取最新的图片"""
        supported_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_files = []
        
        for ext in supported_extensions:
            image_files.extend(glob.glob(os.path.join(self.capture_dir, ext)))
            image_files.extend(glob.glob(os.path.join(self.capture_dir, ext.upper())))
        
        if not image_files:
            return None
        
        # 按修改时间排序，获取最新的图片
        image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        latest_file = image_files[0]
        
        # 读取图片
        img = cv2.imread(latest_file)
        if img is None:
            return None
        
        filename = os.path.basename(latest_file)
        return img, filename
    
    def list_capture_images(self) -> List[str]:
        """列出capture目录中的所有图片"""
        supported_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        image_files = []
        
        for ext in supported_extensions:
            image_files.extend(glob.glob(os.path.join(self.capture_dir, ext)))
            image_files.extend(glob.glob(os.path.join(self.capture_dir, ext.upper())))
        
        # 按修改时间排序，最新的在前
        image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [os.path.basename(f) for f in image_files]
    
    def load_capture_image(self, filename: str) -> Optional[np.ndarray]:
        """加载capture目录中指定的图片"""
        filepath = os.path.join(self.capture_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        img = cv2.imread(filepath)
        return img
    
    def save_photo(self) -> str:
        """保存照片"""
        if self.captured_image is None:
            raise ValueError("没有可保存的照片，请先拍照")
        
        self.photo_count += 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}_{self.photo_count:03d}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        cv2.imwrite(filepath, self.captured_image)
        print(f"💾 照片已保存: {filepath}")
        
        return filepath

def recognize_face(image_path=None):
    """
    人脸识别函数
    
    参数:
        image_path: 图像文件路径
    
    返回:
        识别结果的JSON字符串
    """
    try:
        # 初始化系统（只初始化一次，不重复构建缓存）
        recognizer = FaceRecognizer()

        # 重建缓存
        # recognizer.rebuild_cache()

        # 识别图片
        result = recognizer.recognize_image(image_path)

        # 打印结果
        recognizer.print_result(result)
        
        # 返回结果
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        # 发生错误时返回错误信息
        error_result = {
            'success': False,
            'filename': os.path.basename(image_path) if image_path else "unknown",
            'matched': False,
            'best_match': None,
            'best_distance': float('inf'),
            'best_similarity': 0.0,
            'all_results': [],
            'feature_time': 0.0,
            'match_time': 0.0,
            'total_time': 0.0,
            'error': str(e)
        }
        print(f"❌ 人脸识别过程发生错误: {e}")
        return json.dumps(error_result, ensure_ascii=False)

if __name__ == "__main__":
    # 从命令行参数获取图像路径
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 执行人脸识别
    result = recognize_face(image_path)
    
    # 输出结果
    print(result) 