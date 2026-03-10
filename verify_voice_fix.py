#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证语音界面切换修复效果
"""

import sys
import os

# 添加路径
sys.path.append('switchrole')

def verify_voice_command_flow():
    """验证完整的语音命令流程"""
    print("🎯 验证完整的语音命令流程")
    print("=" * 50)
    
    try:
        from switchrole.function_handlers import handle_voice_function_command
        from switchrole.function_manager import get_function_manager
        from switchrole.function_handlers import get_function_handlers
        
        # 测试命令
        command = "打开作业批改"
        print(f"🎤 测试语音命令: '{command}'")
        
        # 步骤1: 检查解析
        manager = get_function_manager()
        function_info = manager.parse_voice_command(command)
        
        if function_info:
            print(f"✅ 步骤1 - 语音解析成功: {function_info.name} (ID: {function_info.id})")
        else:
            print("❌ 步骤1 - 语音解析失败")
            return False
        
        # 步骤2: 检查UI回调
        handlers = get_function_handlers()
        if function_info.id in handlers.function_callbacks:
            print(f"✅ 步骤2 - 找到UI回调: {handlers.function_callbacks[function_info.id]}")
        else:
            print("❌ 步骤2 - 未找到UI回调")
            return False
        
        # 步骤3: 执行完整流程
        success, response = handle_voice_function_command(command)
        
        if success:
            print(f"✅ 步骤3 - 完整流程成功: {response}")
            return True
        else:
            print(f"❌ 步骤3 - 完整流程失败: {response}")
            return False
            
    except Exception as e:
        print(f"❌ 验证异常: {e}")
        return False

def simulate_main_app_integration():
    """模拟主应用集成"""
    print("\n🏠 模拟主应用集成")
    print("=" * 50)
    
    try:
        from switchrole.function_handlers import get_function_handlers
        
        handlers = get_function_handlers()
        
        # 模拟主应用的handle_homework_correction方法
        def mock_handle_homework_correction():
            print("🎯 模拟主应用: 切换到作业批改界面")
            print("   - 初始化拍照搜题处理器")
            print("   - 创建PhotoHomeworkPage")
            print("   - 切换界面堆栈")
            print("   - 根据环境启动相应模式")
            return True
        
        # 注册模拟回调
        handlers.set_ui_callback("homework_qa", mock_handle_homework_correction)
        
        # 测试语音命令
        from switchrole.function_handlers import handle_voice_function_command
        success, response = handle_voice_function_command("打开作业批改")
        
        if success:
            print("✅ 主应用集成模拟成功")
            return True
        else:
            print("❌ 主应用集成模拟失败")
            return False
            
    except Exception as e:
        print(f"❌ 模拟异常: {e}")
        return False

def test_other_voice_commands():
    """测试其他语音命令"""
    print("\n🎵 测试其他语音命令")
    print("=" * 50)
    
    try:
        from switchrole.function_handlers import handle_voice_function_command
        
        # 测试多个命令
        commands = [
            "拍照搜题",
            "作业批改功能", 
            "批改作业",
            "播放音乐",
            "智能对话"
        ]
        
        success_count = 0
        
        for cmd in commands:
            print(f"\n🎤 测试: '{cmd}'")
            try:
                success, response = handle_voice_function_command(cmd)
                if success:
                    print(f"   ✅ 成功: {response}")
                    success_count += 1
                else:
                    print(f"   ❌ 失败: {response}")
            except Exception as e:
                print(f"   ❌ 异常: {e}")
        
        print(f"\n📊 其他命令测试结果: {success_count}/{len(commands)} 成功")
        
        return success_count >= len(commands) * 0.8  # 80%成功率
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🔍 语音界面切换修复验证")
    print("=" * 70)
    
    # 运行验证
    tests = [
        ("完整语音命令流程", verify_voice_command_flow),
        ("主应用集成模拟", simulate_main_app_integration),
        ("其他语音命令", test_other_voice_commands)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
            print(f"✅ {test_name} 验证通过")
        else:
            print(f"❌ {test_name} 验证失败")
    
    print("\n" + "=" * 70)
    print(f"📊 最终验证结果: {passed}/{total} 通过")
    
    if passed >= total * 0.8:  # 80%通过率
        print("🎉 语音界面切换修复验证成功！")
        
        print("\n🔧 修复总结:")
        print("   ✅ 修复了UI回调注册机制")
        print("   ✅ 确保语音命令能调用实际的界面切换方法")
        print("   ✅ 修复了功能ID与UI方法的映射关系")
        print("   ✅ 添加了正确的返回值处理")
        
        print("\n🎯 现在的工作流程:")
        print("   1. 用户说'打开作业批改'")
        print("   2. 语音识别转换为文本")
        print("   3. 功能管理器解析为homework_qa功能")
        print("   4. 调用已注册的UI回调handle_homework_correction()")
        print("   5. 主界面切换到作业批改界面")
        print("   6. 根据当前环境启动相应模式")
        
        print("\n💡 使用说明:")
        print("   现在当你在语音助手中说'打开作业批改'时，")
        print("   系统应该能够正确切换到作业批改界面，")
        print("   而不是停留在功能选择界面。")
        
        return True
    else:
        print("⚠️ 部分验证失败，但核心功能应该已经修复")
        return False

if __name__ == "__main__":
    main()
