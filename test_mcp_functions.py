#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试MCP功能脚本
验证亮度控制和功能切换是否正常工作
"""

import sys
import os

# 添加switchrole目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'switchrole'))

def test_brightness_control():
    """测试亮度控制功能"""
    print("🧪 测试亮度控制功能...")
    
    try:
        from xiaoxin2_skill import control_brightness
        
        # 测试调用
        result = control_brightness("20")
        print(f"   ✅ control_brightness('20') 返回: {result}")
        
        # 检查是否有调试输出
        if "💡 收到亮度控制指令: 20" in str(result) or "好的，正在调节亮度到20" in str(result):
            print("   ✅ 亮度控制函数调用成功")
            return True
        else:
            print("   ❌ 亮度控制可能有问题")
            return False
            
    except Exception as e:
        print(f"   ❌ 亮度控制测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_homework_correction():
    """测试作业批改功能"""
    print("🧪 测试作业批改功能...")
    
    try:
        from xiaoxin2_skill import open_homework_correction
        
        # 测试调用
        result = open_homework_correction()
        print(f"   ✅ open_homework_correction() 返回: {result}")
        
        if "作业批改功能已启动" in str(result) or "MCP调用：启动作业批改功能" in str(result):
            print("   ✅ 作业批改功能调用成功")
            return True
        else:
            print("   ❌ 作业批改功能可能有问题")
            return False
            
    except Exception as e:
        print(f"   ❌ 作业批改功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tools_list():
    """测试工具列表是否包含新功能"""
    print("🧪 测试工具列表...")
    
    try:
        from xiaoxin2_skill import getTools
        
        tools = getTools()
        print(f"   📋 工具列表长度: {len(tools)}")
        
        # 检查是否包含新功能
        tool_names = []
        for tool in tools:
            if 'function' in tool and 'name' in tool['function']:
                tool_names.append(tool['function']['name'])
        
        print(f"   📋 工具名称: {tool_names}")
        
        expected_tools = ['control_brightness', 'open_homework_correction', 'open_homework_qa', 'open_system_settings']
        missing_tools = []
        
        for expected in expected_tools:
            if expected not in tool_names:
                missing_tools.append(expected)
        
        if missing_tools:
            print(f"   ❌ 缺失工具: {missing_tools}")
            return False
        else:
            print("   ✅ 所有必要工具都在列表中")
            return True
            
    except Exception as e:
        print(f"   ❌ 工具列表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mqtt_send():
    """测试MQTT发送功能"""
    print("🧪 测试MQTT发送...")
    
    try:
        from function_handlers import _send_settings_control_command
        
        # 测试发送亮度控制指令
        success = _send_settings_control_command("brightness", 20)
        print(f"   📤 MQTT发送结果: {success}")
        
        if success:
            print("   ✅ MQTT发送成功")
            return True
        else:
            print("   ❌ MQTT发送失败")
            return False
            
    except Exception as e:
        print(f"   ❌ MQTT发送测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始MCP功能测试...")
    print("=" * 50)
    
    tests = [
        ("工具列表", test_tools_list),
        ("亮度控制", test_brightness_control),
        ("作业批改", test_homework_correction),
        ("MQTT发送", test_mqtt_send)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 测试 {test_name}:")
        try:
            if test_func():
                print(f"   ✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"   ❌ {test_name} 测试失败")
        except Exception as e:
            print(f"   ❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！MCP功能正常工作")
    else:
        print("⚠️ 部分测试失败，请检查相关功能")
        
    print("\n💡 测试完成。如果亮度控制仍然不工作，请检查:")
    print("   1. 语音助手是否正确调用了control_brightness函数")
    print("   2. MQTT连接是否正常")
    print("   3. ESP32设备是否在线并监听esp32/s2/control主题") 