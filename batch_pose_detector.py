#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量低头检测程序
可以同时检测多张图片的低头状态并生成对比报告

使用方法:
1. 将要检测的图片放在当前目录下
2. 修改 image_list 变量
3. 运行: python batch_head_down_detector.py
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
from pose_detector import HeadDownDetector
import pandas as pd
import config

# 中文支持
plt.rcParams['font.family'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class BatchHeadDownDetector:
    def __init__(self):
        """初始化批量低头检测器"""
        self.detector = HeadDownDetector()
        self.results = []
    
    def analyze_multiple_images(self, image_paths, confidence_threshold=0.5):
        """
        分析多张图片的低头状态
        Args:
            image_paths: 图片路径列表
            confidence_threshold: 置信度阈值
        """
        print(f"开始批量检测 {len(image_paths)} 张图片...")
        
        for i, image_path in enumerate(image_paths):
            print(f"\n正在检测第 {i+1}/{len(image_paths)} 张图片: {os.path.basename(image_path)}")
            
            try:
                result = self.detector.analyze_image(image_path, confidence_threshold)
                result['filename'] = os.path.basename(image_path)
                result['filepath'] = image_path
                self.results.append(result)
                
                # 显示当前图片的检测结果
                detection = result['detection']
                if detection['valid']:
                    status = "✅ 正常" if not detection['is_head_down'] else f"⚠️ {detection['severity']}"
                    nose_bottom = f", 鼻子到底部: {detection['nose_to_bottom']:.1f}px" if detection['nose_to_bottom'] is not None else ""
                    myopia_status = f"👁️ {detection['myopia_risk_level']}" if detection['myopia_risk'] else "👁️ 无风险"
                    print(f"  结果: {status}{nose_bottom}, 近视风险: {myopia_status}")
                else:
                    print(f"  结果: ❌ {detection['message']}")
                    
            except Exception as e:
                print(f"  错误: {e}")
        
        print(f"\n批量检测完成！成功检测了 {len(self.results)} 张图片")
    
    def generate_comparison_report(self):
        """生成对比分析报告"""
        if not self.results:
            print("没有检测结果，请先进行图片检测")
            return
        
        print("\n" + "="*80)
        print("批量低头检测对比报告")
        print("="*80)
        
        # 创建数据表格
        data = []
        valid_results = []
        
        for result in self.results:
            detection = result['detection']
            if detection['valid']:
                valid_results.append(result)
                data.append({
                    '文件名': result['filename'],
                    '检测状态': detection['severity'],
                    '是否低头': '是' if detection['is_head_down'] else '否',
                    '垂直距离': f"{detection['vertical_distance']:.1f}px",
                    '低头程度': f"{detection['head_down_ratio']:.3f}",
                    '鼻子到底部': f"{detection['nose_to_bottom']:.1f}px" if detection['nose_to_bottom'] is not None else "N/A",
                    '近视风险': detection['myopia_risk_level'],
                    '风险级别': self._get_risk_level(detection)
                })
        
        if data:
            df = pd.DataFrame(data)
            print(df.to_string(index=False))
            
            # 统计信息
            head_down_count = sum(1 for r in valid_results if r['detection']['is_head_down'])
            normal_count = len(valid_results) - head_down_count
            
            # 近视风险统计
            myopia_risk_count = sum(1 for r in valid_results if r['detection']['myopia_risk'])
            no_myopia_risk_count = len(valid_results) - myopia_risk_count
            
            print(f"\n统计信息:")
            print(f"总检测图片数: {len(valid_results)}")
            print(f"正常姿态: {normal_count} 张 ({normal_count/len(valid_results)*100:.1f}%)")
            print(f"低头姿态: {head_down_count} 张 ({head_down_count/len(valid_results)*100:.1f}%)")
            print(f"无近视风险: {no_myopia_risk_count} 张 ({no_myopia_risk_count/len(valid_results)*100:.1f}%)")
            print(f"有近视风险: {myopia_risk_count} 张 ({myopia_risk_count/len(valid_results)*100:.1f}%)")
            
            # 低头程度分布
            severities = [r['detection']['severity'] for r in valid_results]
            severity_counts = pd.Series(severities).value_counts()
            print(f"\n低头状态分布:")
            for severity, count in severity_counts.items():
                print(f"  {severity}: {count} 张 ({count/len(valid_results)*100:.1f}%)")
                
            # 近视风险分布
            myopia_levels = [r['detection']['myopia_risk_level'] for r in valid_results]
            myopia_counts = pd.Series(myopia_levels).value_counts()
            print(f"\n近视风险分布:")
            for level, count in myopia_counts.items():
                print(f"  {level}: {count} 张 ({count/len(valid_results)*100:.1f}%)")
            
            return df
        else:
            print("没有有效的检测结果")
            return None
    
    def _get_risk_level(self, detection):
        """获取风险级别"""
        if not detection['is_head_down']:
            return "无风险"
        elif detection['severity'] == "轻微低头":
            return "低风险"
        elif detection['severity'] == "中度低头":
            return "中风险"
        else:
            return "高风险"
    
    def create_comparison_visualization(self, max_images=6):
        """
        创建可视化对比图
        Args:
            max_images: 最多显示的图片数量
        """
        if not self.results:
            print("没有检测结果，请先进行图片检测")
            return
        
        # 过滤有效结果
        valid_results = [r for r in self.results if r['detection']['valid']]
        
        if not valid_results:
            print("没有有效的检测结果")
            return
        
        # 限制显示的图片数量
        results_to_show = valid_results[:max_images]
        
        # 计算布局
        n_images = len(results_to_show)
        if n_images <= 2:
            rows, cols = 1, n_images
        elif n_images <= 4:
            rows, cols = 2, 2
        else:
            rows, cols = 2, 3
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 10))
        if rows == 1:
            axes = [axes] if cols == 1 else axes
        else:
            axes = axes.flatten()
        
        for i, result in enumerate(results_to_show):
            if i >= len(axes):
                break
                
            # 显示检测结果图片
            axes[i].imshow(cv2.cvtColor(result['image'], cv2.COLOR_BGR2RGB))
            
            # 设置标题
            detection = result['detection']
            status = detection['severity']
            distance = detection['vertical_distance']
            title = f"{result['filename']}\n{status}\n垂直距离: {distance:.1f}px"
            axes[i].set_title(title, fontsize=10)
            axes[i].axis('off')
        
        # 隐藏多余的子图
        for i in range(len(results_to_show), len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        plt.suptitle('低头检测对比结果', fontsize=16, y=0.98)
        plt.show()
        
        # 保存对比图
        comparison_path = "head_down_comparison.jpg"
        plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
        print(f"对比图已保存到: {comparison_path}")
    
    def find_extremes(self):
        """找出最严重的低头和最好的姿态"""
        valid_results = [r for r in self.results if r['detection']['valid']]
        
        if not valid_results:
            print("没有有效的检测结果")
            return
        
        # 找出最严重的低头
        head_down_results = [r for r in valid_results if r['detection']['is_head_down']]
        if head_down_results:
            worst_result = max(head_down_results, key=lambda x: x['detection']['head_down_ratio'])
            print(f"\n最严重的低头:")
            print(f"  文件: {worst_result['filename']}")
            print(f"  状态: {worst_result['detection']['severity']}")
            print(f"  垂直距离: {worst_result['detection']['vertical_distance']:.1f}px")
            print(f"  低头程度: {worst_result['detection']['head_down_ratio']:.3f}")
        
        # 找出最好的姿态
        normal_results = [r for r in valid_results if not r['detection']['is_head_down']]
        if normal_results:
            best_result = min(normal_results, key=lambda x: abs(x['detection']['vertical_distance']))
            print(f"\n最佳姿态:")
            print(f"  文件: {best_result['filename']}")
            print(f"  状态: {best_result['detection']['severity']}")
            print(f"  垂直距离: {best_result['detection']['vertical_distance']:.1f}px")
        
        if head_down_results and normal_results:
            return worst_result, best_result
        elif head_down_results:
            return worst_result, None
        elif normal_results:
            return None, best_result
        else:
            return None, None
    
    def save_detailed_report(self, filename="head_down_report.txt"):
        """保存详细检测报告到文件"""
        if not self.results:
            print("没有检测结果")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("低头检测详细报告\n")
            f.write("="*50 + "\n\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"图片 {i}: {result['filename']}\n")
                f.write("-" * 30 + "\n")
                
                detection = result['detection']
                if detection['valid']:
                    f.write(f"检测状态: {detection['severity']}\n")
                    f.write(f"是否低头: {'是' if detection['is_head_down'] else '否'}\n")
                    f.write(f"垂直距离: {detection['vertical_distance']:.1f}px\n")
                    f.write(f"低头程度: {detection['head_down_ratio']:.3f}\n")
                    if detection['nose_to_bottom'] is not None:
                        f.write(f"鼻子到底部距离: {detection['nose_to_bottom']:.1f}px\n")
                    f.write(f"近视风险: {detection['myopia_risk_level']}\n")
                    f.write(f"风险级别: {self._get_risk_level(detection)}\n")
                    
                    if detection['is_head_down']:
                        f.write("低头改善建议:\n")
                        f.write("  • 抬起头部，眼睛平视前方\n")
                        f.write("  • 调整屏幕高度到眼睛水平\n")
                        f.write("  • 保持脊柱挺直\n")
                        
                    if detection['myopia_risk']:
                        f.write("近视风险建议:\n")
                        f.write("  • 保持适当的阅读距离\n")
                        f.write("  • 避免长时间近距离用眼\n")
                        f.write("  • 定期进行眼部检查\n")
                else:
                    f.write(f"检测失败: {detection['message']}\n")
                
                f.write("\n")
        
        print(f"详细报告已保存到: {filename}")

def main():
    """主函数"""
    # 自动识别test_photos文件夹下所有图片
    folder = "test_photos"
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    if not os.path.exists(folder):
        print(f"文件夹不存在: {folder}")
        return
    image_list = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(image_extensions)]
    
    # 检查文件是否存在
    existing_images = [img for img in image_list if os.path.exists(img)]
    
    if not existing_images:
        print("="*60)
        print(f"在 {folder} 文件夹中没有找到图片文件")
        print("1. 请将要检测的图片放在 test_photos 文件夹下")
        print("2. 支持的图片格式: jpg, jpeg, png, bmp")
        print("3. 程序将通过鼻子与肩膀连线的位置关系批量判断低头状态")
        print("="*60)
        return
    
    # 创建批量检测器
    batch_detector = BatchHeadDownDetector()
    
    # 进行批量检测
    batch_detector.analyze_multiple_images(existing_images)
    
    # 生成对比报告
    df = batch_detector.generate_comparison_report()
    
    # 创建可视化对比
    batch_detector.create_comparison_visualization()
    
    # 找出极端情况
    batch_detector.find_extremes()
    
    # 保存详细报告
    batch_detector.save_detailed_report()

if __name__ == "__main__":
    main() 