#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低头检测程序
通过判断鼻子是否低于肩膀连线来检测低头状态

使用方法:
1. 将图片放在当前目录下
2. 修改 IMAGE_PATH 变量
3. 运行: python head_down_detector.py
"""

import cv2
import numpy as np
import subprocess
import os
import re
from ultralytics import YOLO
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import config

# 中文支持
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class HeadDownDetector:
    def __init__(self, model_path='yolo11n-pose.pt'):
        """
        初始化低头检测器
        Args:
            model_path: YOLO模型路径
        """
        print("正在加载YOLOv11姿态检测模型...")
        self.model = YOLO(model_path)
        print("模型加载完成！")
        
        # 关键点索引
        self.NOSE = 0
        self.LEFT_SHOULDER = 5
        self.RIGHT_SHOULDER = 6
        
        # 尝试加载中文字体
        self.font = self._load_chinese_font()
    
    def _load_chinese_font(self):
        """加载中文字体"""
        try:
            # Linux系统中文字体路径
            linux_font_paths = [
                # Ubuntu/Debian 系统字体
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",    # 文泉驿正黑
                "/usr/share/fonts/truetype/arphic/ukai.ttc",       # AR PL UKai
                "/usr/share/fonts/truetype/arphic/uming.ttc",      # AR PL UMing
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                
                # CentOS/RHEL/Fedora 系统字体
                "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
                "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
                "/usr/share/fonts/chinese/TrueType/ukai.ttf",
                "/usr/share/fonts/chinese/TrueType/uming.ttf",
                
                # 其他可能的位置
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/droid/DroidSansFallback.ttf",
                
                # Windows字体
                "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
                "C:/Windows/Fonts/msyh.ttf",    # Windows 微软雅黑
                
                # macOS字体
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",
            ]
            
            print("正在查找中文字体...")
            for font_path in linux_font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 20)
                        print(f"成功加载字体: {font_path}")
                        return font
                    except Exception as e:
                        print(f"字体加载失败 {font_path}: {e}")
                        continue
            
            # 如果没有找到任何字体，尝试使用系统默认字体
            print("未找到中文字体，尝试安装字体包...")
            try:
                # 尝试使用系统命令安装字体包
                import subprocess
                try:
                    # Ubuntu/Debian
                    subprocess.run(['sudo', 'apt-get', 'update'], check=False, capture_output=True)
                    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'fonts-wqy-microhei'], check=False, capture_output=True)
                    print("尝试安装了fonts-wqy-microhei字体包")
                except:
                    pass
                
                try:
                    # CentOS/RHEL/Fedora
                    subprocess.run(['sudo', 'yum', 'install', '-y', 'wqy-microhei-fonts'], check=False, capture_output=True)
                    print("尝试安装了wqy-microhei-fonts字体包")
                except:
                    pass
                    
            except Exception as e:
                print(f"自动安装字体失败: {e}")
            
            # 再次尝试加载字体
            for font_path in linux_font_paths[:6]:  # 只检查前几个常用路径
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 20)
                        print(f"安装后成功加载字体: {font_path}")
                        return font
                    except:
                        continue
            
            print("使用默认字体（可能无法显示中文）")
            return ImageFont.load_default()
            
        except Exception as e:
            print(f"字体加载异常: {e}")
            return ImageFont.load_default()

    def put_chinese_text(self, image, text, position, font_size=20, color=(255, 255, 255)):
        """
        在图像上绘制中文文本
        Args:
            image: OpenCV图像 (numpy array)
            text: 要绘制的文本
            position: 文本位置 (x, y)
            font_size: 字体大小
            color: 文本颜色 (B, G, R)
        Returns:
            绘制文本后的图像
        """
        try:
            # 将OpenCV图像转换为PIL图像
            image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(image_pil)
            
            # 创建字体对象
            try:
                if hasattr(self.font, 'path') and self.font.path:
                    font = ImageFont.truetype(self.font.path, font_size)
                else:
                    # 如果没有路径属性，尝试重新加载字体
                    font = self._load_chinese_font()
                    if hasattr(font, 'path'):
                        font = ImageFont.truetype(font.path, font_size)
                    else:
                        font = ImageFont.load_default()
            except Exception as e:
                print(f"字体加载失败，使用默认字体: {e}")
                font = ImageFont.load_default()
                
            # 转换颜色格式 (BGR -> RGB)
            rgb_color = (color[2], color[1], color[0])
            
            # 绘制文本
            draw.text(position, text, font=font, fill=rgb_color)
            
            # 转换回OpenCV格式
            return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"绘制文本失败: {e}")
            # 如果PIL方法失败，回退到OpenCV的putText（但不支持中文）
            try:
                cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                           font_size/20, color, 2, cv2.LINE_AA)
            except:
                # 如果连OpenCV也失败，只绘制英文替代文本
                english_text = "Text Display Error"
                cv2.putText(image, english_text, position, cv2.FONT_HERSHEY_SIMPLEX, 
                           font_size/20, color, 2, cv2.LINE_AA)
            return image

    def detect_head_down(self, keypoints, confidence_threshold=0.5, image_height=None):
        """
        检测低头状态
        Args:
            keypoints: 关键点数据
            confidence_threshold: 置信度阈值
            image_height: 图片高度（用于计算鼻子到底部的距离）
        Returns:
            检测结果字典
        """
        # 获取关键点坐标
        nose = keypoints[self.NOSE]
        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]
        
        # 检查关键点置信度
        if (nose[2] < confidence_threshold or 
            left_shoulder[2] < confidence_threshold or 
            right_shoulder[2] < confidence_threshold):
            return {
                'valid': False,
                'message': '关键点置信度不足，无法准确检测'
            }
        
        # 计算肩膀连线的中点和y坐标
        shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
        shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
        shoulder_line_y = shoulder_center_y  # 肩膀连线的y坐标
        
        # 获取鼻子的坐标
        nose_x = nose[0]
        nose_y = nose[1]
        
        # 计算鼻子相对于肩膀连线的垂直距离
        vertical_distance = nose_y - shoulder_line_y
        
        # 计算鼻子到图片底部的距离
        nose_to_bottom = image_height - nose_y if image_height else None
        
        # 近视风险检测
        myopia_risk = False
        myopia_risk_level = "无风险"
        myopia_risk_color = (0, 255, 0)  # 绿色
        
        if nose_to_bottom is not None:
            if nose_to_bottom < config.MYOPIA_RISK_THRESHOLD:
                myopia_risk = True
                # 根据距离程度分级
                if nose_to_bottom < config.MYOPIA_RISK_THRESHOLD * 0.8:  # 小于120px
                    myopia_risk_level = "高风险"
                    myopia_risk_color = (0, 0, 255)  # 红色
                elif nose_to_bottom < config.MYOPIA_RISK_THRESHOLD * 0.9:  # 小于160px
                    myopia_risk_level = "中风险" 
                    myopia_risk_color = (0, 165, 255)  # 橙色
                else:  # 小于200px但大于160px
                    myopia_risk_level = "低风险"
                    myopia_risk_color = (0, 255, 255)  # 黄色
        
        # 判断低头状态
        is_head_down = vertical_distance > 0  # 鼻子y坐标大于肩膀连线y坐标表示低头
        
        # 计算低头程度
        if is_head_down:
            # 计算头部到肩膀的距离作为参考
            head_shoulder_distance = np.sqrt((nose_x - shoulder_center_x)**2 + 
                                           (nose_y - shoulder_center_y)**2)
            
            # 计算低头程度比例
            if head_shoulder_distance > 0:
                head_down_ratio = abs(vertical_distance) / head_shoulder_distance
            else:
                head_down_ratio = 0
            
            # 低头程度分级
            if head_down_ratio > 0.3:
                severity = "严重低头"
                color = (0, 0, 255)  # 红色
            elif head_down_ratio > 0.15:
                severity = "中度低头"
                color = (0, 165, 255)  # 橙色
            else:
                severity = "轻微低头"
                color = (0, 255, 255)  # 黄色
        else:
            head_down_ratio = 0
            severity = "正常"
            color = (0, 255, 0)  # 绿色
        
        return {
            'valid': True,
            'is_head_down': is_head_down,
            'vertical_distance': vertical_distance,
            'head_down_ratio': head_down_ratio,
            'severity': severity,
            'color': color,
            'nose_position': (nose_x, nose_y),
            'nose_to_bottom': nose_to_bottom,
            'shoulder_line_y': shoulder_line_y,
            'shoulder_center': (shoulder_center_x, shoulder_center_y),
            'left_shoulder': (left_shoulder[0], left_shoulder[1]),
            'right_shoulder': (right_shoulder[0], right_shoulder[1]),
            'myopia_risk': myopia_risk,
            'myopia_risk_level': myopia_risk_level,
            'myopia_risk_color': myopia_risk_color
        }

    def draw_detection_result(self, image, detection_result):
        """
        在图像上绘制检测结果
        Args:
            image: 原始图像
            detection_result: 检测结果
        Returns:
            绘制结果的图像
        """
        if not detection_result['valid']:
            image = self.put_chinese_text(image, detection_result['message'], 
                                        (10, 30), 20, (0, 0, 255))
            return image
        
        # 获取坐标信息
        nose_pos = detection_result['nose_position']
        shoulder_line_y = detection_result['shoulder_line_y']
        shoulder_center = detection_result['shoulder_center']
        left_shoulder = detection_result['left_shoulder']
        right_shoulder = detection_result['right_shoulder']
        
        # 绘制关键点
        # 鼻子
        cv2.circle(image, (int(nose_pos[0]), int(nose_pos[1])), 8, (255, 0, 0), -1)
        
        # 肩膀
        cv2.circle(image, (int(left_shoulder[0]), int(left_shoulder[1])), 8, (0, 255, 0), -1)
        cv2.circle(image, (int(right_shoulder[0]), int(right_shoulder[1])), 8, (0, 255, 0), -1)
        
        # 绘制肩膀连线
        cv2.line(image, (int(left_shoulder[0]), int(left_shoulder[1])), 
                (int(right_shoulder[0]), int(right_shoulder[1])), (0, 255, 0), 3)
        
        # 绘制肩膀连线延长线（用于参考）
        line_extend = 100
        cv2.line(image, (int(left_shoulder[0] - line_extend), int(shoulder_line_y)), 
                (int(right_shoulder[0] + line_extend), int(shoulder_line_y)), 
                (0, 255, 0), 2)
        
        # 绘制鼻子到肩膀连线的垂直线
        cv2.line(image, (int(nose_pos[0]), int(nose_pos[1])), 
                (int(nose_pos[0]), int(shoulder_line_y)), (255, 0, 255), 2)
        
        # 绘制鼻子到肩膀中心的连线
        cv2.line(image, (int(nose_pos[0]), int(nose_pos[1])), 
                (int(shoulder_center[0]), int(shoulder_center[1])), (255, 255, 0), 2)
        
        # 绘制检测结果文本
        image = self.put_chinese_text(image, "低头检测", (10, 10), 24, (255, 255, 255))
        
        # 检测状态
        status_text = f"检测状态: {detection_result['severity']}"
        image = self.put_chinese_text(image, status_text, (10, 45), 20, detection_result['color'])
        
        # 近视风险状态
        myopia_text = f"近视风险: {detection_result['myopia_risk_level']}"
        image = self.put_chinese_text(image, myopia_text, (10, 75), 20, detection_result['myopia_risk_color'])
        
        # 详细数据
        y_pos = 105
        distance_text = f"垂直距离: {detection_result['vertical_distance']:.1f}像素"
        image = self.put_chinese_text(image, distance_text, (10, y_pos), 16, (255, 255, 255))
        
        y_pos += 25
        ratio_text = f"低头程度: {detection_result['head_down_ratio']:.3f}"
        image = self.put_chinese_text(image, ratio_text, (10, y_pos), 16, (255, 255, 255))
        
        y_pos += 25
        if detection_result['nose_to_bottom'] is not None:
            bottom_text = f"鼻子到底部: {detection_result['nose_to_bottom']:.1f}像素"
            image = self.put_chinese_text(image, bottom_text, (10, y_pos), 16, (255, 255, 255))
        
        # 判断说明
        y_pos += 35
        if detection_result['is_head_down']:
            explanation = "鼻子低于肩膀连线 - 检测到低头"
            image = self.put_chinese_text(image, explanation, (10, y_pos), 16, (255, 100, 100))
        else:
            explanation = "鼻子高于肩膀连线 - 姿态正常"
            image = self.put_chinese_text(image, explanation, (10, y_pos), 16, (100, 255, 100))
        
        # 添加改善建议
        if detection_result['is_head_down']:
            y_pos += 35
            image = self.put_chinese_text(image, "建议:", (10, y_pos), 16, (0, 255, 255))
            y_pos += 22
            image = self.put_chinese_text(image, "• 抬起头部，眼睛平视前方", (10, y_pos), 14, (200, 200, 200))
            y_pos += 20
            image = self.put_chinese_text(image, "• 调整屏幕高度到眼睛水平", (10, y_pos), 14, (200, 200, 200))
            y_pos += 20
            image = self.put_chinese_text(image, "• 保持脊柱挺直", (10, y_pos), 14, (200, 200, 200))
        
        # 近视风险提示
        if detection_result['myopia_risk']:
            y_pos += 35
            image = self.put_chinese_text(image, "近视风险:", (10, y_pos), 16, (255, 0, 0))
            y_pos += 22
            image = self.put_chinese_text(image, f"风险等级: {detection_result['myopia_risk_level']}", (10, y_pos), 14, detection_result['myopia_risk_color'])
            y_pos += 20
            image = self.put_chinese_text(image, "建议:", (10, y_pos), 14, (0, 255, 255))
            y_pos += 20
            image = self.put_chinese_text(image, "• 保持正确的坐姿，避免长时间低头", (10, y_pos), 14, (200, 200, 200))
            y_pos += 20
            image = self.put_chinese_text(image, "• 定期进行眼部检查", (10, y_pos), 14, (200, 200, 200))
            y_pos += 20
            image = self.put_chinese_text(image, "• 注意用眼卫生，避免过度疲劳", (10, y_pos), 14, (200, 200, 200))
        
        return image

    def analyze_frame(self, image_frame, confidence_threshold=0.5):
        """
        分析图片帧中的低头状态
        Args:
            image_frame: 图片帧对象 (numpy array)
            confidence_threshold: 置信度阈值
        Returns:
            分析结果
        """
        if image_frame is None:
            raise ValueError("图片帧为空")
        
        print(f"正在分析图片帧，尺寸: {image_frame.shape}")
        
        # 进行姿态检测
        results = self.model(image_frame, conf=confidence_threshold)
        
        if len(results[0].keypoints.data) == 0:
            raise ValueError("未检测到人体，请确保图片中有清晰的人体上半身")
        
        # 获取第一个检测到的人的关键点
        keypoints = results[0].keypoints.data[0].cpu().numpy()
        
        # 获取图片高度
        image_height = image_frame.shape[0]
        
        # 进行低头检测
        detection_result = self.detect_head_down(keypoints, confidence_threshold, image_height)
        
        # 绘制检测结果
        result_image = image_frame.copy()
        result_image = self.draw_detection_result(result_image, detection_result)
        
        return {
            'image': result_image,
            'detection': detection_result,
            'keypoints': keypoints
        }

    def analyze_image(self, image_path, confidence_threshold=0.5):
        """
        分析图片中的低头状态
        Args:
            image_path: 图片路径
            confidence_threshold: 置信度阈值
        Returns:
            分析结果
        """
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        print(f"正在分析图片: {image_path}")
        
        # 进行姿态检测
        results = self.model(image, conf=confidence_threshold)
        
        if len(results[0].keypoints.data) == 0:
            raise ValueError("未检测到人体，请确保图片中有清晰的人体上半身")
        
        # 获取第一个检测到的人的关键点
        keypoints = results[0].keypoints.data[0].cpu().numpy()
        
        # 获取图片高度
        image_height = image.shape[0]
        
        # 进行低头检测
        detection_result = self.detect_head_down(keypoints, confidence_threshold, image_height)
        
        # 绘制检测结果
        result_image = image.copy()
        result_image = self.draw_detection_result(result_image, detection_result)
        
        return {
            'image': result_image,
            'detection': detection_result,
            'keypoints': keypoints
        }

def main():
    """主函数"""
    # 配置参数
    IMAGE_PATH = "bad.jpg"  # 修改为你的图片路径
    CONFIDENCE_THRESHOLD = 0.5
    
    # 初始化检测器
    detector = HeadDownDetector()
    
    # 检查图片是否存在
    if not os.path.exists(IMAGE_PATH):
        print("=" * 60)
        print("低头检测程序使用说明:")
        print("1. 请将要检测的图片放在当前目录下")
        print("2. 修改 IMAGE_PATH 变量为你的图片文件名")
        print("3. 确保图片包含清晰的人体上半身正面照")
        print("4. 程序将通过鼻子与肩膀连线的位置关系判断低头状态")
        print("=" * 60)
        return
    
    try:
        # 进行低头检测
        result = detector.analyze_image(IMAGE_PATH, CONFIDENCE_THRESHOLD)
        
        # 显示结果
        plt.figure(figsize=(12, 8))
        plt.imshow(cv2.cvtColor(result['image'], cv2.COLOR_BGR2RGB))
        plt.title('低头检测结果')
        plt.axis('off')
        plt.show()
        
        # 打印详细检测结果
        detection = result['detection']
        if detection['valid']:
            print("\n" + "="*50)
            print("低头检测分析报告")
            print("="*50)
            print(f"检测状态: {detection['severity']}")
            print(f"是否低头: {'是' if detection['is_head_down'] else '否'}")
            print(f"垂直距离: {detection['vertical_distance']:.1f} 像素")
            print(f"低头程度: {detection['head_down_ratio']:.3f}")
            if detection['nose_to_bottom'] is not None:
                print(f"鼻子到底部距离: {detection['nose_to_bottom']:.1f} 像素")
            print(f"近视风险: {detection['myopia_risk_level']}")
            
            if detection['is_head_down']:
                print(f"\n⚠️  检测到低头行为！")
                print(f"建议:")
                print(f"  • 抬起头部，眼睛平视前方")
                print(f"  • 调整屏幕高度到眼睛水平")
                print(f"  • 保持脊柱挺直")
            else:
                print(f"\n✅ 坐姿正常，继续保持！")
                
            if detection['myopia_risk']:
                print(f"\n👁️  检测到近视风险！")
                print(f"风险等级: {detection['myopia_risk_level']}")
                print(f"建议:")
                print(f"  • 保持适当的阅读距离")
                print(f"  • 避免长时间近距离用眼")
                print(f"  • 定期进行眼部检查")
            else:
                print(f"\n��️  眼部距离适宜，无近视风险！")
        else:
            print(f"\n❌ {detection['message']}")
        
        # 保存结果
        output_path = "head_down_detection_result.jpg"
        cv2.imwrite(output_path, result['image'])
        print(f"\n检测结果已保存到: {output_path}")
        
    except Exception as e:
        print(f"检测过程中出现错误: {e}")

if __name__ == "__main__":
    main() 