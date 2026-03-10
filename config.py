#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5应用程序配置文件
"""

import os

# 窗口配置
WINDOW_CONFIG = {
    'width': 1920,
    'height': 1080,
    'title': '智能学习助手'
}

# 通知窗口配置
NOTIFICATION_CONFIG = {
    'width': 450,   # 350 → 450 (增加宽度以适应更大字体)
    'height': 160,  # 100 → 160 (增加高度以适应更大字体)
    'show_duration': 3  # 显示时长（秒）
}

# MQTT配置
MQTT_CONFIG = {
    'broker': '117.72.8.255',
    'port': 1883,
    'control_topic': 'gesture',  # 程序控制主题（程序接收）
    'hardware_control_topic': 'esp32/s2/control',  # 硬件控制主题（程序发送，不订阅）
    'gesture_topic': 'gesture',  # 手势识别传感器主题
    'gesture_switch_topic': 'gesture_switch',  # 手势模式切换主题
    'notification_topics': ['nf', 'room', 'roomclose'],
    'sa_topic': 'sa'
}

# 控制指令映射
CONTROL_COMMANDS = {
    '6-0-1': 'confirm',      # 确认
    '6-0-2': 'back',         # 返回
    '6-0-3': 'next',         # 下一页/下一个/右边
    '6-0-4': 'prev',         # 上一页/上一个/左边
    '6-0-5': 'up',           # 上滑
    '6-0-6': 'down',         # 下滑

    # 🔧 新增：语音功能切换指令
    '7-1-1': 'voice_homework_correction', # 语音：打开作业批改
    '7-1-2': 'voice_homework_qa',      # 语音：打开作业问答
    '7-1-3': 'voice_music_player',     # 语音：打开音乐播放
    '7-1-4': 'voice_ai_chat',          # 语音：打开AI对话
    '7-1-5': 'voice_settings',         # 语音：打开系统设置
    '7-1-6': 'voice_video_meetings',   # 语音：打开视频连接
    '7-1-7': 'voice_notifications',    # 语音：打开通知功能
    '7-1-8': 'voice_assistant'         # 语音：打开语音助手
}

# 手势识别配置
GESTURE_CONFIG = {
    'delta_volume': 10,      # 音量调节增量
    'delta_brightness': 10,  # 亮度调节增量
    'delta_desk_height': 1,  # 桌子高度调节增量
}

# 设置页面初始值配置
SETTINGS_DEFAULT_VALUES = {
    'volume': 50,          # 音量初始值
    'brightness': 0,       # 亮度初始值
    'desk_height': 1       # 桌子高度初始值（1档）
}

# 手势识别指令映射
GESTURE_COMMANDS = {
    '6-0-1': 'confirm',      # 确认
    '6-0-2': 'back',         # 返回
    '6-0-3': 'right',        # 右滑，增加DELTA
    '6-0-4': 'left',         # 左滑，减少DELTA
    '6-0-5': 'up',           # 上滑，选中上一个变量
    '6-0-6': 'down',         # 下滑，选中下一个变量
    '6-0-7': 'increase',     # 增加DELTA
    '6-0-8': 'decrease',     # 减少DELTA
}

# 设置控制指令（直接传递给设置页面处理）
SETTINGS_COMMANDS = {
    # 音量控制：4-X-X
    '4-0-': 'volume_set',     # 4-0-X 设置音量为X
    '4-2-0': 'volume_up',     # 4-2-0 音量+10
    '4-3-0': 'volume_down',   # 4-3-0 音量-10
    
    # 亮度控制：7-X-X
    '7-0-0': 'brightness_off',  # 7-0-0 关闭亮度
    '7-0-1': 'brightness_on',   # 7-0-1 打开亮度
    '7-1-': 'brightness_set',   # 7-1-X 设置亮度为X
    
    # 桌子高度控制：3-X-X
    '3-0-0': 'desk_level_1',   # 3-0-0 桌子高度1档
    '3-1-0': 'desk_level_2',   # 3-1-0 桌子高度2档
    '3-2-0': 'desk_level_3',   # 3-2-0 桌子高度3档
}

# 结果显示页面配置
RESULT_DISPLAY_CONFIG = {
    'scroll_step': 500,       # 滚动步长（像素）- 增大提升响应速度
    'scroll_smooth': False,   # 是否启用平滑滚动 - 关闭提升响应速度
    'font_size': 14,         # 正常字体大小
    'title_font_size': 20,   # 标题字体大小
    'max_content_width': 900 # 内容最大宽度
}

# 功能配置
FEATURES = {
    'school': {
        'name': '学校',
        'enabled_functions': ['settings', 'pigai', 'batch_homework', 'book_management', 'mettings', 'voice', 'gesture']
    },
    'home': {
        'name': '家庭',
        'enabled_functions': ['settings', 'pigai', 'mettings', 'voice', 'answer', 'note', 'gesture', 'thinking_guidance']
    }
}

# 功能图标映射
FUNCTION_ICONS = {
    'settings': 'img/settings.png',
    'mettings': 'img/mettings.png',
    'note': 'img/note.png',
    'voice': 'img/voice.png',
    'answer': 'img/answer.png',
    'pigai': 'img/pigai.png',
    'batch_homework': 'img/piliangzuoye.png',
    'gesture': 'img/reading.png',
    'book_management': 'img/tushuguanli.png',
    'thinking_guidance': 'img/silujieda.png'
}

# 功能名称映射
FUNCTION_NAMES = {
    'settings': '设置',
    'mettings': '视频连接',
    'note': '通知',
    'voice': '语音助手',
    'answer': '作业问答',
    'pigai': '作业批改',
    'batch_homework': '批量批改',
    'gesture': '指尖单词',
    'book_management': '图书管理',
    'thinking_guidance': '思路解答'
}

# 视频会议配置
VIDEO_CONFIG = {
    'mirotalk_base_url': 'https://p2p.mirotalk.com',
    'username': 'student'
}

# 数据库配置 - 敏感信息请通过环境变量配置
DATABASE_CONFIG = {
    'host': os.environ.get('DATABASE_HOST', 'localhost'),
    'port': int(os.environ.get('DATABASE_PORT', 3306)),
    'user': os.environ.get('DATABASE_USER', 'root'),
    'password': os.environ.get('DATABASE_PASSWORD', ''),
    'charset': 'utf8mb4'
}

# 数据库表配置
DATABASE_TABLES = {
    'school_mode': {
        'database': 'student_info',
        'table': 'student',
        'columns': {
            'id': 'INT AUTO_INCREMENT PRIMARY KEY',
            'name': 'VARCHAR(100)',
            'gender': 'VARCHAR(10)', 
            'subject': 'TEXT',  # 存储薄弱知识点
            'teacher': 'VARCHAR(100)'
        }
    },
    'home_mode': {
        'database': 'error',
        'table': 'error_details',
        'columns': {
            'id': 'INT AUTO_INCREMENT PRIMARY KEY',
            'time': 'DATETIME',
            'error': 'TEXT',  # 存储错误题号
            'details': 'TEXT'  # 存储薄弱知识点
        }
    },
    'batch_homework': {
        'database': 'data_info',
        'table': 'studentinfo',
        'columns': {
            'id': 'INT AUTO_INCREMENT PRIMARY KEY',
            'time': 'DATETIME',
            'info': 'TEXT'  # 存储完整的分析结果JSON
        }
    },
    'book_management': {
        'database': 'data_info',
        'table': 'book',
        'columns': {
            'id': 'INT AUTO_INCREMENT PRIMARY KEY',
            'bookname': 'VARCHAR(255)',  # 存储图书名称
            'studentname': 'VARCHAR(100)',  # 存储学生姓名
            'time': 'DATETIME'  # 存储记录时间
        }
    }
}

 

"""
低头检测系统配置文件
"""

# 近视风险检测阈值（像素）
# 当鼻子到图片底部距离小于此值时，认为眼睛离桌面太近，可能诱发近视
MYOPIA_RISK_THRESHOLD = 200

# 低头检测相关阈值
HEAD_DOWN_THRESHOLDS = {
    'mild': 0.15,      # 轻微低头阈值
    'moderate': 0.3,   # 中度低头阈值
    # 大于moderate视为严重低头
}

# 置信度阈值
CONFIDENCE_THRESHOLD = 0.5

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp')

# 输出文件名
OUTPUT_FILES = {
    'single_detection': 'head_down_detection_result.jpg',
    'batch_comparison': 'head_down_comparison.jpg',
    'detailed_report': 'head_down_report.txt'
}

# 姿势检测配置
POSE_DETECTION_CONFIG = {
    'detection_interval': 10.0,  # 检测间隔（秒）
    'save_detection_images': False,  # 是否保存检测结果图片
    'detection_folder': 'pose_detections',  # 保存检测结果的文件夹
    'max_stored_results': 100,  # 最多保存的检测结果数量
    'auto_cleanup': True,  # 是否自动清理旧的检测结果
    'alert_on_bad_posture': True,  # 检测到不良姿势时是否提醒
    'consecutive_bad_posture_threshold': 3,  # 连续检测到不良姿势多少次后发出警告
    'alert_on_myopia_risk': True,  # 检测到近视风险时是否提醒
    'consecutive_myopia_risk_threshold': 3,  # 连续检测到近视风险多少次后发出警告
}

# 摄像头配置
CAMERA_CONFIG = {
    'face_camera_name': "UNIQUESKY_CAR_CAMERA: Integrate",  # 人脸识别摄像头名称
    'photo_camera_name': "DECXIN: DECXIN",  # 试卷拍照摄像头名称
    'default_face_camera_index': 0,  # 默认人脸识别摄像头索引
    'default_photo_camera_index': 1,  # 默认拍照摄像头索引
    'preview_width': 2560,  # 预览窗口宽度
    'preview_height': 1440,  # 预览窗口高度
    'frame_width': 2560,  # 预览帧宽度
    'frame_height': 1440,  # 预览帧高度
    'capture_width': 1920,  # 拍照分辨率宽度
    'capture_height': 1080,  # 拍照分辨率高度
    'face_photo_width': 1920,  # 人脸识别照片宽度
    'face_photo_height': 1080,  # 人脸识别照片高度
    'photo_width': 1920,  # 作业拍照宽度
    'photo_height': 1080,  # 作业拍照高度
    'fps': 10,  # 帧率
} 