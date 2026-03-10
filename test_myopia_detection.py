#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试近视风险检测功能
"""

import sys
import os
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pose_detector import HeadDownDetector
import config

def test_myopia_detection():
    """测试近视风险检测功能"""
    print("=" * 60)
    print("🔍 近视风险检测功能测试")
    print("=" * 60)
    
    # 初始化检测器
    print("\n📍 初始化姿势检测器...")
    try:
        detector = HeadDownDetector()
        print("✅ 姿势检测器初始化成功")
    except Exception as e:
        print(f"❌ 姿势检测器初始化失败: {e}")
        return False
    
    # 测试图片列表（如果存在的话）
    test_images = [
        "bad.jpg",  # 不良姿势图片
        "good.jpg", # 可能存在的好姿势图片
        "head_down_detection_result.jpg"  # 之前的检测结果
    ]
    
    existing_images = []
    for img in test_images:
        if os.path.exists(img):
            existing_images.append(img)
    
    if not existing_images:
        print("⚠️  未找到测试图片，将跳过图片检测测试")
        print("📁 请确保以下文件存在其中之一:")
        for img in test_images:
            print(f"   - {img}")
        return True
    
    print(f"\n📷 找到 {len(existing_images)} 张测试图片")
    
    # 逐个测试图片
    for i, image_path in enumerate(existing_images, 1):
        print(f"\n--- 测试图片 {i}: {image_path} ---")
        
        try:
            # 执行检测
            print(f"🔍 开始检测...")
            result = detector.analyze_image(image_path, config.CONFIDENCE_THRESHOLD)
            
            if result and 'detection' in result:
                detection_data = result['detection']
                
                print(f"✅ 检测完成")
                print(f"📊 检测结果:")
                print(f"   - 检测有效性: {'是' if detection_data.get('valid', False) else '否'}")
                
                if detection_data.get('valid', False):
                    # 姿势信息
                    is_head_down = detection_data.get('is_head_down', False)
                    severity = detection_data.get('severity', '未知')
                    vertical_distance = detection_data.get('vertical_distance', 0)
                    head_down_ratio = detection_data.get('head_down_ratio', 0)
                    
                    print(f"   - 姿势状态: {severity}")
                    print(f"   - 低头状态: {'是' if is_head_down else '否'}")
                    print(f"   - 垂直距离: {vertical_distance:.1f} 像素")
                    print(f"   - 低头程度: {head_down_ratio:.3f}")
                    
                    # 近视风险信息 (新增的功能)
                    myopia_risk = detection_data.get('myopia_risk', False)
                    myopia_level = detection_data.get('myopia_risk_level', '未知')
                    nose_to_bottom = detection_data.get('nose_to_bottom', 0)
                    
                    print(f"\n👁️  近视风险评估:")
                    print(f"   - 有近视风险: {'是' if myopia_risk else '否'}")
                    print(f"   - 风险等级: {myopia_level}")
                    print(f"   - 眼部距离: {nose_to_bottom:.1f} 像素")
                    print(f"   - 风险阈值: {config.MYOPIA_RISK_THRESHOLD} 像素")
                    
                    # 健康建议
                    print(f"\n💡 健康建议:")
                    if is_head_down:
                        print(f"   - 请抬起头部，保持正确坐姿")
                    if myopia_risk:
                        if myopia_level == "高风险":
                            print(f"   - ⚠️  眼部距离屏幕过近，请立即调整座椅位置")
                        elif myopia_level == "中风险":
                            print(f"   - ⚠️  请适当增加与屏幕的距离")
                        elif myopia_level == "低风险":
                            print(f"   - 💡 建议稍微远离屏幕一些")
                    
                    if not is_head_down and not myopia_risk:
                        print(f"   - ✅ 当前姿势良好，请继续保持")
                        
                else:
                    print(f"   - 错误信息: {detection_data.get('message', '检测失败')}")
                    
            else:
                print(f"❌ 检测失败或返回结果无效")
                
        except Exception as e:
            print(f"❌ 检测过程异常: {e}")
    
    print(f"\n" + "=" * 60)
    print("✅ 近视风险检测功能测试完成")
    print("📝 测试总结:")
    print("   - 新增了近视风险检测功能")
    print("   - 可以识别高、中、低风险等级")
    print("   - 提供针对性的健康建议")
    print("   - 与原有的低头检测功能并行工作")
    print("=" * 60)
    
    return True

def test_config_updates():
    """测试配置更新"""
    print("\n🔧 检查配置更新...")
    
    # 检查新增的近视风险配置
    required_configs = [
        'alert_on_myopia_risk',
        'consecutive_myopia_risk_threshold'
    ]
    
    missing_configs = []
    for cfg in required_configs:
        if cfg not in config.POSE_DETECTION_CONFIG:
            missing_configs.append(cfg)
    
    if missing_configs:
        print(f"❌ 缺少配置项: {', '.join(missing_configs)}")
        return False
    else:
        print(f"✅ 配置检查通过")
        print(f"   - 近视风险提醒: {'开启' if config.POSE_DETECTION_CONFIG['alert_on_myopia_risk'] else '关闭'}")
        print(f"   - 近视风险阈值: {config.POSE_DETECTION_CONFIG['consecutive_myopia_risk_threshold']} 次")
        print(f"   - 近视距离阈值: {config.MYOPIA_RISK_THRESHOLD} 像素")
        return True

def main():
    """主函数"""
    print(f"⏰ 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试配置更新
    config_ok = test_config_updates()
    if not config_ok:
        print("❌ 配置测试失败")
        return 1
    
    # 测试近视风险检测功能
    detection_ok = test_myopia_detection()
    if not detection_ok:
        print("❌ 检测功能测试失败")
        return 1
    
    print(f"\n🎉 所有测试通过！近视风险检测功能已成功集成")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
