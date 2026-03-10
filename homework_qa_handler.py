# -*- coding: utf-8 -*-
"""
作业问答处理器
包含拍照、语音识别、数据上传的完整流程
现在支持分步语音识别：科目识别和困惑点识别
"""

import os
import json
import logging
import base64
import requests
import threading
import time
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from camera_handler import CameraHandler
from mqtt_handler import MQTTHandler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SubjectRecognitionThread(QThread):
    """科目识别线程"""
    
    # 信号定义
    recognition_completed = pyqtSignal(str)  # 识别完成信号 (科目)
    recognition_failed = pyqtSignal(str)  # 识别失败信号
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.recognizer = None
        
    def run(self):
        """执行科目识别"""
        try:
            logger.info("开始科目识别...")

            
            # 导入语音识别模块
            from voice_recognition import AliCloudVoiceRecognizer
            
            # 创建语音识别器
            self.recognizer = AliCloudVoiceRecognizer()
            
            # 执行科目识别
            subject = self.recognizer.recognize_subject(duration=5)
            
            if subject:
                logger.info(f"科目识别完成: {subject}")
                self.recognition_completed.emit(subject)
                
            else:
                logger.error("科目识别失败")
                self.recognition_failed.emit("科目识别失败")
                
            
        except Exception as e:
            logger.error(f"科目识别过程失败: {e}")
            self.recognition_failed.emit(str(e))
            
    
    def stop_recognition(self):
        """停止科目识别"""
        self.is_recording = False
        if self.recognizer:
            self.recognizer.stop_recording()
        


class DifficultyRecognitionThread(QThread):
    """困惑点识别线程"""
    
    # 信号定义
    recognition_completed = pyqtSignal(str)  # 识别完成信号 (困惑点)
    recognition_failed = pyqtSignal(str)  # 识别失败信号
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.recognizer = None
        
    def run(self):
        """执行困惑点识别"""
        try:
            logger.info("开始困惑点识别...")
            
            # 导入语音识别模块
            from voice_recognition import AliCloudVoiceRecognizer
            
            # 创建语音识别器
            self.recognizer = AliCloudVoiceRecognizer()
            
            # 执行困惑点识别
           
            difficulty = self.recognizer.recognize_difficulty(duration=5)
            
            if difficulty:
                logger.info(f"困惑点识别完成: {difficulty}")
                self.recognition_completed.emit(difficulty)
               
            else:
                logger.error("困惑点识别失败")
                self.recognition_failed.emit("困惑点识别失败")
                
            
        except Exception as e:
            logger.error(f"困惑点识别过程失败: {e}")
            self.recognition_failed.emit(str(e))
            
    
    def stop_recognition(self):
        """停止困惑点识别"""
        self.is_recording = False
        if self.recognizer:
            self.recognizer.stop_recording()
        


class HomeworkQAHandler(QObject):
    """作业问答处理器"""
    
    # 信号定义
    process_started = pyqtSignal()  # 流程开始信号
    step_completed = pyqtSignal(int)  # 步骤完成信号 (step_number)
    photo_captured = pyqtSignal(str)  # 拍照完成信号 (photo_path)
    subject_recognition_started = pyqtSignal()  # 科目识别开始信号
    subject_recognition_completed = pyqtSignal(str)  # 科目识别完成信号
    difficulty_recognition_started = pyqtSignal()  # 困惑点识别开始信号
    difficulty_recognition_completed = pyqtSignal(str)  # 困惑点识别完成信号
    upload_started = pyqtSignal()  # 上传开始信号
    upload_completed = pyqtSignal(dict)  # 上传完成信号
    process_completed = pyqtSignal(dict)  # 整个流程完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    back_requested = pyqtSignal()  # 返回请求信号
    
    def __init__(self):
        super().__init__()
        
        # 组件初始化
        self.camera_handler = None
        self.mqtt_handler = None
        self.subject_thread = None
        self.difficulty_thread = None
        
        # 流程状态
        self.current_step = 0  # 当前步骤：0=未开始, 1=拍照, 2=科目识别, 3=困惑点识别, 4=上传
        self.is_processing = False
        self.waiting_for_mqtt = False
        
        # 数据存储
        self.photo_path = None
        self.subject = None  # 科目
        self.difficulty = None  # 难点
        self.photo_base64 = None
        
        # 安全机制
        self.mqtt_ready = False
        
        # 初始化组件
        self._init_components()
        
        # 延迟启用MQTT响应
        QTimer.singleShot(3000, self._enable_mqtt_response)
    
    def _init_components(self):
        """初始化各个组件"""
        try:
            # 初始化摄像头处理器
            self.camera_handler = CameraHandler()
            # 设置照片保存文件夹
            self.camera_handler.photo_folder = "homework_qa_photos"
            self.camera_handler.photo_captured.connect(self._on_photo_captured)
            self.camera_handler.error_occurred.connect(self._on_camera_error)
            
            
            # 初始化MQTT处理器
            self.mqtt_handler = MQTTHandler()
            self.mqtt_handler.control_command_received.connect(self._on_mqtt_commmand)
            self.mqtt_handler.start()
            
            logger.info("作业问答处理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            self.error_occurred.emit(f"初始化组件失败: {e}")
    
    def _enable_mqtt_response(self):
        """启用MQTT响应"""
        self.mqtt_ready = True
        logger.info("作业问答MQTT响应已启用")
    
    def start_process(self):
        """开始作业问答流程"""
        if self.is_processing:
            self.error_occurred.emit("系统正在处理中，请稍候")
            return
        
        logger.info("开始作业问答流程")
        self.is_processing = True
        self.current_step = 1
        self.photo_path = None
        self.subject = None
        self.difficulty = None
        self.photo_base64 = None
        
        self.process_started.emit()
        
        # 进入第一步：等待拍照
        self._wait_for_step1_photo()
    
    def _wait_for_step1_photo(self):
        """等待第一步拍照"""
        logger.info("请确认拍照")
        self.waiting_for_mqtt = True
    
    def _on_mqtt_command(self, command: str):
        """处理MQTT控制指令"""
        logger.info(f"收到MQTT指令: {command} (当前步骤: {self.current_step})")
        
        if not self.mqtt_ready or not self.is_processing:
            logger.info(f"忽略MQTT指令: {command}")
            return
        
        if command == 'back':
            # 返回指令
            logger.info("收到返回信号")
            self._reset_process()
            self.back_requested.emit()
            return
        
        if command == 'next' and self.current_step == 0:
            # 流程完成后，6-0-3 返回功能选择
            logger.info("流程已完成，返回功能选择")
            self.back_requested.emit()
            return
        
        if not self.waiting_for_mqtt:
            logger.info(f"当前不等待MQTT指令，忽略: {command}")
            return
        
        if self.current_step == 1 and command == 'confirm':
            # 第一步：拍照
            self._start_photo_capture()
        elif self.current_step == 2 and command == 'confirm':
            # 第二步：科目识别
            self._start_subject_recognition()
        elif self.current_step == 3 and command == 'confirm':
            # 第三步：困惑点识别
            self._start_difficulty_recognition()
        elif self.current_step == 4 and command == 'confirm':
            # 第四步：上传
            self._start_upload()
    
    def _start_photo_capture(self):
        """开始拍照"""
        try:
            logger.info("开始执行拍照...")
            self.waiting_for_mqtt = False
            
            # 清除旧照片
            self.camera_handler.clear_photos()
            
            # 拍摄单张照片
            success = self.camera_handler.capture_photos_for_homework(photo_count=1)
            logger.info(f"拍照结果: {success}")
            
        except Exception as e:
            logger.error(f"拍照失败: {e}")
            self.error_occurred.emit(f"拍照失败: {e}")
            self._reset_process()
    
    def _on_photo_captured(self, success: bool):
        """处理拍照结果"""
        logger.info(f"拍照完成，成功: {success}")
        
        if not success:
            self.error_occurred.emit("拍照失败，请重试")
            self._reset_process()
            return
        
        # 获取照片路径
        photo_paths = self.camera_handler.get_photo_paths()
        if photo_paths:
            self.photo_path = photo_paths[0]
            logger.info(f"照片已保存: {self.photo_path}")
            
            # 转换为base64
            self._convert_photo_to_base64()
            
            # 第一步完成
            self.step_completed.emit(1)
            self.photo_captured.emit(self.photo_path)
            
            # 自动进入第二步
            self._start_step2_subject()
        else:
            self.error_occurred.emit("未找到拍摄的照片")
            self._reset_process()
    
    def _convert_photo_to_base64(self):
        """将照片转换为base64"""
        try:
            if self.photo_path and os.path.exists(self.photo_path):
                logger.info(f"开始转换照片为base64: {self.photo_path}")
                
                # 检查文件大小
                file_size = os.path.getsize(self.photo_path)
                logger.info(f"照片文件大小: {file_size} bytes")
                
                if file_size == 0:
                    logger.error("照片文件大小为0，可能损坏")
                    self.photo_base64 = ""
                    return
                
                with open(self.photo_path, 'rb') as f:
                    photo_data = f.read()
                    self.photo_base64 = base64.b64encode(photo_data).decode('utf-8')
                
                # 验证base64编码
                if self.photo_base64:
                    logger.info(f"✅ 照片已转换为base64格式 (长度: {len(self.photo_base64)})")
                else:
                    logger.error("❌ base64编码为空")
            else:
                logger.error(f"❌ 照片文件不存在: {self.photo_path}")
                self.photo_base64 = ""
        except Exception as e:
            logger.error(f"❌ 转换照片为base64失败: {e}")
            self.photo_base64 = ""
    
    def _start_step2_subject(self):
        """开始第二步：科目识别"""
        logger.info("进入第二步：科目识别")
        self.current_step = 2
        logger.info("请确认科目")
        self.waiting_for_mqtt = True
    
    def _start_subject_recognition(self):
        """开始科目识别"""
        try:
            logger.info("开始科目识别...")
            self.waiting_for_mqtt = False
            self.subject_recognition_started.emit()
            
            # 创建科目识别线程
            self.subject_thread = SubjectRecognitionThread()
            self.subject_thread.recognition_completed.connect(self._on_subject_recognition_completed)
            self.subject_thread.recognition_failed.connect(self._on_subject_recognition_failed)
            self.subject_thread.start()
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-1-3")
                logger.info("已发送科目识别成功消息: 2-1-3")
            
            
        except Exception as e:
            logger.error(f"启动科目识别失败: {e}")
            self.error_occurred.emit(f"启动科目识别失败: {e}")
            self._reset_process()
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别失败消息: 2-2-0")
            
    
    def _on_subject_recognition_completed(self, subject: str):
        """科目识别完成"""
        logger.info(f"科目识别完成: {subject}")
        if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别结束消息: 2-2-0")
        

        
        self.subject = subject
        self.subject_recognition_completed.emit(subject)
        
        # 第二步完成
        self.step_completed.emit(2)
        
        # 自动进入第三步
        self._start_step3_difficulty()
    
    def _on_subject_recognition_failed(self, error_msg: str):
        """科目识别失败"""
        logger.error(f"科目识别失败: {error_msg}")
        self.error_occurred.emit(f"科目识别失败: {error_msg}")
        if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别结束消息: 2-2-0")
        # 允许重试，不重置流程
        self.waiting_for_mqtt = True
    
    def _start_step3_difficulty(self):
        """开始第三步：困惑点识别"""
        logger.info("进入第三步：困惑点识别")
        self.current_step = 3
        logger.info("请确认困惑点")
        self.waiting_for_mqtt = True
    
    def _start_difficulty_recognition(self):
        """开始困惑点识别"""
        try:
            logger.info("开始困惑点识别...")
            self.waiting_for_mqtt = False
            self.difficulty_recognition_started.emit()
            
            # 创建困惑点识别线程
            self.difficulty_thread = DifficultyRecognitionThread()
            self.difficulty_thread.recognition_completed.connect(self._on_difficulty_recognition_completed)
            self.difficulty_thread.recognition_failed.connect(self._on_difficulty_recognition_failed)
            self.difficulty_thread.start()
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-1-3")
                logger.info("已发送科目识别成功消息: 2-1-3")
        
            
        except Exception as e:
            logger.error(f"启动困惑点识别失败: {e}")
            self.error_occurred.emit(f"启动困惑点识别失败: {e}")
            self._reset_process()
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别成功消息: 2-2-0")
    
    def _on_difficulty_recognition_completed(self, difficulty: str):
        """困惑点识别完成"""
        logger.info(f"困惑点识别完成: {difficulty}")
        if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别成功消息: 2-2-0")
        
        self.difficulty = difficulty
        self.difficulty_recognition_completed.emit(difficulty)
        
        # 第三步完成
        self.step_completed.emit(3)
        
        # 自动进入第四步
        self._start_step4_upload()
    
    def _on_difficulty_recognition_failed(self, error_msg: str):
        """困惑点识别失败"""
        logger.error(f"困惑点识别失败: {error_msg}")
        self.error_occurred.emit(f"困惑点识别失败: {error_msg}")
        if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("2-2-0")
                logger.info("已发送科目识别失败消息: 2-2-0")
        # 允许重试，不重置流程
        self.waiting_for_mqtt = True
    
    def _start_step4_upload(self):
        """开始第四步：数据上传"""
        logger.info("进入第四步：数据上传")
        self.current_step = 4
        logger.info("确认上传")
        self.waiting_for_mqtt = True
    
    def _start_upload(self):
        """开始上传数据"""
        try:
            logger.info("开始上传数据到服务器...")
            self.waiting_for_mqtt = False
            self.upload_started.emit()
            
            # 检查并确保照片数据存在
            if not self.photo_base64 and self.photo_path:
                logger.warning("⚠️ 照片base64数据为空，尝试重新转换...")
                self._convert_photo_to_base64()
            
            # 验证关键数据
            logger.info("📋 验证上传数据...")
            logger.info(f"   📸 照片路径: {self.photo_path}")
            logger.info(f"   📸 照片base64长度: {len(self.photo_base64) if self.photo_base64 else 0}")
            logger.info(f"   📚 科目: {self.subject}")
            logger.info(f"   🤔 困惑点: {self.difficulty}")
            
            # 🔧 关键修复：从user_memory模块获取用户信息
            try:
                # 导入user_memory模块
                import sys
                import os
                switchrole_path = os.path.join(os.path.dirname(__file__), 'switchrole')
                if switchrole_path not in sys.path:
                    sys.path.append(switchrole_path)
                
                from user_memory import get_user_memory
                user_memory = get_user_memory()
                
                # 获取用户信息
                user_info = user_memory.memory_data.get("user_info", {})
                student_name = user_info.get("name", "")
                user_grade = user_info.get("grade", "")
                
                # 构造年级性别信息
                if user_grade:
                    gender_grade = user_grade  # 例如 "3年级"
                else:
                    gender_grade = "未知"
                
                # 如果姓名为空，使用默认值
                if not student_name:
                    student_name = "默认用户"
                
                logger.info(f"✅ 从用户记忆读取信息: 姓名='{student_name}', 年级='{user_grade}'")
                
            except Exception as user_info_error:
                logger.warning(f"⚠️ 读取用户信息失败，使用默认值: {user_info_error}")
                student_name = "默认用户"
                gender_grade = "未知"
            
            # 准备上传数据
            upload_data = {
                "student_name": student_name,
                "gender": gender_grade, 
                "des": self.subject or "未知科目",  # 科目
                "details": self.difficulty or "未明确困惑点",  # 困惑点
                "picture": self.photo_base64 or ""  # 照片
            }
            
            # 最终检查
            if not upload_data["picture"]:
                logger.warning("⚠️ 警告：即将上传的数据中没有照片！")
            else:
                logger.info(f"✅ 准备上传包含照片的数据 (base64长度: {len(upload_data['picture'])})")
            
            # 上传到服务器
            QTimer.singleShot(100, lambda: self._upload_to_server(upload_data))
            
        except Exception as e:
            logger.error(f"准备上传数据失败: {e}")
            self.error_occurred.emit(f"准备上传数据失败: {e}")
            self._reset_process()
    
    def _upload_to_server(self, data: dict):
        """上传数据到服务器"""
        try:
            # API服务器地址
            api_url = "http://poem.e5.luyouxia.net:21387/api/student/submit_json"
            
            logger.info(f"正在上传数据到服务器: {api_url}")
            logger.info(f"📊 上传数据详情:")
            logger.info(f"   👤 学生姓名: {data['student_name']}")
            logger.info(f"   🎓 年级性别: {data['gender']}")
            logger.info(f"   📚 科目: {data['des']}")
            logger.info(f"   🤔 困惑点: {data['details']}")
            
            # 重点检查图片数据
            picture_data = data.get('picture', '')
            if picture_data:
                logger.info(f"   📸 图片数据: ✅ 已包含 (base64长度: {len(picture_data)})")
            else:
                logger.warning(f"   📸 图片数据: ❌ 未包含或为空")
            
            response = requests.post(
                api_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            result = response.json()
            logger.info(f"服务器响应: {result}")
            
            if result.get('success'):
                logger.info("✅ 数据上传成功！")
                self.upload_completed.emit(result)
                
                # 第四步完成
                self.step_completed.emit(4)
                
                # 完成整个流程
                self._complete_process(result)
            else:
                error_msg = f"❌ 数据上传失败: {result.get('message', '未知错误')}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ 网络请求失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"❌ 上传过程出错: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _complete_process(self, upload_result: dict):
        """完成整个流程"""
        logger.info("🎉 作业问答流程全部完成！")
        
        # 准备完成结果
        complete_result = {
            'photo_path': self.photo_path,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'upload_result': upload_result,
            'success': True
        }
        
        # 重置流程状态，但保持处理状态以便接收6-0-3指令
        self.current_step = 0  # 设置为0，等待6-0-3返回功能选择
        self.waiting_for_mqtt = True
        
        # 发射完成信号
        self.process_completed.emit(complete_result)
        
        logger.info("等待返回指令回到功能选择")
    
    def _on_camera_error(self, error_msg: str):
        """摄像头错误处理"""
        logger.error(f"摄像头错误: {error_msg}")
        self.error_occurred.emit(f"摄像头错误: {error_msg}")
        self._reset_process()
    
    def _reset_process(self):
        """重置流程状态"""
        logger.info("重置作业问答流程状态")
        
        self.current_step = 0
        self.is_processing = False
        self.waiting_for_mqtt = False
        
        # 停止所有线程
        if self.subject_thread and self.subject_thread.isRunning():
            self.subject_thread.stop_recognition()
            self.subject_thread.quit()
            self.subject_thread.wait()
            self.subject_thread = None
        
        if self.difficulty_thread and self.difficulty_thread.isRunning():
            self.difficulty_thread.stop_recognition()
            self.difficulty_thread.quit()
            self.difficulty_thread.wait()
            self.difficulty_thread = None
        
        # 清除数据
        self.photo_path = None
        self.subject = None
        self.difficulty = None
        self.photo_base64 = None
    
    def get_camera(self):
        """获取摄像头对象"""
        return self.camera_handler.get_photo_camera() if self.camera_handler else None
    
    def stop(self):
        """停止处理器"""
        try:
            self._reset_process()
            
            if self.camera_handler:
                self.camera_handler.close_cameras()
                self.camera_handler = None
            
            if self.mqtt_handler:
                self.mqtt_handler.stop()
                self.mqtt_handler = None
            
            logger.info("作业问答处理器已停止")
            
        except Exception as e:
            logger.error(f"停止处理器失败: {e}")
    
    def __del__(self):
        """析构函数"""
        self.stop() 