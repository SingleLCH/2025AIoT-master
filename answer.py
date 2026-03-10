#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON API 使用示例脚本
演示如何使用API提交学生问题

运行方式：
python json_api_example.py
"""

import requests
import json
import base64
import os

# API服务器地址
API_BASE_URL = "http://poem.e5.luyouxia.net:21387/"  # 根据实际情况修改

def encode_image_to_base64(image_path):
    """将图片文件编码为base64字符串"""
    try:
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"编码图片失败: {e}")
        return ""

def submit_single_question():
    """提交单个问题示例"""
    print("=== 提交单个问题示例 ===")
    
    # 准备数据
    question_data = {
        "student_name": "暴薨于",
        "gender": "三年级",
        "des": "数学", 
        "details": "太难了",
        "picture": ""  # 在这里填入图片的base64编码
    }
    
    # 如果有图片文件，可以这样编码
    # image_path = "test.png"  # 图片路径
    # if os.path.exists(image_path):
    #     question_data["picture"] = encode_image_to_base64(image_path)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/student/submit_json",
            json=question_data,
            headers={'Content-Type': 'application/json'}
        )
        
        result = response.json()
        print(f"响应状态码: {response.status_code}")
        print(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get('success'):
            print("✅ 问题提交成功！")
        else:
            print(f"❌ 问题提交失败: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

def submit_multiple_questions():
    """提交多个问题示例（数组格式）"""
    print("\n=== 提交多个问题示例 ===")
    
    # 准备多个问题数据
    questions_data = [
        {
            "student_name": "张三",
            "gender": "高一",
            "des": "物理",
            "details": "力学问题不太理解",
            "picture": ""
        },
        {
            "student_name": "李四", 
            "gender": "初二",
            "des": "英语",
            "details": "语法有困难",
            "picture": ""
        },
        {
            "student_name": "王五",
            "gender": "高三",
            "des": "化学", 
            "details": "有机化学反应机理",
            "picture": ""
        }
    ]
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/student/submit_json",
            json=questions_data,
            headers={'Content-Type': 'application/json'}
        )
        
        result = response.json()
        print(f"响应状态码: {response.status_code}")
        print(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get('success'):
            print("✅ 问题提交成功！")
        else:
            print(f"❌ 问题提交失败: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

def submit_question_with_image():
    """提交包含图片的问题示例"""
    print("\n=== 提交包含图片的问题示例 ===")
    
    # 检查是否有测试图片
    image_path = "test.png"
    image_base64 = ""
    
    if os.path.exists(image_path):
        image_base64 = encode_image_to_base64(image_path)
        print(f"✅ 找到图片文件 {image_path}，已编码为base64")
    else:
        print(f"⚠️  未找到图片文件 {image_path}，将提交不包含图片的问题")
    
    question_data = {
        "student_name": "赵六",
        "gender": "高二", 
        "des": "数学",
        "details": "这道几何题怎么解？",
        "picture": image_base64
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/student/submit_json",
            json=question_data,
            headers={'Content-Type': 'application/json'}
        )
        
        result = response.json()
        print(f"响应状态码: {response.status_code}")
        print(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get('success'):
            print("✅ 问题提交成功！")
        else:
            print(f"❌ 问题提交失败: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

def test_api_connection():
    """测试API连接"""
    print("=== 测试API连接 ===")
    try:
        response = requests.get(f"{API_BASE_URL}/zhuye")
        if response.status_code == 200:
            print("✅ API服务器连接正常")
            return True
        else:
            print(f"❌ API服务器响应异常，状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到API服务器: {e}")
        print(f"请确保服务器运行在 {API_BASE_URL}")
        return False

def main():
    """主函数"""
    print("📚 JSON API 使用示例脚本")
    print("=" * 50)
    
    # 测试连接
    if not test_api_connection():
        print("\n请先启动服务器，然后重新运行此脚本")
        return
    
    # 执行示例
    submit_single_question()
    submit_multiple_questions()
    submit_question_with_image()
    
    print("\n=" * 50)
    print("📝 API使用说明：")
    print("1. API端点: POST /api/student/submit_json")
    print("2. Content-Type: application/json")
    print("3. 数据格式: 支持单个对象或对象数组")
    print("4. 必填字段: student_name, gender, des, details")
    print("5. 可选字段: picture (图片的base64编码)")
    print("6. gender字段实际存储的是年级信息")

if __name__ == "__main__":
    main() 