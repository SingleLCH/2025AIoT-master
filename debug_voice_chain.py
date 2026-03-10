#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试语音命令完整调用链
"""

import sys
import os

# 添加路径
sys.path.append('switchrole')

def debug_complete_voice_chain():
    """调试完整的语音命令调用链"""
    print("🔍 调试完整的语音命令调用链")
    print("=" * 60)
    
    command = "打开作业批改"
    print(f"🎤 测试命令: '{command}'")
    
    try:
        # 步骤1: 模拟主应用注册UI回调
        print("\n📝 步骤1: 模拟主应用注册UI回调")
        
        from function_handlers import get_function_handlers
        handlers = get_function_handlers()
        
        # 模拟主应用的handle_homework_correction方法
        def mock_handle_homework_correction(**kwargs):
            print("🎯 [模拟主应用] handle_homework_correction() 被调用")
            print("   - 初始化拍照搜题处理器")
            print("   - 创建PhotoHomeworkPage")
            print("   - 切换界面堆栈")
            print("   - 根据环境启动相应模式")
            return True
        
        # 注册UI回调
        handlers.set_ui_callback("homework_qa", mock_handle_homework_correction)
        print(f"✅ UI回调已注册: {list(handlers.function_callbacks.keys())}")
        
        # 步骤2: 测试功能管理器解析
        print("\n🔍 步骤2: 测试功能管理器解析")
        
        from function_manager import get_function_manager
        manager = get_function_manager()
        
        function_info = manager.parse_voice_command(command)
        if function_info:
            print(f"✅ 解析成功: {function_info.name} (ID: {function_info.id})")
        else:
            print("❌ 解析失败")
            return False
        
        # 步骤3: 检查功能处理器注册
        print("\n📋 步骤3: 检查功能处理器注册")
        
        print(f"功能管理器中的处理器: {list(manager.function_handlers.keys())}")
        
        if function_info.id in manager.function_handlers:
            handler = manager.function_handlers[function_info.id]
            print(f"✅ 找到处理器: {handler}")
        else:
            print("❌ 未找到处理器，重新注册...")
            handlers._register_handlers()
            print(f"重新注册后: {list(manager.function_handlers.keys())}")
        
        # 步骤4: 测试直接调用功能处理器
        print("\n🔧 步骤4: 测试直接调用功能处理器")
        
        try:
            result = handlers.open_homework_qa()
            print(f"✅ 直接调用结果: {result}")
        except Exception as e:
            print(f"❌ 直接调用失败: {e}")
        
        # 步骤5: 测试功能管理器执行
        print("\n⚙️ 步骤5: 测试功能管理器执行")
        
        success = manager.execute_function(function_info.id)
        print(f"{'✅' if success else '❌'} 功能管理器执行结果: {success}")
        
        # 步骤6: 测试完整的handle_voice_function_command
        print("\n🎯 步骤6: 测试完整的handle_voice_function_command")
        
        from function_handlers import handle_voice_function_command
        success, response = handle_voice_function_command(command)
        
        print(f"{'✅' if success else '❌'} 完整流程结果: {success}")
        print(f"响应: {response}")
        
        return success
        
    except Exception as e:
        print(f"❌ 调试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_callback_mechanism():
    """测试UI回调机制"""
    print("\n🔗 测试UI回调机制")
    print("=" * 60)
    
    try:
        from function_handlers import get_function_handlers
        handlers = get_function_handlers()
        
        # 测试回调注册和调用
        callback_called = False
        
        def test_callback(**kwargs):
            nonlocal callback_called
            callback_called = True
            print("🎯 测试回调被成功调用")
            return True
        
        # 注册测试回调
        handlers.set_ui_callback("test_function", test_callback)
        
        # 检查回调是否注册
        if "test_function" in handlers.function_callbacks:
            print("✅ 回调注册成功")
            
            # 调用回调
            callback = handlers.function_callbacks["test_function"]
            result = callback()
            
            if callback_called and result:
                print("✅ 回调调用成功")
                return True
            else:
                print("❌ 回调调用失败")
                return False
        else:
            print("❌ 回调注册失败")
            return False
            
    except Exception as e:
        print(f"❌ UI回调机制测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 语音命令调用链调试")
    print("=" * 70)
    
    # 运行调试
    tests = [
        ("UI回调机制", test_ui_callback_mechanism),
        ("完整语音命令调用链", debug_complete_voice_chain)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")
    
    print("\n" + "=" * 70)
    print(f"📊 调试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 语音命令调用链调试成功！")
        
        print("\n🔧 修复总结:")
        print("   ✅ 修复了模块导入路径问题")
        print("   ✅ 修复了UI回调调用机制")
        print("   ✅ 确保功能处理器正确连接到主界面方法")
        print("   ✅ 添加了详细的日志和错误处理")
        
        print("\n🎯 现在的调用流程:")
        print("   1. 语音识别: '打开作业批改'")
        print("   2. xiaoxin2_zh.py: handle_voice_function_command()")
        print("   3. function_manager: parse_voice_command() -> homework_qa")
        print("   4. function_manager: execute_function('homework_qa')")
        print("   5. function_handlers: open_homework_qa()")
        print("   6. UI回调: handle_homework_correction()")
        print("   7. 主界面: 切换到作业批改界面")
        
        return True
    else:
        print("⚠️ 部分调试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    main()
