from openai import OpenAI
import os
import json
import base64
from datetime import datetime
import glob
import sys

def batch_analyze_homework(image_paths):
    """
    批量分析作业图片
    
    Args:
        image_paths: 图片文件路径列表
    
    Returns:
        bool: 分析是否成功
    """
    
    if not image_paths:
        print("❌ 错误：未提供图片文件路径！")
        return False
    
    # 验证图片文件是否存在
    valid_images = []
    for img_path in image_paths:
        if os.path.exists(img_path):
            valid_images.append(img_path)
            print(f"✅ 找到图片: {os.path.basename(img_path)}")
        else:
            print(f"⚠️ 警告：图片文件不存在，跳过: {img_path}")
    
    if not valid_images:
        print("❌ 错误：没有有效的图片文件！")
        return False
    
    print(f"\n📊 准备分析 {len(valid_images)} 个图片文件")
    
    try:
        # 处理多个图片
        image_contents = []
        for image_path in valid_images:
            # 读取图片并转换为base64格式
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # 根据文件扩展名确定MIME类型
                ext = os.path.splitext(image_path)[1].lower()
                mime_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.bmp': 'image/bmp',
                    '.gif': 'image/gif'
                }
                mime_type = mime_type_map.get(ext, 'image/png')
                
                data_url = f"data:{mime_type};base64,{base64_image}"
                
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": data_url
                    }
                })
                
        print(f"✅ {len(image_contents)} 个图片已转换为base64格式")
        
        # 构建分析提示词
        analysis_prompt = """
你是一位教育数据分析专家。请分析这些学生作业图片，并提供教学分析报告。

请按照以下JSON格式返回分析结果：
{

   "error_analysis": { 
     "common_mistakes": [ 
       { 
         "question_id": "Q1", 
         "error_rate": 0.75, 
         "reason": "学生普遍不会运用公式解题" 
       }
     ], 
     "class_weak_points": [ 
       { 
         "knowledge_point": "分数乘法", 
         "wrong_rate": 0.60, 
         "related_questions": ["Q3", "Q5", "Q12"] 
       }
     ] 
   }, 
   "ai_teaching_advice": { 
     "summary": "本次作业显示学生在某些知识点掌握不牢固，需重点强化。", 
     "recommendations": [ 
       "布置针对性练习", 
       "课堂重点讲解", 
       "组织错题分享活动" ,
       "针对某些学生，则加强其针对性练习"
     ] 
   } 
}

请严格按照上述JSON格式返回，不要包含其他文字。
"""
        
        # 构建消息内容
        content_list = image_contents.copy()
        content_list.append({
            "type": "text",
            "text": analysis_prompt
        })
        
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的教育数据分析专家，擅长分析学生作业并提供教学建议。请严格按照JSON格式返回分析结果。"
            },
            {
                "role": "user",
                "content": content_list
            }
        ]
        
        # API配置 - 从环境变量获取
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ 错误：请设置环境变量 DASHSCOPE_API_KEY")
            return False
        
        # 初始化客户端
        print("\n🔄 正在连接阿里云通义千问API...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            timeout=30  # 设置客户端超时
        )
        
        # 发起API请求
        request_start_time = datetime.now()
        print(f"📤 正在发送分析请求... [{request_start_time.strftime('%H:%M:%S')}]")
        print("🔗 测试网络连接...")
        
        try:
            # 测试API端点连接
            import requests
            test_response = requests.get("https://dashscope.aliyuncs.com/compatible-mode/v1/models", 
                                       headers={"Authorization": f"Bearer {api_key}"}, 
                                       timeout=10)
            if test_response.status_code in [200, 401, 403]:  # 200成功，401/403说明连接正常但认证问题
                print(f"✅ 网络连接正常，API端点可达")
            else:
                print(f"⚠️ API端点响应异常 (状态码: {test_response.status_code})")
        except Exception as conn_error:
            print(f"⚠️ 网络连接测试失败: {conn_error}")
            print("继续尝试API调用...")
        
        try:
            # 使用更快的模型提升响应速度
            model_name = os.environ.get("BATCH_HOMEWORK_MODEL", "qvq-plus")  # 默认使用更快的qvq-plus
            print(f"🤖 使用模型: {model_name}")
            
            api_call_start = datetime.now()
            completion = client.chat.completions.create(
                model=model_name,  # 可配置的模型选择
                messages=messages,
                stream=True,  # QVQ模型必须使用流式输出
                temperature=0.6,  # 降低随机性，可能稍微提升速度
                max_tokens=8000,  # 限制最大token数量，避免过长响应
                timeout=60  # 设置60秒超时
            )
            api_call_elapsed = (datetime.now() - api_call_start).total_seconds()
            print(f"✅ API请求成功 (连接用时: {api_call_elapsed:.1f}s)")
        except Exception as api_error:
            print(f"❌ API请求失败: {api_error}")
            return False
        
        # 处理流式响应  
        model_name = os.environ.get("BATCH_HOMEWORK_MODEL", "qvq-plus")  # 获取模型名称用于显示
        print("🔍 正在处理响应数据...")
        print(f"⏳ 等待服务器AI处理中... ({model_name}模型处理中，请耐心等待)")
        full_response = ""
        chunk_count = 0
        start_time = datetime.now()
        first_chunk_received = False
        
        try:
            for chunk in completion:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        # 接收到第一个数据块时立即反馈
                        if not first_chunk_received:
                            print("🎯 已建立连接，开始接收AI响应数据...")
                            first_chunk_received = True
                        
                        full_response += delta.content
                        chunk_count += 1
                        
                        # 每15个chunk输出一次进度，让用户知道在处理
                        if chunk_count % 15 == 0:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            print(f"📥 已接收 {chunk_count} 个数据块，已用时 {elapsed:.1f}s，正在持续处理中...")
                            
                        # 每200个字符输出一次点，显示实时进度
                        if len(full_response) % 200 == 0 and len(full_response) > 0:
                            print(".", end="", flush=True)
            
            elapsed_total = (datetime.now() - start_time).total_seconds()
            print(f"\n✅ 响应数据处理完成 (共接收 {chunk_count} 个数据块, {len(full_response)} 个字符, 用时 {elapsed_total:.1f}s)")
            
            if not full_response.strip():
                print("❌ 未获取到有效的响应内容")
                return False
                
        except Exception as stream_error:
            elapsed_error = (datetime.now() - start_time).total_seconds()
            print(f"❌ 处理响应时出错 (已处理 {elapsed_error:.1f}s): {stream_error}")
            print(f"📊 已接收数据: {chunk_count} 个数据块, {len(full_response)} 个字符")
            
            # 提供更详细的错误诊断
            if "timeout" in str(stream_error).lower():
                print("💡 提示：可能是网络超时，建议检查网络连接")
            elif "connection" in str(stream_error).lower():
                print("💡 提示：可能是网络连接问题，建议重试")
            elif len(full_response) == 0:
                print("💡 提示：未接收到任何数据，可能是API配置问题")
            else:
                print("💡 提示：已接收部分数据，可能是服务端问题")
                
            return False
        
        # 解析JSON结果
        print("🔍 正在解析分析结果...")
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', full_response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                print("✅ JSON解析成功")
                
                # 保存结果到文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"homework_analysis_result_{timestamp}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"\n✅ 分析结果已保存到: {output_file}")
                
                # 显示分析摘要
                print("\n" + "=" * 50)
                print("📊 教学分析报告摘要")
                print("=" * 50)
                
                print(f"作业ID: {result.get('homework_id', '未识别')}")
                print(f"班级ID: {result.get('class_id', '未识别')}")
                
                error_analysis = result.get('error_analysis', {})
                common_mistakes = error_analysis.get('common_mistakes', [])
                weak_points = error_analysis.get('class_weak_points', [])
                
                print(f"\n🔍 错误分析:")
                print(f"  - 常见错误: {len(common_mistakes)} 个")
                for mistake in common_mistakes[:3]:  # 显示前3个
                    print(f"    • {mistake.get('question_id', 'N/A')}: {mistake.get('reason', 'N/A')} (错误率: {mistake.get('error_rate', 0):.1%})")
                
                print(f"  - 薄弱知识点: {len(weak_points)} 个")
                for point in weak_points[:3]:  # 显示前3个
                    print(f"    • {point.get('knowledge_point', 'N/A')} (错误率: {point.get('wrong_rate', 0):.1%})")
                
                teaching_advice = result.get('ai_teaching_advice', {})
                summary = teaching_advice.get('summary', '')
                recommendations = teaching_advice.get('recommendations', [])
                
                print(f"\n💡 教学建议:")
                print(f"  总结: {summary}")
                print(f"  建议数量: {len(recommendations)} 条")
                for i, rec in enumerate(recommendations[:3], 1):  # 显示前3条
                    print(f"    {i}. {rec}")
                
                print("\n" + "=" * 50)
                
                return True
            else:
                print("❌ 无法从响应中提取有效的JSON格式")
                print("响应内容前500字符:")
                print(full_response[:500])
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print("原始响应内容:")
            print(full_response)
            return False
        except Exception as parse_error:
            print(f"❌ 解析过程中出现错误: {parse_error}")
            return False
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    主函数 - 支持命令行参数或交互式输入
    """
    print("🎓 作业批量分析工具")
    print("=" * 30)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 使用命令行参数
        image_paths = sys.argv[1:]
        print(f"使用命令行参数，分析 {len(image_paths)} 个图片文件")
    else:
        # 交互式输入
        print("\n请选择输入方式:")
        print("1. 输入图片文件路径（多个用逗号分隔）")
        print("2. 输入包含图片的文件夹路径")
        print("3. 使用当前目录的所有图片")
        
        choice = input("\n请选择 (1/2/3): ").strip()
        
        if choice == '1':
            # 手动输入图片路径
            paths_input = input("请输入图片文件路径（多个用逗号分隔）: ").strip()
            if not paths_input:
                print("❌ 未输入任何路径")
                return False
            image_paths = [path.strip() for path in paths_input.split(',')]
            
        elif choice == '2':
            # 输入文件夹路径
            folder_path = input("请输入文件夹路径: ").strip()
            if not folder_path or not os.path.isdir(folder_path):
                print("❌ 文件夹路径无效")
                return False
            
            # 获取文件夹中的所有图片
            image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
            image_paths = []
            for ext in image_extensions:
                image_paths.extend(glob.glob(os.path.join(folder_path, ext)))
                image_paths.extend(glob.glob(os.path.join(folder_path, ext.upper())))
            
            if not image_paths:
                print(f"❌ 在文件夹 {folder_path} 中未找到图片文件")
                return False
                
        elif choice == '3':
            # 使用当前目录
            image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']
            image_paths = []
            for ext in image_extensions:
                image_paths.extend(glob.glob(ext))
                image_paths.extend(glob.glob(ext.upper()))
            
            if not image_paths:
                print("❌ 当前目录中未找到图片文件")
                return False
        else:
            print("❌ 无效的选择")
            return False
    
    # 执行分析
    print(f"\n🚀 开始分析 {len(image_paths)} 个图片文件...")
    success = batch_analyze_homework(image_paths)
    
    if success:
        print("\n🎉 作业分析完成！")
    else:
        print("\n❌ 作业分析失败")
    
    return success

if __name__ == "__main__":
    main()