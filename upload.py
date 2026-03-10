from openai import OpenAI
import os
import glob
import json
import re
import sys
import base64
#将图片上传到服务器，返回json信息，json信息包含错误题号和薄弱知识点

def main():
    # 设置图片文件夹路径
    image_folder = "paper_photos"
    
    # 检查文件夹是否存在
    if not os.path.exists(image_folder):
        print(f"❌ 错误：图片文件夹 {image_folder} 不存在！")
        print("请确保路径正确或创建该文件夹")
        return False
    
    # 获取所有 .png 图片路径
    image_paths = glob.glob(os.path.join(image_folder, "*.png"))
    
    if not image_paths:
        print(f"❌ 在 {image_folder} 中未找到任何 PNG 图片文件")
        print("请确保文件夹中有 .png 格式的图片")
        return False
    
    print(f"✅ 找到 {len(image_paths)} 张 PNG 图片文件:")
    for i, path in enumerate(image_paths, 1):
        print(f"  {i}. {os.path.basename(path)}")
    
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
    
    # 添加统一的提示词
    image_messages.append({
        "type": "text",
        "text": (
            "这是一份作业，批改一下，返回错误题号以及薄弱信息，严格按照以下的json格式返回：\n"
            '{\n'
            '  "error_numbers": [],\n'
            '  "weak_areas": ["立体"]\n'
            '}\n'
            "注意：\n"
            "1. error_numbers 数组中包含错误题目的题号（如果所有题目都正确，则为空数组[]）\n"
            "2. weak_areas 数组中包含学生薄弱的知识点\n"
            "3. 严格按照以上JSON格式返回，不要添加任何markdown标记或其他解释文字\n"
            "4. 直接输出JSON内容，不要用代码块包围"
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
            if not chunk.choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    print("\n📊 API使用统计:")
                    print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    content_piece = delta.content or ""
                    if content_piece and not is_answering:
                        print("\n" + "=" * 20 + "模型回复" + "=" * 20 + "\n")
                        is_answering = True
                    print(content_piece, end='', flush=True)
                    answer_content += content_piece
        
        # 尝试从回答中提取 JSON 结构
        print("\n\n" + "=" * 20 + "JSON解析结果" + "=" * 20 + "\n")
        
        if not answer_content.strip():
            print("❌ 模型没有返回任何内容")
            return False
        
        # 多种方式尝试提取JSON
        json_result = None
        json_str = None
        
        # 方式1：直接尝试解析整个回复
        try:
            json_result = json.loads(answer_content.strip())
            json_str = answer_content.strip()
        except:
            pass
        
        # 方式2：查找第一个完整的JSON对象
        if not json_result:
            json_match = re.search(r'\{[^{}]*"error_numbers"[^{}]*"weak_areas"[^{}]*\}', answer_content)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    json_result = json.loads(json_str)
                except:
                    pass
        
        # 方式3：更宽泛的JSON匹配
        if not json_result:
            json_match = re.search(r'\{[\s\S]*?\}', answer_content)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    json_result = json.loads(json_str)
                except:
                    pass
        
        if json_result:
            # 验证 JSON 格式是否符合要求
            if "error_numbers" in json_result and "weak_areas" in json_result:
                print("✅ JSON 格式验证通过")
                print("📋 批改结果：")
                print(json.dumps(json_result, indent=2, ensure_ascii=False))
                
                # 保存结果到文件
                try:
                    # 保存JSON结果
                    with open("result.json", "w", encoding="utf-8") as f:
                        json.dump(json_result, f, indent=2, ensure_ascii=False)
                    print("\n💾 已保存结果到 result.json")
                    
                    # 保存完整的分析内容（包括思考过程）
                    analysis_data = {
                        "reasoning_content": reasoning_content,
                        "answer_content": answer_content,
                        "json_result": json_result,
                        "full_analysis": f"====================思考过程====================\n{reasoning_content}\n====================模型回复====================\n{answer_content}"
                    }
                    
                    with open("analysis.json", "w", encoding="utf-8") as f:
                        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
                    print("💾 已保存完整分析到 analysis.json")
                    
                    # 输出总结信息
                    error_count = len(json_result.get("error_numbers", []))
                    weak_areas = json_result.get("weak_areas", [])
                    
                    print(f"\n📊 批改总结：")
                    print(f"   错误题目数量: {error_count}")
                    if error_count > 0:
                        print(f"   错误题号: {json_result['error_numbers']}")
                    print(f"   薄弱知识点: {weak_areas}")
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ 保存文件失败: {e}")
                    return False
            else:
                print("❌ JSON 格式不符合要求，缺少 error_numbers 或 weak_areas 字段")
                print(f"实际返回的JSON: {json_result}")
        else:
            print("❌ 未能解析出有效的JSON内容")
            print("🔍 原始回复内容：")
            print("-" * 50)
            print(answer_content)
            print("-" * 50)
            print("\n💡 建议：")
            print("1. 检查API Key是否有效")
            print("2. 确认模型是否支持图片处理")
            print("3. 检查网络连接")
            
        return False
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        print("💡 常见问题排查：")
        print("1. 检查API Key是否正确")
        print("2. 检查网络连接")
        print("3. 确认模型名称是否正确")
        print("4. 检查图片文件是否损坏")
        return False

if __name__ == "__main__":
    print("🚀 开始批改作业...")
    success = main()
    if success:
        print("\n🎉 作业批改完成！")
    else:
        print("\n❌ 作业批改失败，请检查上述提示信息")
        sys.exit(1)
