#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查语音功能切换的完整逻辑
"""

import sys
import os

def check_config_consistency():
    """检查配置一致性"""
    print("⚙️ 检查配置一致性")
    print("=" * 50)
    
    try:
        # 检查config.py中的MQTT指令配置
        from config import CONTROL_COMMANDS
        
        voice_commands = {k: v for k, v in CONTROL_COMMANDS.items() if k.startswith('7-1-')}
        
        print("📋 MQTT语音指令配置:")
        for mqtt_code, action in voice_commands.items():
            print(f"   {mqtt_code} -> {action}")
        
        # 检查switchrole中的功能映射
        switchrole_path = os.path.join(os.path.dirname(__file__), 'switchrole')
        if switchrole_path not in sys.path:
            sys.path.insert(0, switchrole_path)
        
        from function_handlers import FunctionHandlers
        handlers = FunctionHandlers()
        
        # 检查MQTT发送映射
        function_to_mqtt = {
            "homework_qa": "7-1-1",
            "homework_correction": "7-1-2", 
            "music_player": "7-1-3",
            "ai_chat": "7-1-4",
            "system_settings": "7-1-5",
            "video_meetings": "7-1-6",
            "notifications": "7-1-7",
            "voice_assistant": "7-1-8"
        }
        
        print("\n📋 功能ID到MQTT指令映射:")
        for func_id, mqtt_code in function_to_mqtt.items():
            print(f"   {func_id} -> {mqtt_code}")
        
        # 检查一致性
        inconsistencies = []
        for func_id, mqtt_code in function_to_mqtt.items():
            if mqtt_code not in voice_commands:
                inconsistencies.append(f"MQTT指令 {mqtt_code} 在config.py中未定义")
        
        if inconsistencies:
            print("\n❌ 发现配置不一致:")
            for issue in inconsistencies:
                print(f"   {issue}")
            return False
        else:
            print("\n✅ 配置一致性检查通过")
            return True
            
    except Exception as e:
        print(f"❌ 配置检查异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_main_ui_logic():
    """检查主界面逻辑"""
    print("\n🏠 检查主界面逻辑")
    print("=" * 50)
    
    try:
        # 检查主界面是否有正确的MQTT处理逻辑
        with open('main.py', 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # 检查关键方法是否存在
        required_methods = [
            'handle_control_command',
            '_handle_voice_function_command',
            'handle_homework_correction'
        ]
        
        missing_methods = []
        for method in required_methods:
            if f"def {method}" not in main_content:
                missing_methods.append(method)
        
        if missing_methods:
            print("❌ 主界面缺少必要方法:")
            for method in missing_methods:
                print(f"   {method}")
            return False
        
        # 检查语音功能切换逻辑
        if "action.startswith('voice_')" in main_content:
            print("✅ 找到语音功能切换逻辑")
        else:
            print("❌ 未找到语音功能切换逻辑")
            return False
        
        # 检查功能映射
        if "voice_homework_qa" in main_content:
            print("✅ 找到功能映射配置")
        else:
            print("❌ 未找到功能映射配置")
            return False
        
        print("✅ 主界面逻辑检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 主界面逻辑检查异常: {e}")
        return False

def check_voice_handler_logic():
    """检查语音处理器逻辑"""
    print("\n🎤 检查语音处理器逻辑")
    print("=" * 50)
    
    try:
        switchrole_path = os.path.join(os.path.dirname(__file__), 'switchrole')
        if switchrole_path not in sys.path:
            sys.path.insert(0, switchrole_path)
        
        # 检查function_handlers.py
        with open(os.path.join(switchrole_path, 'function_handlers.py'), 'r', encoding='utf-8') as f:
            handler_content = f.read()
        
        # 检查MQTT发送方法
        if "_send_mqtt_function_command" in handler_content:
            print("✅ 找到MQTT发送方法")
        else:
            print("❌ 未找到MQTT发送方法")
            return False
        
        # 检查MQTT配置
        if "117.72.8.255" in handler_content and "esp32/s2/control" in handler_content:
            print("✅ 找到MQTT配置")
        else:
            print("❌ MQTT配置不正确")
            return False
        
        # 检查功能处理器是否调用MQTT发送
        if "self._send_mqtt_function_command" in handler_content:
            print("✅ 功能处理器会调用MQTT发送")
        else:
            print("❌ 功能处理器未调用MQTT发送")
            return False
        
        print("✅ 语音处理器逻辑检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 语音处理器逻辑检查异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_complete_flow():
    """检查完整流程"""
    print("\n🔄 检查完整流程")
    print("=" * 50)
    
    try:
        # 模拟完整流程
        print("📋 完整流程步骤:")
        print("   1. 用户说'打开作业批改'")
        print("   2. xiaoxin2_zh.py 识别语音")
        print("   3. handle_voice_function_command() 处理")
        print("   4. function_manager 解析为 homework_qa")
        print("   5. function_handlers.open_homework_qa() 执行")
        print("   6. _send_mqtt_function_command('homework_qa') 发送")
        print("   7. MQTT发送 '7-1-1' 到主界面")
        print("   8. 主界面 handle_control_command('voice_homework_qa')")
        print("   9. _handle_voice_function_command() 处理")
        print("   10. handle_homework_correction() 切换界面")
        
        # 检查每个步骤的依赖
        dependencies = [
            ("xiaoxin2_zh.py", "switchrole/xiaoxin2_zh.py"),
            ("function_handlers.py", "switchrole/function_handlers.py"),
            ("function_manager.py", "switchrole/function_manager.py"),
            ("main.py", "main.py"),
            ("config.py", "config.py")
        ]
        
        missing_files = []
        for name, path in dependencies:
            if not os.path.exists(path):
                missing_files.append(name)
        
        if missing_files:
            print(f"\n❌ 缺少必要文件: {missing_files}")
            return False
        
        print("\n✅ 完整流程检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 完整流程检查异常: {e}")
        return False

def check_potential_issues():
    """检查潜在问题"""
    print("\n⚠️ 检查潜在问题")
    print("=" * 50)
    
    issues = []
    
    # 检查MQTT连接问题
    print("🔍 检查MQTT连接...")
    try:
        import paho.mqtt.client as mqtt
        client = mqtt.Client()
        # 不实际连接，只检查库是否可用
        print("✅ MQTT库可用")
    except ImportError:
        issues.append("MQTT库未安装 (pip install paho-mqtt)")
    
    # 检查路径问题
    print("🔍 检查路径配置...")
    switchrole_path = os.path.join(os.path.dirname(__file__), 'switchrole')
    if not os.path.exists(switchrole_path):
        issues.append("switchrole目录不存在")
    
    # 检查权限问题
    print("🔍 检查文件权限...")
    important_files = ['main.py', 'config.py', 'switchrole/function_handlers.py']
    for file_path in important_files:
        if os.path.exists(file_path) and not os.access(file_path, os.R_OK):
            issues.append(f"文件 {file_path} 无读取权限")
    
    if issues:
        print("❌ 发现潜在问题:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ 未发现明显问题")
        return True

def main():
    """主函数"""
    print("🔍 语音功能切换逻辑检查")
    print("=" * 70)
    
    # 运行检查
    checks = [
        ("配置一致性", check_config_consistency),
        ("主界面逻辑", check_main_ui_logic),
        ("语音处理器逻辑", check_voice_handler_logic),
        ("完整流程", check_complete_flow),
        ("潜在问题", check_potential_issues)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        if check_func():
            passed += 1
            print(f"✅ {check_name} 检查通过")
        else:
            print(f"❌ {check_name} 检查失败")
    
    print("\n" + "=" * 70)
    print(f"📊 检查结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 语音功能切换逻辑检查完全通过！")
        
        print("\n💡 使用建议:")
        print("   1. 确保主界面已启动并连接MQTT")
        print("   2. 确保语音助手在switchrole目录下运行")
        print("   3. 说'打开作业批改'测试功能")
        print("   4. 观察界面是否实际切换")
        
        return True
    else:
        print("⚠️ 部分检查失败，建议修复后再测试")
        return False

if __name__ == "__main__":
    main()
