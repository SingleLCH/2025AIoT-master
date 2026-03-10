# -*- coding: utf-8 -*-
"""
思路解答上传脚本
复用作业批改的上传逻辑，但修改提示词只提供解题思路，不给出答案
"""

import os
import json
import base64
import re
from openai import OpenAI

def main():
    # 设置图片文件夹路径
    image_folder = "paper_photos"
    
    # 获取图片文件列表
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
    image_paths = []
    
    if os.path.exists(image_folder):
        for filename in os.listdir(image_folder):
            if filename.lower().endswith(image_extensions):
                image_paths.append(os.path.join(image_folder, filename))
    
    if not image_paths:
        print("❌ 没有找到可处理的图片文件")
        return False
    
    print(f"📷 找到 {len(image_paths)} 个图片文件")
    for path in image_paths:
        print(f"  - {os.path.basename(path)}")
    
    # 构建 image_url 消息列表
    image_messages = []
    for i, path in enumerate(image_paths):
        # 检查图片文件是否存在且可读取
        if not os.path.isfile(path):
            print(f"⚠️ 警告：图片文件 {path} 不存在，跳过")
            continue
            
        # 对于DashScope，需要将图片转换为base64格式
        try:
            with open(path, "rb") as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                # 构建data URL格式
                data_url = f"data:image/png;base64,{base64_image}"
                
            image_messages.append({
                "type": "image_url",
                "image_url": {
                    "url": data_url  # 使用base64编码的data URL
                }
            })
            print(f"  ✅ 图片 {os.path.basename(path)} 已转换为base64格式")
            
        except Exception as e:
            print(f"  ❌ 读取图片 {path} 失败: {e}")
            continue
    
    if not image_messages:
        print("❌ 没有有效的图片文件可以处理")
        return False
    
    # 添加思路解答专用提示词
    image_messages.append({
        "type": "text",
        "text": (
            "这是一份学生作业题目，请仔细分析并提供解题思路指导。\n\n"
            "重要要求：\n"
            "1. 必须按照当前学生的思路提供解题思路和方法，绝对不要给出具体答案或计算结果，不要随意发挥\n"
            "2. 必须严格按照下面的JSON格式返回，不要添加任何其他内容\n"
            "3. 直接输出纯JSON，不要使用代码块标记（如```json```）\n\n"
            "JSON格式模板：\n"
            '{\n'
            '  "thinking_process": "这里写详细的解题思路分析过程，说明如何分析这类题目",\n'
            '  "key_points": ["关键解题步骤1", "关键解题步骤2", "关键解题步骤3"],\n'
            '  "knowledge_areas": ["相关知识点1", "相关知识点2"],\n'
            '  "tips": ["解题技巧1", "注意事项2"]\n'
            '}\n\n'
            "字段说明：\n"
            "- thinking_process: 详细分析解题思路，帮助学生理解解题方法，详细一点\n"
            "- key_points: 列出解题的关键步骤（3-5个），只说方法不给答案，详细一点\n"
            "- knowledge_areas: 涉及的知识点或概念（2-4个）\n"
            "- tips: 解题技巧和注意事项，详细一点，不要只说大概\n\n"
            "请直接返回JSON格式的内容，不要有任何前缀或后缀。"
        )
    })
    
    try:
        # 从环境变量获取 API 密钥
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ 错误：请设置环境变量 DASHSCOPE_API_KEY")
            print("💡 获取API Key: https://help.aliyun.com/zh/dashscope/developer-reference/activate-dashscope-and-create-an-api-key")
            return False
        
        # 初始化 DashScope（通义千问）客户端
        print("\n🔄 正在连接通义千问API...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 发起流式请求 - 使用通义千问-QVQ-Plus
        print("📤 正在发送请求到模型...")
        completion = client.chat.completions.create(
            model="qvq-plus",  # 使用通义千问-QVQ-Plus模型
            messages=[
                {
                    "role": "user",
                    "content": image_messages
                }
            ],
            stream=True,
        )
        
        # 初始化内容变量
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")
        
        # 处理流式响应
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                
                # 检查是否进入答案阶段
                if "<answer>" in content:
                    is_answering = True
                    content = content.replace("<answer>", "")
                elif "</answer>" in content:
                    content = content.replace("</answer>", "")
                    break
                
                # 根据阶段处理内容
                if is_answering:
                    answer_content += content
                    print(content, end="", flush=True)
                else:
                    reasoning_content += content
                    print(content, end="", flush=True)
        
        print("\n\n" + "=" * 20 + "处理完成" + "=" * 20 + "\n")
        
        # 🔧 思路解答场景特殊处理：如果answer_content为空，尝试从reasoning_content获取JSON
        if not answer_content.strip() and reasoning_content.strip():
            print("🔍 检测到思路解答场景：answer_content为空，尝试从reasoning_content获取JSON数据")
            print(f"reasoning_content长度: {len(reasoning_content)}")
            
            # 检查reasoning_content是否包含JSON数据
            if '{' in reasoning_content and '}' in reasoning_content:
                print("✅ reasoning_content包含JSON数据，转移到answer_content进行解析")
                answer_content = reasoning_content
                reasoning_content = "AI思路解答分析过程"  # 保留一个简单的说明
            else:
                print("⚠️ reasoning_content不包含JSON数据")
        
        # 解析JSON结果 - 使用多重策略
        try:
            print(f"🔍 开始解析JSON，原始内容长度: {len(answer_content)}")
            print(f"原始内容前200字符: {answer_content[:200]}")
            
            result_json = None
            json_str = None
            
            # 方式1：直接尝试解析整个回复
            try:
                result_json = json.loads(answer_content.strip())
                json_str = answer_content.strip()
                print("✅ 方式1成功：直接解析整个回复")
            except json.JSONDecodeError:
                print("⚠️ 方式1失败：直接解析")
            
            # 方式2：去除代码块标记后解析
            if not result_json:
                try:
                    clean_content = answer_content.strip()
                    
                    # 去掉 ```json 和 ``` 标记（如果存在）
                    if clean_content.startswith('```json'):
                        clean_content = clean_content[7:]  # 去掉 ```json
                    elif clean_content.startswith('```'):
                        clean_content = clean_content[3:]   # 去掉 ```
                        
                    if clean_content.endswith('```'):
                        clean_content = clean_content[:-3]  # 去掉结尾的 ```
                        
                    clean_content = clean_content.strip()
                    result_json = json.loads(clean_content)
                    json_str = clean_content
                    print("✅ 方式2成功：去除代码块标记后解析")
                except json.JSONDecodeError:
                    print("⚠️ 方式2失败：代码块清理")
            
            # 方式3：使用正则表达式查找JSON对象（查找包含必需字段的JSON）
            if not result_json:
                try:
                    # 查找包含思路解答必需字段的JSON对象
                    json_pattern = r'\{[^{}]*"thinking_process"[^{}]*"key_points"[^{}]*"knowledge_areas"[^{}]*"tips"[^{}]*\}'
                    json_match = re.search(json_pattern, answer_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        result_json = json.loads(json_str)
                        print("✅ 方式3成功：正则表达式匹配特定字段")
                    else:
                        print("⚠️ 方式3失败：未找到匹配的JSON模式")
                except json.JSONDecodeError:
                    print("⚠️ 方式3失败：正则匹配的内容无法解析")
            
            # 方式4：更宽泛的JSON匹配（查找任何JSON对象）
            if not result_json:
                try:
                    json_match = re.search(r'\{[\s\S]*?\}', answer_content)
                    if json_match:
                        json_str = json_match.group(0)
                        result_json = json.loads(json_str)
                        print("✅ 方式4成功：宽泛JSON匹配")
                    else:
                        print("⚠️ 方式4失败：未找到JSON对象")
                except json.JSONDecodeError:
                    print("⚠️ 方式4失败：宽泛匹配的内容无法解析")
            
            if result_json:
                print("✅ JSON格式解析成功")
                print(f"解析结果包含字段: {list(result_json.keys())}")
            else:
                raise json.JSONDecodeError("所有解析方式都失败", "", 0)
            
            # 保存结果到文件
            with open('result.json', 'w', encoding='utf-8') as f:
                json.dump(result_json, f, ensure_ascii=False, indent=2)
            print("💾 结果已保存到 result.json")
            
            # 保存完整分析内容
            analysis_data = {
                "reasoning_process": reasoning_content,
                "final_result": answer_content,
                "full_analysis": reasoning_content + answer_content
            }
            
            with open('analysis.json', 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            print("💾 完整分析已保存到 analysis.json")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"原始内容: {answer_content}")
            
            # 即使JSON解析失败，也保存原始结果
            fallback_result = {
                "thinking_process": "解析失败，请查看原始内容",
                "key_points": ["数据解析错误"],
                "knowledge_areas": ["未知"],
                "tips": ["请重新分析"]
            }
            
            with open('result.json', 'w', encoding='utf-8') as f:
                json.dump(fallback_result, f, ensure_ascii=False, indent=2)
            
            analysis_data = {
                "reasoning_process": reasoning_content,
                "final_result": answer_content,
                "full_analysis": reasoning_content + answer_content,
                "error": str(e)
            }
            
            with open('analysis.json', 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        
        # 创建错误结果文件
        error_result = {
            "thinking_process": f"分析失败: {str(e)}",
            "key_points": ["请求错误"],
            "knowledge_areas": ["未知"],
            "tips": ["请检查网络连接和API配置"]
        }
        
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(error_result, f, ensure_ascii=False, indent=2)
        
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 思路解答分析完成")
    else:
        print("\n💥 思路解答分析失败")