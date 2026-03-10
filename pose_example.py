import cv2
import numpy as np
from ultralytics import YOLO
import matplotlib.pyplot as plt
import os

# 中文支持
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class PoseDetector:
    def __init__(self, model_path='yolo11n-pose.pt'):
        """
        初始化姿态检测器
        Args:
            model_path: YOLO模型路径，默认使用yolo11n-pose.pt
        """
        print("正在加载YOLOv11姿态检测模型...")
        self.model = YOLO(model_path)
        print("模型加载完成！")
        
    def detect_pose(self, image_path, confidence_threshold=0.5):
        """
        检测图片中的人体姿态
        Args:
            image_path: 图片路径
            confidence_threshold: 置信度阈值
        Returns:
            处理后的图片和检测结果
        """
        # 检查图片是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
            
        print(f"正在处理图片: {image_path}")
        print(f"图片尺寸: {image.shape}")
        
        # 进行姿态检测
        results = self.model(image, conf=confidence_threshold)
        
        # 绘制检测结果
        annotated_image = results[0].plot()
        
        return annotated_image, results[0]
    
    def draw_keypoints(self, image, keypoints, confidence_threshold=0.5):
        """
        在图片上绘制关键点
        Args:
            image: 输入图片
            keypoints: 关键点坐标
            confidence_threshold: 置信度阈值
        """
        # COCO 17个关键点的连接关系
        skeleton = [
            [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],
            [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],
            [8, 10], [9, 11], [2, 3], [1, 2], [1, 3],
            [2, 4], [3, 5], [4, 6], [5, 7]
        ]
        
        # 关键点名称
        keypoint_names = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
        
        if keypoints is not None and len(keypoints) > 0:
            for person_kpts in keypoints:
                # 绘制关键点
                for i, (x, y, conf) in enumerate(person_kpts):
                    if conf > confidence_threshold:
                        cv2.circle(image, (int(x), int(y)), 5, (0, 255, 0), -1)
                        cv2.putText(image, str(i), (int(x), int(y-10)), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                
                # 绘制骨架连接
                for connection in skeleton:
                    kpt1_idx, kpt2_idx = connection[0] - 1, connection[1] - 1
                    if (kpt1_idx < len(person_kpts) and kpt2_idx < len(person_kpts)):
                        x1, y1, conf1 = person_kpts[kpt1_idx]
                        x2, y2, conf2 = person_kpts[kpt2_idx]
                        
                        if conf1 > confidence_threshold and conf2 > confidence_threshold:
                            cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), 
                                   (255, 0, 0), 2)
        
        return image

def main():
    """主函数示例"""
    # 初始化姿态检测器
    detector = PoseDetector()
    
    # 示例图片路径（请替换为你的图片路径）
    image_path = "bad.jpg"
    
    # 如果没有示例图片，创建一个简单的说明
    if not os.path.exists(image_path):
        print("=" * 50)
        print("使用说明:")
        print("1. 请将要检测的图片放在当前目录下")
        print("2. 修改 image_path 变量为你的图片文件名")
        print("3. 支持的图片格式: jpg, png, bmp, etc.")
        print("=" * 50)
        
        # 创建一个示例用法函数
        demo_usage()
        return
    
    try:
        # 进行姿态检测
        result_image, detection_results = detector.detect_pose(image_path, confidence_threshold=0.3)
        
        # 显示结果
        plt.figure(figsize=(12, 8))
        plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
        plt.title('YOLOv11 人体姿态检测结果')
        plt.axis('off')
        plt.show()
        
        # 打印检测信息
        if detection_results.keypoints is not None:
            num_persons = len(detection_results.keypoints.data)
            print(f"检测到 {num_persons} 个人")
            
            for i, person_keypoints in enumerate(detection_results.keypoints.data):
                print(f"人员 {i+1}: 检测到 {len(person_keypoints)} 个关键点")
        
        # 保存结果
        output_path = "pose_detection_result.jpg"
        cv2.imwrite(output_path, result_image)
        print(f"检测结果已保存到: {output_path}")
        
    except Exception as e:
        print(f"错误: {e}")

def demo_usage():
    """演示如何使用这个脚本"""
    print("\n代码使用示例:")
    print("""
# 基本使用方法
from temp import PoseDetector

# 1. 创建检测器实例
detector = PoseDetector()

# 2. 检测图片中的姿态
image_path = "your_image.jpg"
result_image, results = detector.detect_pose(image_path)

# 3. 显示或保存结果
import cv2
cv2.imshow('结果', result_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# 或者保存到文件
cv2.imwrite('output.jpg', result_image)
""")

if __name__ == "__main__":
    main()
