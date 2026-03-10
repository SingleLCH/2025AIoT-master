#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语音功能切换演示
"""

def demo_voice_functions():
    """演示语音功能切换"""
    print("🎯 语音功能切换演示")
    print("=" * 50)
    
    try:
        from function_handlers import handle_voice_function_command
        
        # 演示命令列表
        demo_commands = [
            "打开拍照搜题",
            "打开作业批改", 
            "打开音乐播放",
            "打开AI对话",
            "打开系统设置",
            "打开语音助手",
            "打开视频连接",
            "打开通知功能"
        ]
        
        print("📋 支持的语音命令:")
        for i, cmd in enumerate(demo_commands, 1):
            print(f"  {i}. {cmd}")
        
        print("\n🧪 开始演示...")
        
        success_count = 0
        for cmd in demo_commands:
            print(f"\n🎤 执行命令: '{cmd}'")
            try:
                success, response = handle_voice_function_command(cmd)
                if success:
                    print(f"✅ {response}")
                    success_count += 1
                else:
                    print(f"❌ {response}")
            except Exception as e:
                print(f"❌ 执行异常: {e}")
        
        print(f"\n📊 演示结果: {success_count}/{len(demo_commands)} 成功")
        
        if success_count >= len(demo_commands) * 0.8:
            print("🎉 语音功能切换演示成功！")
            print("\n💡 使用说明:")
            print("   - 在语音助手中说出上述命令")
            print("   - 系统会自动切换到对应的功能界面")
            print("   - 根据当前模式（学校/家庭）显示相应功能")
            return True
        else:
            print("⚠️ 部分功能演示失败")
            return False
            
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        return False

def show_mode_functions():
    """显示不同模式下的可用功能"""
    print("\n🏫 学校模式可用功能:")
    school_functions = [
        "📸 拍照搜题 - 拍照识别题目并获取答案",
        "📝 作业批改 - 批改作业并提供反馈", 
        "🤖 AI对话 - 智能对话和学习辅导",
        "⚙️ 系统设置 - 调整系统参数"
    ]
    
    for func in school_functions:
        print(f"   {func}")
    
    print("\n🏠 家庭模式可用功能:")
    home_functions = [
        "📸 拍照搜题 - 拍照识别题目并获取答案",
        "📝 作业批改 - 批改作业并提供反馈",
        "🎵 音乐播放 - 播放音乐和娱乐内容",
        "🤖 AI对话 - 智能对话和学习辅导",
        "📹 视频连接 - 视频通话和远程学习",
        "🔔 通知功能 - 消息通知和提醒",
        "⚙️ 系统设置 - 调整系统参数"
    ]
    
    for func in home_functions:
        print(f"   {func}")

def show_voice_commands():
    """显示所有支持的语音命令"""
    print("\n🎤 支持的语音命令格式:")
    
    command_patterns = {
        "拍照搜题": ["打开拍照搜题", "启动搜题功能", "切换到题目解答"],
        "作业批改": ["打开作业批改", "启动批改作业", "进入作业检查"],
        "音乐播放": ["打开音乐播放", "启动音乐功能", "播放音乐"],
        "AI对话": ["打开AI对话", "启动智能对话", "进入对话功能"],
        "系统设置": ["打开系统设置", "启动设置功能", "进入设置"],
        "语音助手": ["打开语音助手", "启动语音功能"],
        "视频连接": ["打开视频连接", "启动视频通话", "进入视频功能"],
        "通知功能": ["打开通知功能", "启动通知中心", "查看消息通知"]
    }
    
    for function, commands in command_patterns.items():
        print(f"\n📋 {function}:")
        for cmd in commands:
            print(f"   • {cmd}")

def main():
    """主函数"""
    print("🚀 语音功能切换系统演示")
    print("=" * 60)
    
    # 显示模式功能
    show_mode_functions()
    
    # 显示语音命令
    show_voice_commands()
    
    # 演示功能切换
    demo_voice_functions()
    
    print("\n" + "=" * 60)
    print("✨ 演示完成！现在你可以在语音助手中使用这些命令了。")

if __name__ == "__main__":
    main()
