#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
功能管理器模块
支持通过语音命令打开不同的功能页面
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FunctionCategory(Enum):
    """功能分类"""
    EDUCATION = "education"      # 教育功能
    ENTERTAINMENT = "entertainment"  # 娱乐功能
    UTILITY = "utility"         # 工具功能
    SYSTEM = "system"           # 系统功能

class DeviceMode(Enum):
    """设备模式"""
    SCHOOL = "school"           # 学校模式
    HOME = "home"              # 家庭模式
    STUDY = "study"            # 学习模式
    FREE = "free"              # 自由模式

@dataclass
class FunctionInfo:
    """功能信息"""
    id: str
    name: str
    description: str
    category: FunctionCategory
    available_modes: List[DeviceMode]
    voice_commands: List[str]
    handler_function: str
    required_params: Dict = None
    
    def __post_init__(self):
        if self.required_params is None:
            self.required_params = {}

class FunctionManager:
    """功能管理器"""
    
    def __init__(self):
        self.current_mode = DeviceMode.HOME
        self.functions = {}
        self.voice_patterns = {}
        self.function_handlers = {}
        
        # 初始化功能列表
        self._init_functions()
        self._compile_voice_patterns()
    
    def _init_functions(self):
        """初始化功能列表"""
        
        # 教育功能 - 作业批改
        homework_correction = FunctionInfo(
            id="homework_correction",
            name="作业批改",
            description="智能拍照搜题和作业批改功能",
            category=FunctionCategory.EDUCATION,
            available_modes=[DeviceMode.SCHOOL, DeviceMode.STUDY, DeviceMode.HOME],
            voice_commands=[
                "打开作业批改",
                "作业批改功能",
                "开始作业批改",
                "拍照搜题",
                "批改作业",
                "搜题功能"
            ],
            handler_function="open_homework_correction"
        )

        # 教育功能 - 作业问答
        homework_qa = FunctionInfo(
            id="homework_qa",
            name="作业问答",
            description="作业问答和答疑功能",
            category=FunctionCategory.EDUCATION,
            available_modes=[DeviceMode.HOME, DeviceMode.STUDY],
            voice_commands=[
                "打开作业问答",
                "作业问答功能",
                "开始作业问答",
                "作业答疑",
                "题目解答",
                "问答功能"
            ],
            handler_function="open_homework_qa"
        )
        
        # 音乐播放功能
        music_player = FunctionInfo(
            id="music_player",
            name="音乐播放",
            description="音乐播放和管理功能",
            category=FunctionCategory.ENTERTAINMENT,
            available_modes=[DeviceMode.HOME, DeviceMode.FREE],
            voice_commands=[
                "打开音乐播放器",
                "音乐功能",
                "播放音乐",
                "音乐播放",
                "听音乐"
            ],
            handler_function="open_music_player"
        )
        
        # 语音对话功能
        ai_chat = FunctionInfo(
            id="ai_chat",
            name="智能对话",
            description="AI智能对话和问答功能",
            category=FunctionCategory.UTILITY,
            available_modes=[DeviceMode.HOME, DeviceMode.STUDY, DeviceMode.FREE, DeviceMode.SCHOOL],
            voice_commands=[
                "智能对话",
                "AI对话",
                "聊天功能",
                "问答功能",
                "开始对话"
            ],
            handler_function="open_ai_chat"
        )
        
        # 系统设置功能
        system_settings = FunctionInfo(
            id="system_settings",
            name="系统设置",
            description="系统设置和配置功能",
            category=FunctionCategory.SYSTEM,
            available_modes=[DeviceMode.HOME, DeviceMode.FREE],
            voice_commands=[
                "打开设置",
                "系统设置",
                "设置功能",
                "配置系统"
            ],
            handler_function="open_system_settings"
        )
        
        # 学习资源功能
        study_resources = FunctionInfo(
            id="study_resources",
            name="学习资源",
            description="学习资源和课程材料管理",
            category=FunctionCategory.EDUCATION,
            available_modes=[DeviceMode.SCHOOL, DeviceMode.STUDY],
            voice_commands=[
                "学习资源",
                "课程材料",
                "打开学习中心",
                "学习功能"
            ],
            handler_function="open_study_resources"
        )
        
        # 将功能添加到管理器
        for func in [homework_correction, homework_qa, music_player, ai_chat, system_settings, study_resources]:
            self.functions[func.id] = func
        
        logger.info(f"✅ 已加载 {len(self.functions)} 个功能")
    
    def _compile_voice_patterns(self):
        """编译语音命令模式"""
        self.voice_patterns = {}
        
        for func_id, func_info in self.functions.items():
            for command in func_info.voice_commands:
                # 创建正则表达式模式
                pattern = self._create_pattern(command)
                self.voice_patterns[pattern] = func_id
        
        logger.info(f"✅ 已编译 {len(self.voice_patterns)} 个语音命令模式")
    
    def _create_pattern(self, command: str) -> str:
        """创建语音命令的正则表达式模式"""
        # 处理常见的语音识别变体
        pattern = command
        
        # 替换常见变体
        replacements = {
            "打开": "(打开|开启|启动|进入)",
            "播放": "(播放|放|听)",
            "功能": "(功能|模式)?",
            "设置": "(设置|配置)"
        }
        
        for old, new in replacements.items():
            pattern = pattern.replace(old, new)
        
        # 添加可选的前缀和后缀
        pattern = f"(请|帮我|我要|我想)?{pattern}(吧|呢|一下)?"
        
        return pattern
    
    def set_mode(self, mode: DeviceMode):
        """设置当前设备模式"""
        self.current_mode = mode
        logger.info(f"📱 设备模式已切换到: {mode.value}")
        
        # 获取当前模式下可用的功能
        available_functions = self.get_available_functions()
        logger.info(f"📋 当前模式下可用功能: {[f.name for f in available_functions]}")
    
    def get_available_functions(self) -> List[FunctionInfo]:
        """获取当前模式下可用的功能"""
        available = []
        for func_info in self.functions.values():
            if self.current_mode in func_info.available_modes:
                available.append(func_info)
        return available
    
    def parse_voice_command(self, user_input: str) -> Optional[FunctionInfo]:
        """解析语音命令，返回匹配的功能"""
        user_input = user_input.strip()
        
        # 遍历所有语音模式
        for pattern, func_id in self.voice_patterns.items():
            if re.search(pattern, user_input, re.IGNORECASE):
                func_info = self.functions[func_id]
                
                # 检查功能是否在当前模式下可用
                if self.current_mode in func_info.available_modes:
                    logger.info(f"🎯 识别到功能命令: '{user_input}' -> {func_info.name}")
                    return func_info
                else:
                    logger.warning(f"⚠️ 功能 '{func_info.name}' 在当前模式 '{self.current_mode.value}' 下不可用")
                    return None
        
        return None
    
    def register_function_handler(self, function_id: str, handler: Callable):
        """注册功能处理器"""
        self.function_handlers[function_id] = handler
        logger.info(f"📝 已注册功能处理器: {function_id}")
    
    def execute_function(self, function_id: str, **kwargs) -> bool:
        """执行功能"""
        if function_id in self.function_handlers:
            try:
                handler = self.function_handlers[function_id]
                result = handler(**kwargs)
                logger.info(f"✅ 功能执行成功: {function_id}")
                return result
            except Exception as e:
                logger.error(f"❌ 功能执行失败: {function_id}, 错误: {e}")
                return False
        else:
            logger.warning(f"⚠️ 未找到功能处理器: {function_id}")
            return False
    
    def get_function_list_text(self) -> str:
        """获取当前模式下功能列表的文本描述"""
        available_functions = self.get_available_functions()
        
        if not available_functions:
            return f"当前 {self.current_mode.value} 模式下没有可用功能。"
        
        text = f"当前 {self.current_mode.value} 模式下可用功能：\n"
        
        # 按分类组织功能
        categories = {}
        for func in available_functions:
            cat_name = func.category.value
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(func)
        
        category_names = {
            "education": "📚 教育功能",
            "entertainment": "🎵 娱乐功能", 
            "utility": "🔧 工具功能",
            "system": "⚙️ 系统功能"
        }
        
        for cat_id, functions in categories.items():
            cat_display = category_names.get(cat_id, cat_id)
            text += f"\n{cat_display}:\n"
            for func in functions:
                # 显示主要的语音命令
                main_command = func.voice_commands[0] if func.voice_commands else "无"
                text += f"  • {func.name} - 说 '{main_command}'\n"
        
        return text
    
    def get_mode_switch_help(self) -> str:
        """获取模式切换帮助信息"""
        return """模式切换命令：
• "切换到学校模式" - 启用教育相关功能
• "切换到家庭模式" - 启用娱乐和基础功能  
• "切换到学习模式" - 启用学习和教育功能
• "切换到自由模式" - 启用所有功能

说 "显示功能列表" 可以查看当前模式下的可用功能。"""

# 全局功能管理器实例
_global_function_manager = None

def get_function_manager() -> FunctionManager:
    """获取全局功能管理器实例"""
    global _global_function_manager
    if _global_function_manager is None:
        _global_function_manager = FunctionManager()
    return _global_function_manager

def parse_voice_command(user_input: str) -> Optional[FunctionInfo]:
    """解析语音命令（便捷函数）"""
    return get_function_manager().parse_voice_command(user_input)

def set_device_mode(mode: str):
    """设置设备模式（便捷函数）"""
    try:
        device_mode = DeviceMode(mode.lower())
        get_function_manager().set_mode(device_mode)
        return True
    except ValueError:
        logger.error(f"❌ 无效的设备模式: {mode}")
        return False

def get_available_functions_text() -> str:
    """获取可用功能列表文本（便捷函数）"""
    return get_function_manager().get_function_list_text()

if __name__ == "__main__":
    # 测试功能管理器
    print("🧪 测试功能管理器")
    print("=" * 50)
    
    manager = get_function_manager()
    
    # 测试不同模式
    for mode in [DeviceMode.SCHOOL, DeviceMode.HOME, DeviceMode.STUDY]:
        print(f"\n📱 切换到 {mode.value} 模式:")
        manager.set_mode(mode)
        print(manager.get_function_list_text())
    
    # 测试语音命令解析
    test_commands = [
        "打开作业批改",
        "播放音乐",
        "我想听音乐",
        "帮我打开设置",
        "学习资源",
        "智能对话功能"
    ]
    
    print(f"\n🎤 测试语音命令解析:")
    manager.set_mode(DeviceMode.HOME)
    
    for command in test_commands:
        result = manager.parse_voice_command(command)
        if result:
            print(f"  '{command}' -> ✅ {result.name}")
        else:
            print(f"  '{command}' -> ❌ 未识别")
    
    print("\n✅ 测试完成") 