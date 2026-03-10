#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用户记忆管理模块
功能：
1. 保存和加载用户个人信息
2. 分析用户偏好和行为模式
3. 动态调整AI人设
4. 智能音乐推荐
"""

import json
import os
import re
import time
from datetime import datetime
from collections import defaultdict, Counter
from dotenv import load_dotenv

# 加载环境配置
load_dotenv("xiaoxin.env")

class UserMemoryManager:
    """用户记忆管理器"""
    
    def __init__(self, memory_file=None):
        # 🔧 修复路径问题：使用绝对路径避免switchrole/switchrole路径重复
        if memory_file:
            self.memory_file = memory_file
        else:
            # 获取当前脚本所在目录（switchrole目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            memory_filename = os.environ.get("user_memory_file", "user_memory.json")
            self.memory_file = os.path.join(current_dir, memory_filename)
        
        self.memory_data = self.load_memory()
        self.preference_threshold = int(os.environ.get("music_preference_threshold", "3"))
        
    def load_memory(self):
        """加载用户记忆数据"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ 加载用户记忆数据: {self.memory_file}")
                return data
            except Exception as e:
                print(f"⚠️ 加载用户记忆失败: {e}")
                return self._create_default_memory()
        else:
            print(f"📝 创建新的用户记忆文件: {self.memory_file}")
            return self._create_default_memory()
    
    def _create_default_memory(self):
        """创建默认的记忆结构"""
        return {
            "user_info": {
                "name": "",
                "grade": "",
                "age": "",
                "school": "",
                "grade_level": "",  # primary_low, primary_high, middle_school, high_school
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "preferences": {
                "music": {
                    "artists": defaultdict(int),
                    "songs": defaultdict(int),
                    "genres": defaultdict(int)
                },
                "activities": defaultdict(int),
                "subjects": defaultdict(int),
                "topics": defaultdict(int)
            },
            "conversation_history": [],
            "interaction_stats": {
                "total_conversations": 0,
                "music_requests": 0,
                "study_requests": 0,
                "casual_chats": 0
            }
        }
    
    def save_memory(self):
        """保存记忆数据到文件"""
        try:
            # 更新最后修改时间
            self.memory_data["user_info"]["last_updated"] = datetime.now().isoformat()
            
            # 转换defaultdict为普通dict以便JSON序列化
            memory_copy = json.loads(json.dumps(self.memory_data, default=dict))
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(memory_copy, f, ensure_ascii=False, indent=2)
            print(f"💾 用户记忆已保存: {self.memory_file}")
            return True
        except Exception as e:
            print(f"❌ 保存用户记忆失败: {e}")
            return False
    
    def update_user_info(self, info_dict):
        """更新用户基本信息"""
        for key, value in info_dict.items():
            if key in self.memory_data["user_info"] and value:
                self.memory_data["user_info"][key] = value
                print(f"📝 更新用户信息: {key} = {value}")
        
        # 根据年级设置等级
        if "grade" in info_dict:
            self.memory_data["user_info"]["grade_level"] = self._determine_grade_level(info_dict["grade"])
        
        self.save_memory()
    
    def _determine_grade_level(self, grade_str):
        """根据年级字符串确定等级"""
        if not grade_str:
            return "primary_low"
        
        # 提取数字
        numbers = re.findall(r'\d+', str(grade_str))
        if not numbers:
            return "primary_low"
        
        grade_num = int(numbers[0])
        
        if grade_num <= 3:
            return "primary_low"      # 小学低年级 1-3年级
        elif grade_num <= 6:
            return "primary_high"     # 小学高年级 4-6年级  
        elif grade_num <= 9:
            return "middle_school"    # 初中 7-9年级
        else:
            return "high_school"      # 高中及以上 10年级+
    
    def get_current_prompt(self):
        """获取当前适合的AI人设提示词"""
        grade_level = self.memory_data["user_info"].get("grade_level", "primary_low")
        
        # 从环境变量中获取对应的提示词
        prompt_key = f"sysprompt_{grade_level}"
        prompt = os.environ.get(prompt_key, os.environ.get("sysprompt_base", ""))
        
        # 如果有用户姓名，添加到提示词中
        user_name = self.memory_data["user_info"].get("name", "")
        if user_name and prompt:
            prompt += f" 用户的名字是{user_name}，你可以亲切地称呼他的名字。"
        
        # 🔧 修复：移除强制添加音乐偏好，避免AI回答总是提到周杰伦
        # 只有在用户主动询问音乐相关内容时，才考虑音乐偏好
        # favorite_artist = self.get_favorite_music_artist()
        # if favorite_artist:
        #     prompt += f" 用户喜欢听{favorite_artist}的歌曲。"
        
        print(f"🎭 使用AI人设: {grade_level} - {user_name}")
        print(f"📝 不再强制添加音乐偏好，避免AI回答总是提到周杰伦")
        return prompt
    
    def record_conversation(self, user_input, ai_response, conversation_type="general"):
        """记录对话历史"""
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "type": conversation_type
        }
        
        self.memory_data["conversation_history"].append(conversation)
        
        # 只保留最近的100条对话
        if len(self.memory_data["conversation_history"]) > 100:
            self.memory_data["conversation_history"] = self.memory_data["conversation_history"][-100:]
        
        # 更新统计数据
        self.memory_data["interaction_stats"]["total_conversations"] += 1
        if conversation_type == "music":
            self.memory_data["interaction_stats"]["music_requests"] += 1
        elif conversation_type == "study":
            self.memory_data["interaction_stats"]["study_requests"] += 1
        else:
            self.memory_data["interaction_stats"]["casual_chats"] += 1
        
        # 分析并更新偏好
        self._analyze_preferences(user_input, conversation_type)
        
        self.save_memory()
    
    def _analyze_preferences(self, user_input, conversation_type):
        """分析用户偏好"""
        user_input_lower = user_input.lower()
        
        # 音乐偏好分析
        if conversation_type == "music" or "播放" in user_input or "音乐" in user_input or "歌" in user_input:
            self._analyze_music_preference(user_input)
        
        # 学科偏好分析
        subjects = ["数学", "语文", "英语", "科学", "历史", "地理", "物理", "化学", "生物"]
        for subject in subjects:
            if subject in user_input:
                self.memory_data["preferences"]["subjects"][subject] += 1
        
        # 活动偏好分析
        activities = ["游戏", "阅读", "运动", "画画", "唱歌", "跳舞", "编程", "手工"]
        for activity in activities:
            if activity in user_input:
                self.memory_data["preferences"]["activities"][activity] += 1
    
    def _analyze_music_preference(self, user_input):
        """分析音乐偏好"""
        # 常见歌手名单
        artists = [
            "周杰伦", "邓紫棋", "林俊杰", "王力宏", "陈奕迅", "张学友", "刘德华", 
            "张杰", "薛之谦", "毛不易", "李荣浩", "华晨宇", "张碧晨", "田馥甄",
            "蔡徐坤", "王俊凯", "易烊千玺", "王源", "鹿晗", "吴亦凡", "张艺兴"
        ]
        
        # 检查歌手
        for artist in artists:
            if artist in user_input:
                self.memory_data["preferences"]["music"]["artists"][artist] += 1
                print(f"🎵 记录音乐偏好: 喜欢{artist}")
        
        # 检查歌曲名 (简单的歌曲名检测)
        song_patterns = [
            r"《(.+?)》", #r""(.+?)"", r"'(.+?)'", r'"(.+?)"'
        ]
        
        for pattern in song_patterns:
            matches = re.findall(pattern, user_input)
            for match in matches:
                if len(match) > 1 and len(match) < 20:  # 合理的歌曲名长度
                    self.memory_data["preferences"]["music"]["songs"][match] += 1
                    print(f"🎵 记录歌曲偏好: {match}")
    
    def get_favorite_music_artist(self):
        """获取最喜欢的歌手"""
        artists = self.memory_data["preferences"]["music"]["artists"]
        if not artists:
            return None
        
        # 找到播放次数最多的歌手
        most_played = max(artists.items(), key=lambda x: x[1])
        if most_played[1] >= self.preference_threshold:
            return most_played[0]
        return None
    
    def should_auto_recommend_music(self, user_input):
        """判断是否应该自动推荐音乐"""
        auto_recommend = os.environ.get("auto_recommend_music", "true").lower() == "true"
        if not auto_recommend:
            return False, None
        
        # 🔧 关键修复：检查用户是否指定了具体歌曲或歌手
        # 如果用户明确指定了歌曲名或歌手，则不进行自动推荐
        
        # 1. 检查是否包含具体的歌曲名称模式
        song_indicators = [
            r"播放.*?的.*?",  # "播放xxx的xxx"
            r"听.*?的.*?",    # "听xxx的xxx" 
            r"来.*?的.*?",    # "来xxx的xxx"
            r"放.*?的.*?",    # "放xxx的xxx"
            r"《.+?》",       # 《歌曲名》
            r'".+?"',         # "歌曲名"
            r"'.+?'",         # '歌曲名'
        ]
        
        for pattern in song_indicators:
            if re.search(pattern, user_input):
                print(f"🎵 检测到具体歌曲指定，不进行自动推荐: {user_input}")
                return False, None
        
        # 2. 检查是否包含知名歌手名称
        known_artists = [
            "周杰伦", "邓紫棋", "林俊杰", "王力宏", "陈奕迅", "张学友", "刘德华", 
            "张杰", "薛之谦", "毛不易", "李荣浩", "华晨宇", "张碧晨", "田馥甄",
            "蔡徐坤", "王俊凯", "易烊千玺", "王源", "鹿晗", "吴亦凡", "张艺兴",
            "邓丽君", "中道美雪", "费玉清", "童安格", "张信哲", "齐秦", "罗大佑"
        ]
        
        for artist in known_artists:
            if artist in user_input:
                print(f"🎵 检测到指定歌手 {artist}，不进行自动推荐")
                return False, None
        
        # 3. 只有在模糊请求时才进行自动推荐
        vague_music_requests = [
            "播放音乐", "放首歌", "听音乐", "来首歌", "放歌", "音乐", "听歌", "放点音乐"
        ]
        
        for request in vague_music_requests:
            if user_input.strip() == request or user_input.strip() in ["播放", "放", "听"]:
                print(f"🎵 检测到模糊音乐请求，启用自动推荐")
                favorite_artist = self.get_favorite_music_artist()
                if favorite_artist:
                    print(f"🤖 推荐用户喜欢的歌手: {favorite_artist}")
                    return True, favorite_artist
        
        return False, None
    
    def get_user_info_status(self):
        """检查用户信息完整性"""
        required_fields = ["name", "grade"]
        missing_fields = []
        
        for field in required_fields:
            if not self.memory_data["user_info"].get(field):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    def extract_user_info_from_response(self, user_response):
        """从用户回答中提取个人信息"""
        info = {}
        
        # 提取姓名
        name_patterns = [
            r"我叫(.+)", r"我的名字是(.+)", r"叫我(.+)", r"我是(.+)",
            r"名字.*?是(.+)", r"称呼.*?(.+)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, user_response)
            if match:
                name = match.group(1).strip()
                # 清理常见的无关词
                name = re.sub(r'[，。！？,.\!?].*', '', name).strip()
                if len(name) > 0 and len(name) < 10:
                    info["name"] = name
                    break
        
        # 提取年级
        grade_patterns = [
            r"(\d+)年级", r"读(\d+)年级", r"上(\d+)年级", r"(\d+)级",
            r"小学(\d+)年级", r"初中(\d+)年级", r"高中(\d+)年级",
            r"读(一|二|三|四|五|六|七|八|九|十|十一|十二)年级",
            r"(一|二|三|四|五|六|七|八|九|十|十一|十二)年级",
            r"读(1|2|3|4|5|6|7|8|9|10|11|12)年级"
        ]
        
        # 中文数字转阿拉伯数字映射
        chinese_num_map = {
            "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6",
            "七": "7", "八": "8", "九": "9", "十": "10", "十一": "11", "十二": "12"
        }
        
        for pattern in grade_patterns:
            match = re.search(pattern, user_response)
            if match:
                grade_num = match.group(1)
                # 如果是中文数字，转换为阿拉伯数字
                if grade_num in chinese_num_map:
                    grade_num = chinese_num_map[grade_num]
                info["grade"] = f"{grade_num}年级"
                break
        
        return info
    
    def generate_welcome_response(self):
        """生成个性化欢迎语"""
        user_name = self.memory_data["user_info"].get("name", "")
        grade = self.memory_data["user_info"].get("grade", "")
        
        if user_name and grade:
            return f"欢迎回来，{user_name}！我记得你在读{grade}。今天想做什么呢？"
        elif user_name:
            return f"欢迎回来，{user_name}！今天想做什么呢？"
        else:
            return "你好！我是广和通，你的AI助手。请问我该怎么称呼你呢？你现在读几年级？"

# 全局用户记忆管理器实例
user_memory = UserMemoryManager()

def get_user_memory():
    """获取用户记忆管理器实例"""
    return user_memory

def update_user_info(info_dict):
    """更新用户信息"""
    return user_memory.update_user_info(info_dict)

def record_conversation(user_input, ai_response, conversation_type="general"):
    """记录对话"""
    return user_memory.record_conversation(user_input, ai_response, conversation_type)

def get_current_prompt():
    """获取当前AI人设"""
    return user_memory.get_current_prompt()

def should_auto_recommend_music(user_input):
    """检查是否需要自动推荐音乐"""
    return user_memory.should_auto_recommend_music(user_input)

def get_user_info_status():
    """获取用户信息状态"""
    return user_memory.get_user_info_status()

def extract_user_info_from_response(user_response):
    """从回答中提取用户信息"""
    return user_memory.extract_user_info_from_response(user_response)

def generate_welcome_response():
    """生成欢迎语"""
    return user_memory.generate_welcome_response()

if __name__ == "__main__":
    # 测试代码
    print("🧪 测试用户记忆管理模块")
    
    # 测试信息提取
    test_responses = [
        "我叫小明，我现在读3年级",
        "我的名字是张小红，上5年级",
        "叫我李华就好了，我在读初中2年级"
    ]
    
    for response in test_responses:
        info = extract_user_info_from_response(response)
        print(f"输入: {response}")
        print(f"提取: {info}")
        print("---") 