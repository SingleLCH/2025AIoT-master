# -*- coding: utf-8 -*-
"""
智能学习助手主应用程序
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtGui import QFont
import os

# 导入模块
from config import WINDOW_CONFIG, FEATURES, CONTROL_COMMANDS
from mqtt_handler import MQTTHandler
from video_handler import VideoHandler
from ui_components import NotificationWidget
from modern_ui import ModernMainWindow
from photo_homework_handler import PhotoHomeworkHandler
from thinking_guidance_handler import ThinkingGuidanceHandler
from result_display import ResultDisplayWidget
from result2_display import ResultDisplayWidgetnew as ThinkingResultDisplayWidget
from photo_homework_page import PhotoHomeworkPage
from answer_photo_page import AnswerPhotoPage
from settings_page import SettingsPage
from meeting_page import MeetingPage
from batch_homework_handler import BatchHomeworkHandler
from batch_homework_page import BatchHomeworkPage
from batch_homework_result_page import BatchHomeworkResultPage
from book_management_handler import BookManagementHandler
from book_management_page import BookManagementPage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


os.environ['QT_XCB_GL_INTEGRATION'] = 'none'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'



class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.current_environment = None  # 当前环境（学校/家庭）
        self.photo_homework_handler = None  # 拍照搜题处理器
        self.photo_homework_page = None  # 拍照搜题三级页面
        self.thinking_guidance_handler = None  # 思路解答处理器
        self.thinking_guidance_page = None  # 思路解答页面
        self.answer_photo_page = None  # 作业问答页面
        self.result_display = None  # 结果显示界面
        self.settings_page = None  # 设置页面
        self.gesture_word_page = None  # 指尖单词页面
        self.notification_page = None  # 通知页面
        self.meeting_page = None  # 会议页面
        self.batch_homework_handler = None  # 批量批改处理器
        self.book_management_handler = None  # 图书管理处理器
        self.batch_homework_page = None  # 批量批改页面
        self.batch_homework_result_page = None  # 批量批改结果页面
        self.book_management_page = None  # 图书管理页面
        self.pending_video_room = None  # 待确认的视频房间号
        
        # 🆕 添加坐姿检测线程
        self.posture_detection_thread = None
        self.posture_monitoring_enabled = False  # 是否启用坐姿监控
        
        self.setup_ui()
        self.setup_handlers()
        self.setup_connections()
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle(WINDOW_CONFIG['title'])
        self.setFixedSize(WINDOW_CONFIG['width'], WINDOW_CONFIG['height'])
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建堆栈布局管理器
        self.stacked_widget = QStackedWidget()
        
        # 创建现代化选择界面
        self.modern_ui = ModernMainWindow()
        self.modern_ui.mode_selected.connect(self.on_environment_selected)
        self.modern_ui.function_selected.connect(self.handle_function_selection)
        self.modern_ui.back_to_mode_selection.connect(self.on_back_to_mode_selection)
        self.modern_ui.notification_requested.connect(self.show_notification)  # 连接通知信号
        
        # 添加到堆栈
        self.stacked_widget.addWidget(self.modern_ui)
        
        # 设置主布局
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        central_widget.setLayout(layout)
        
        # 创建通知组件（确保只创建一个）
        self.notification_widget = NotificationWidget(self)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #3B4252;
            }
            QWidget {
                background-color: #3B4252;
            }
        """)
        
        logger.info("主界面初始化完成")
        
    def setup_handlers(self):
        """设置处理器"""
        # 创建MQTT处理器
        self.mqtt_handler = MQTTHandler()

        # 创建视频处理器
        self.video_handler = VideoHandler(self.mqtt_handler)

        # 拍照搜题处理器将在需要时延迟初始化
        self.photo_homework_handler = None
        
        # 语音助手服务将在需要时延迟初始化
        self.voice_assistant_service = None
        
        # 注册功能回调（即使语音助手还未初始化，也要确保回调函数已准备好）
        self._register_function_callbacks()

        logger.info("处理器初始化完成")

    def _init_photo_homework_handler(self):
        """延迟初始化拍照搜题处理器"""
        if self.photo_homework_handler is None:
            try:
                logger.info("开始初始化拍照搜题处理器...")
                self.photo_homework_handler = PhotoHomeworkHandler()

                # 连接信号
                self.photo_homework_handler.process_started.connect(self.on_photo_process_started)
                self.photo_homework_handler.face_recognition_completed.connect(self.on_face_recognition_completed)
                self.photo_homework_handler.face_recognition_failed.connect(self.on_face_recognition_failed)
                self.photo_homework_handler.photo_capture_completed.connect(self.on_photo_capture_completed)
                self.photo_homework_handler.upload_started.connect(self.on_upload_started)
                self.photo_homework_handler.upload_completed.connect(self.on_upload_completed)
                self.photo_homework_handler.database_saved.connect(self.on_database_saved)
                self.photo_homework_handler.process_completed.connect(self.on_photo_process_completed)
                self.photo_homework_handler.back_requested.connect(self.on_photo_page_back)
                self.photo_homework_handler.error_occurred.connect(self.on_photo_error_occurred)

                logger.info("拍照搜题处理器初始化成功")
                return True
            except Exception as e:
                logger.error(f"拍照搜题处理器初始化失败: {e}")
                self.photo_homework_handler = None
                return False
        return True
    
    def _init_thinking_guidance_handler(self):
        """延迟初始化思路解答处理器"""
        if self.thinking_guidance_handler is None:
            try:
                logger.info("开始初始化思路解答处理器...")
                self.thinking_guidance_handler = ThinkingGuidanceHandler()

                # 设置相关处理器
                if self.photo_homework_handler:
                    # 复用拍照搜题的摄像头和MQTT处理器
                    self.thinking_guidance_handler.set_camera_handler(self.photo_homework_handler.camera_handler)
                    self.thinking_guidance_handler.set_mqtt_handler(self.mqtt_handler)
                    self.thinking_guidance_handler.set_database_handler(self.photo_homework_handler.database_handler)

                # 连接信号
                self.thinking_guidance_handler.process_started.connect(self.on_thinking_guidance_process_started)
                self.thinking_guidance_handler.face_recognition_completed.connect(self.on_thinking_guidance_face_recognition_completed)
                self.thinking_guidance_handler.face_recognition_failed.connect(self.on_thinking_guidance_face_recognition_failed)
                self.thinking_guidance_handler.photo_capture_completed.connect(self.on_thinking_guidance_photo_capture_completed)
                self.thinking_guidance_handler.upload_started.connect(self.on_thinking_guidance_upload_started)
                self.thinking_guidance_handler.upload_completed.connect(self.on_thinking_guidance_upload_completed)
                self.thinking_guidance_handler.database_saved.connect(self.on_thinking_guidance_database_saved)
                self.thinking_guidance_handler.process_completed.connect(self.on_thinking_guidance_process_completed)
                self.thinking_guidance_handler.back_requested.connect(self.on_thinking_guidance_back)
                self.thinking_guidance_handler.error_occurred.connect(self.on_thinking_guidance_error_occurred)

                logger.info("思路解答处理器初始化成功")
                return True
            except Exception as e:
                logger.error(f"思路解答处理器初始化失败: {e}")
                self.thinking_guidance_handler = None
                return False
        return True
    
    def _init_voice_assistant_service(self):
        """延迟初始化语音助手服务"""
        if self.voice_assistant_service is None:
            try:
                logger.info("开始初始化语音助手服务...")
                from voice_assistant_service import VoiceAssistantService
                
                self.voice_assistant_service = VoiceAssistantService(environment=self.current_environment)
                
                # 连接信号
                self.voice_assistant_service.assistant_ready.connect(self.on_voice_assistant_ready)
                self.voice_assistant_service.wake_detected.connect(self.on_voice_wake_detected)
                self.voice_assistant_service.user_speaking.connect(self.on_voice_user_speaking)
                self.voice_assistant_service.assistant_responding.connect(self.on_voice_assistant_responding)
                self.voice_assistant_service.error_occurred.connect(self.on_voice_assistant_error)

                # 🔧 注册功能回调
                self._register_function_callbacks()

                logger.info("语音助手服务初始化成功")
                return True
            except Exception as e:
                logger.error(f"语音助手服务初始化失败: {e}")
                self.voice_assistant_service = None
                return False
        return True

    def _register_function_callbacks(self):
        """注册功能回调"""
        try:
            import sys
            import os

            # 确保switchrole目录在Python路径中
            switchrole_path = os.path.join(os.path.dirname(__file__), 'switchrole')
            if switchrole_path not in sys.path:
                sys.path.insert(0, switchrole_path)

            from switchrole.function_handlers import get_function_handlers
            from switchrole.function_manager import get_function_manager

            # 获取功能处理器和管理器
            handlers = get_function_handlers()
            manager = get_function_manager()

            # 注册各功能的回调 - 直接调用主界面的方法
            # 🔧 修复：正确映射功能ID到对应方法
            logger.info("🔧 开始注册功能回调...")
            
            handlers.set_ui_callback("homework_correction", self.handle_homework_correction)  # 作业批改
            logger.info("✅ 已注册作业批改回调")
            
            handlers.set_ui_callback("homework_qa", self.handle_homework_qa)                  # 作业问答
            logger.info("✅ 已注册作业问答回调")
            
            handlers.set_ui_callback("music_player", self.handle_music_player)
            logger.info("✅ 已注册音乐播放回调")
            
            handlers.set_ui_callback("ai_chat", self.handle_ai_chat)
            logger.info("✅ 已注册AI对话回调")
            
            handlers.set_ui_callback("system_settings", self._voice_handle_settings)
            logger.info("✅ 已注册系统设置回调")
            
            handlers.set_ui_callback("voice_assistant", self._voice_handle_voice_assistant)
            logger.info("✅ 已注册语音助手回调")
            
            handlers.set_ui_callback("video_meetings", self._voice_handle_video_meetings)
            logger.info("✅ 已注册视频连接回调")
            
            handlers.set_ui_callback("notifications", self._voice_handle_notifications)
            logger.info("✅ 已注册通知功能回调")

            logger.info("✅ 所有功能回调注册成功")
        except Exception as e:
            logger.error(f"❌ 功能回调注册失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _handle_voice_function_command(self, action: str):
        """处理语音功能切换指令"""
        logger.info(f"🎯 处理语音功能切换指令: {action}")

        try:
            # 映射语音指令到功能方法
            function_mapping = {
                'voice_homework_correction': self.handle_homework_correction,  # 作业批改
                'voice_homework_qa': self.handle_homework_qa,                  # 作业问答
                'voice_music_player': self.handle_music_player,
                'voice_ai_chat': self.handle_ai_chat,
                'voice_settings': self.handle_settings,
                'voice_video_meetings': self.handle_video_meetings,
                'voice_notifications': self.handle_notifications,
                'voice_assistant': self.handle_voice_assistant
            }

            if action in function_mapping:
                function_method = function_mapping[action]
                result = function_method()

                if result:
                    logger.info(f"✅ 语音功能切换成功: {action}")
                    self.show_notification("语音助手", f"已切换到{action.replace('voice_', '')}功能")
                else:
                    logger.error(f"❌ 语音功能切换失败: {action}")
                    self.show_notification("语音助手", f"切换到{action.replace('voice_', '')}功能失败")
            else:
                logger.warning(f"⚠️ 未知的语音功能指令: {action}")

        except Exception as e:
            logger.error(f"❌ 处理语音功能切换指令异常: {e}")

    def handle_music_player(self, **kwargs):
        """处理音乐播放器功能"""
        logger.info("🎵 语音命令：打开音乐播放器")
        # 这里可以添加特定的音乐播放器界面逻辑
        # 目前直接返回True，表示功能已处理
        return True

    def handle_ai_chat(self, **kwargs):
        """处理AI对话功能"""
        logger.info("🤖 语音命令：打开AI对话")
        # AI对话功能已经是默认模式，直接返回True
        return True

    def _voice_handle_homework_qa(self, **kwargs):
        """语音命令：打开拍照搜题功能"""
        logger.info("📸 语音命令：打开拍照搜题")
        try:
            # 调用实际的拍照搜题功能
            self.handle_homework_qa()
            return True
        except Exception as e:
            logger.error(f"打开拍照搜题失败: {e}")
            return False

    def _voice_handle_homework_correction(self, **kwargs):
        """语音命令：打开作业批改功能"""
        logger.info("📝 语音命令：打开作业批改")
        try:
            # 调用实际的作业批改功能
            self.handle_homework_correction()
            return True
        except Exception as e:
            logger.error(f"打开作业批改失败: {e}")
            return False

    def _voice_handle_settings(self, **kwargs):
        """语音命令：打开系统设置功能"""
        logger.info("⚙️ 语音命令：打开系统设置")
        try:
            # 调用实际的设置功能
            self.handle_settings()
            return True
        except Exception as e:
            logger.error(f"打开系统设置失败: {e}")
            return False

    def _voice_handle_voice_assistant(self, **kwargs):
        """语音命令：打开语音助手功能"""
        logger.info("🎤 语音命令：打开语音助手")
        try:
            # 调用实际的语音助手功能
            self.handle_voice_assistant()
            return True
        except Exception as e:
            logger.error(f"打开语音助手失败: {e}")
            return False

    def _voice_handle_video_meetings(self, **kwargs):
        """语音命令：打开视频连接功能"""
        logger.info("📹 语音命令：打开视频连接")
        try:
            # 调用实际的视频连接功能
            self.handle_video_meetings()
            return True
        except Exception as e:
            logger.error(f"打开视频连接失败: {e}")
            return False

    def _voice_handle_notifications(self, **kwargs):
        """语音命令：打开通知功能"""
        logger.info("🔔 语音命令：打开通知功能")
        try:
            # 调用实际的通知功能
            self.handle_notifications()
            return True
        except Exception as e:
            logger.error(f"打开通知功能失败: {e}")
            return False

    def setup_connections(self):
        """设置信号连接"""
        # MQTT信号连接
        self.mqtt_handler.control_command_received.connect(self.handle_control_command)
        self.mqtt_handler.notification_received.connect(self.handle_notification)
        self.mqtt_handler.room_invitation_received.connect(self.handle_room_invitation)
        self.mqtt_handler.room_close_received.connect(self.handle_room_close)
        
        # 拍照搜题信号连接将在处理器初始化后进行
        
        # 启动MQTT处理器
        self.mqtt_handler.start()
        
        logger.info("信号连接设置完成")
    
    @pyqtSlot(str)
    def on_environment_selected(self, environment):
        """环境选择完成"""
        self.current_environment = environment
        logger.info(f"选择环境: {FEATURES[environment]['name']}")
        
        # 如果语音助手服务已存在，更新环境
        if hasattr(self, 'voice_assistant_service') and self.voice_assistant_service:
            self.voice_assistant_service.set_environment(environment)
        
        # 🆕 在家庭模式下启动坐姿检测
        if environment == 'home':
            self._start_posture_detection()
        else:
            # 在学校模式下确保坐姿检测已停止
            self._stop_posture_detection()
    
    def on_back_to_mode_selection(self):
        """返回模式选择时的处理"""
        logger.info("返回模式选择界面")
        self.current_environment = None
        
    @pyqtSlot(str)
    def handle_control_command(self, command):
        """处理控制指令（统一从gesture主题接收）"""
        logger.info(f"接收到控制指令: {command}")

        # 处理视频会议确认
        if command == "6-0-1" and self.pending_video_room:
            # 🔧 修复：确认加入视频会议，创建会议页面
            logger.info(f"确认加入视频会议: {self.pending_video_room}")
            self._start_meeting(self.pending_video_room)
            self.pending_video_room = None  # 清除待确认状态
            return
            
                # 🔧 修复：处理退出会议或取消会议邀请
        if command == "6-0-2":
            # 检查是否有待确认的会议
            if self.pending_video_room:
                logger.info("取消待确认的会议邀请")
                self.pending_video_room = None
                self.show_notification("视频会议", "已取消会议邀请")
                return
            
            # 检查是否在会议页面中
            current_widget = self.stacked_widget.currentWidget()
            if isinstance(current_widget, MeetingPage):
                logger.info("用户手势退出会议")
                self._exit_meeting()
                return
            
            # 检查是否有正在进行的会议（通过video_handler）
            if self.video_handler.get_current_room_id():
                logger.info("检测到正在进行的会议，执行退出")
                self._exit_meeting()
                return
            
            # 🔧 修复：如果不是会议相关场景，继续执行后面的逻辑，让其他页面处理6-0-2指令
            # 不要在这里return，让指令继续传递给其他页面

        # 🔧 修复：优先处理语音功能切换指令，无论当前界面是什么
        if command.startswith('voice_'):
            self._handle_voice_function_command(command)
            return
            
        # 如果设置页面正在显示，检查是否为特殊手势指令
        if (self.settings_page and 
            self.stacked_widget.currentWidget() == self.settings_page):
            
            # 检查是否为特殊手势指令（6-0-X, 6-1-X）
            if self.is_special_gesture_command(command):
                logger.info(f"设置页面处理特殊手势指令: {command}")
                self.settings_page.handle_gesture_command(command)
                return
            
            # 其他指令按普通控制指令处理
            logger.info(f"设置页面处理普通控制指令: {command}")
        
        # 尝试解析为标准控制指令
        if command in CONTROL_COMMANDS:
            action = CONTROL_COMMANDS[command]
            logger.info(f"解析控制指令: {command} -> {action}")
            
            # 🔧 修复：优先处理语音功能切换指令，无论当前界面是什么
            if action.startswith('voice_'):
                logger.info(f"🎯 检测到语音功能切换指令: {action}")
                self._handle_voice_function_command(action)
                return
            
            # 🔧 修复：优先检查当前显示的界面类型，确保指令路由优先级正确
            current_widget = self.stacked_widget.currentWidget()
            logger.info(f"当前页面类型: {type(current_widget).__name__}")
            
            # 🎯 最高优先级：主界面（模式选择/功能选择）处理
            if isinstance(current_widget, ModernMainWindow):
                logger.info(f"主界面处理控制指令: {action}")
                current_widget.handle_control_command(action)
                return
            
            # 如果当前显示的是结果页面，优先处理
            if isinstance(current_widget, ResultDisplayWidget):
                logger.info(f"结果页面处理MQTT控制指令: {action}")
                current_widget.handle_control_command(action)
                return
            
            # 如果当前显示的是思路解答结果页面，优先处理
            if isinstance(current_widget, ThinkingResultDisplayWidget):
                logger.info(f"思路解答结果页面处理MQTT控制指令: {action}")
                current_widget.handle_control_command(action)
                return
            
            # 检查是否在图书管理页面，如果是则优先处理
            logger.info(f"图书管理页面是否存在: {self.book_management_page is not None}")
            if (self.book_management_page and current_widget == self.book_management_page):
                logger.info(f"当前在图书管理页面，转发指令: {command}")
                if self.book_management_handler:
                    self.book_management_handler.handle_mqtt_command(command)
                    return
            elif self.book_management_page and isinstance(current_widget, BookManagementPage):
                logger.info(f"通过类型检查确认在图书管理页面，转发指令: {command}")
                if self.book_management_handler:
                    self.book_management_handler.handle_mqtt_command(command)
                    return
            
            # 如果批量批改结果页面正在显示，转发指令给它处理
            if (self.batch_homework_result_page and 
                isinstance(current_widget, BatchHomeworkResultPage)):
                logger.info(f"批量批改结果页面处理控制指令: {command}")
                self.batch_homework_result_page.handle_control_command(command)
                return
            
            # 如果拍照搜题处理器正在运行，转发指令给它处理
            if (self.photo_homework_handler and 
                hasattr(self.photo_homework_handler, 'is_processing') and 
                self.photo_homework_handler.is_processing):
                logger.info(f"拍照搜题流程正在运行，直接转发控制指令: {action}")
                # 直接调用拍照搜题处理器的MQTT指令处理方法
                self.photo_homework_handler._on_mqtt_command(action)
                return
            
            # 如果思路解答处理器正在运行，转发指令给它处理
            if (self.thinking_guidance_handler and 
                hasattr(self.thinking_guidance_handler, 'is_processing') and 
                self.thinking_guidance_handler.is_processing):
                logger.info(f"思路解答流程正在运行，直接转发控制指令: {action}")
                # 直接调用思路解答处理器的MQTT指令处理方法
                self.thinking_guidance_handler._on_mqtt_command(action)
                return
            
            # 如果批量批改处理器正在运行，转发指令给它处理
            if (self.batch_homework_handler and 
                hasattr(self.batch_homework_handler, 'is_processing') and 
                self.batch_homework_handler.is_processing):
                logger.info(f"批量批改流程正在运行，直接转发控制指令: {command}")
                # 直接调用批量批改处理器的MQTT指令处理方法
                self.batch_homework_handler.handle_mqtt_command(command)
                return
            
            # 如果图书管理处理器存在且在处理中，检查是否需要处理指令
            if (self.book_management_handler and 
                hasattr(self.book_management_handler, 'is_processing') and 
                self.book_management_handler.is_processing):
                logger.info(f"图书管理流程正在运行，转发指令给图书管理处理器: {command}")
                self.book_management_handler.handle_mqtt_command(command)
                return

            
            # 根据当前界面分发指令（其他页面）
            if hasattr(self, 'voice_assistant_page') and current_widget == self.voice_assistant_page:
                # 语音助手界面处理
                self.voice_assistant_page.handle_control_command(action)
            elif hasattr(self, 'notification_page') and current_widget == self.notification_page:
                # 通知页面处理
                self.notification_page.handle_control_command(command)
            elif isinstance(current_widget, MeetingPage):
                # 🔧 新增：会议页面处理
                current_widget.handle_control_command(action)
            elif hasattr(current_widget, 'handle_control_command'):
                # 其他支持MQTT控制的界面
                current_widget.handle_control_command(action)
        else:
            # 检查是否为设置指令格式
            if self.is_settings_command(command):
                logger.info(f"接收到设置指令: {command}")
                # 如果设置页面正在显示，转发给设置页面处理
                if (self.settings_page and 
                    self.stacked_widget.currentWidget() == self.settings_page):
                    self.settings_page.handle_mqtt_command(command)
                else:
                    logger.warning(f"设置页面未显示，忽略设置指令: {command}")
            else:
                logger.info(f"未识别的控制指令: {command}")
    
    def is_special_gesture_command(self, command):
        """检查是否为特殊手势指令（6-0-X, 6-1-X）"""
        try:
            parts = command.split('-')
            if len(parts) != 3:
                return False
            
            category = int(parts[0])
            # 检查是否为手势指令（6-0-X 或 6-1-X）
            return category == 6
        except ValueError:
            return False
    
    def is_settings_command(self, command):
        """检查是否为设置指令"""
        try:
            parts = command.split('-')
            if len(parts) != 3:
                return False
            
            category = int(parts[0])
            # 检查是否为设置相关指令（音量：4，亮度：7，桌子：3）
            return category in [3, 4, 7]
        except ValueError:
            return False
    
    @pyqtSlot(str, dict)
    def handle_notification(self, topic, data):
        """处理通知消息"""
        logger.info(f"处理通知 - 主题: {topic}, 数据: {data}")

        # 将通知数据传递给通知页面
        if hasattr(self, 'notification_page') and self.notification_page:
            self.notification_page.add_notification(data)

        if topic == 'nf':
            # 处理普通通知
            message = data.get('message', '无消息内容')
            logger.info(f"收到通知: {message}")
            # 显示通知窗口
            self.show_notification("系统通知", message)

        elif topic == 'room':
            # 处理房间邀请通知
            logger.info("收到视频邀请")
            # 显示视频邀请通知
            room_id = data.get('room_id', '未知房间')
            from_teacher = data.get('from', '老师')
            self.show_notification("视频邀请", f"收到来自{from_teacher}的视频邀请\n房间号: {room_id}")
    
    @pyqtSlot(str)
    def handle_room_invitation(self, room_id):
        """处理房间邀请"""
        logger.info(f"处理房间邀请: {room_id}")
        # 🔧 修复：不直接进入会议，设置为待确认状态
        self.pending_video_room = room_id
        logger.info(f"房间邀请已设为待确认状态: {room_id}")
        # 显示确认提示
        self.show_notification("视频邀请确认", f"收到会议邀请，房间号: {room_id}\n使用手势6-0-1确认加入会议")
    
    @pyqtSlot()
    def handle_room_close(self):
        """处理房间关闭"""
        logger.info("处理房间关闭")
        self.video_handler.close_current_room()
    
    @pyqtSlot(str)
    def handle_function_selection(self, function_key):
        """处理功能选择"""
        logger.info(f"选择功能: {function_key}")
        
        # 这里可以根据功能类型进行不同的处理
        if function_key == 'settings':
            self.handle_settings()
        elif function_key == 'mettings':
            self.handle_video_meetings()
        elif function_key == 'voice':
            self.handle_voice_assistant()
        elif function_key == 'pigai':
            self.handle_homework_correction()
        elif function_key == 'answer':
            self.handle_homework_qa()
        elif function_key == 'note':
            self.handle_notifications()
        elif function_key == 'gesture':
            self.handle_gesture_word()
        elif function_key == 'batch_homework':
            self.handle_batch_homework()
        elif function_key == 'book_management':
            self.handle_book_management()
        elif function_key == 'thinking_guidance':
            self.handle_thinking_guidance()
    
    def handle_settings(self):
        """处理设置功能"""
        logger.info("打开设置页面")
        
        # 创建设置页面（如果不存在）
        if self.settings_page is None:
            self.settings_page = SettingsPage()
            self.settings_page.back_requested.connect(self.on_settings_back)
            self.settings_page.send_esp32_control_command.connect(self.mqtt_handler.send_esp32_control_command)
            self.stacked_widget.addWidget(self.settings_page)
        
        # 切换到设置页面
        self.stacked_widget.setCurrentWidget(self.settings_page)
        
    def handle_video_meetings(self):
        """处理视频连接功能"""
        logger.info("打开视频连接功能")
        
        # 检查是否有当前房间
        current_room_id = self.video_handler.get_current_room_id()
        
        if not current_room_id:
            # 没有房间号，通过通知系统提示用户
            self.show_notification("视频连接", "暂时没有会议，请稍后进入")
            return
        
        # 有会议，通过通知系统提示用户确认
        self.show_notification("视频连接确认", f"检测到会议房间: {current_room_id}\n使用手势6-0-1确认加入会议")
        
        # 设置临时状态，等待用户确认
        self.pending_video_room = current_room_id
        
    def handle_voice_assistant(self):
        """处理语音助手功能"""
        logger.info(f"打开语音助手功能 - 当前环境: {self.current_environment}")
        
        try:
            # 检查是否已经有语音助手服务在运行
            if (hasattr(self, 'voice_assistant_service') and 
                self.voice_assistant_service and 
                self.voice_assistant_service.is_running):
                logger.info("语音助手已在运行中")
                self.show_notification("语音助手", "语音助手已经在运行中")
                
                # 如果已经有页面，直接切换到该页面
                if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
                    self.stacked_widget.setCurrentWidget(self.voice_assistant_page)
                    return
                
                # 如果没有页面但服务在运行，创建页面
                from voice_assistant_page import VoiceAssistantPage
                self.voice_assistant_page = VoiceAssistantPage()
                self.voice_assistant_page.back_requested.connect(self.on_voice_assistant_back)
                self.stacked_widget.addWidget(self.voice_assistant_page)
                self.stacked_widget.setCurrentWidget(self.voice_assistant_page)
                self.voice_assistant_page.update_status("已就绪")
                return
            
            # 创建语音助手页面
            from voice_assistant_page import VoiceAssistantPage
            self.voice_assistant_page = VoiceAssistantPage()
            
            # 连接信号
            self.voice_assistant_page.back_requested.connect(self.on_voice_assistant_back)
            
            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.voice_assistant_page)
            self.stacked_widget.setCurrentWidget(self.voice_assistant_page)
            
            logger.info("已切换到语音助手界面")
            
            # 初始化语音助手服务
            if not hasattr(self, 'voice_assistant_service') or self.voice_assistant_service is None:
                self._init_voice_assistant_service()
            
            # 确保功能回调已注册（重新注册以确保最新状态）
            self._register_function_callbacks()
            
            # 设置环境并启动语音助手
            if self.voice_assistant_service:
                self.voice_assistant_service.set_environment(self.current_environment)
                if self.voice_assistant_service.start():
                    logger.info("✅ 语音助手启动成功，可以通过'你好广和通'唤醒")
                    # 在界面左上角显示已就绪状态
                    self.voice_assistant_page.update_status("已就绪")
                else:
                    logger.error("❌ 语音助手启动失败")
                    self.show_notification("语音助手", "语音助手启动失败，请检查音频设备")
            else:
                logger.error("❌ 语音助手服务初始化失败")
                self.show_notification("语音助手", "语音助手初始化失败")
                
        except Exception as e:
            logger.error(f"打开语音助手功能失败: {e}")
            self.show_notification("语音助手", "语音助手功能启动失败")
        
    def handle_homework_correction(self):
        """处理作业批改功能"""        
        try:
            logger.info(f"🎯 语音触发：打开作业批改功能 - 当前环境: {self.current_environment}")

            # 🆕 暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()

            # 延迟初始化拍照搜题处理器
            if not self._init_photo_homework_handler():
                logger.error("拍照搜题处理器初始化失败，无法进入功能")
                # 🆕 出错时恢复坐姿检测
                self._resume_posture_detection()
                return False

            # 创建拍照搜题三级页面
            self.photo_homework_page = PhotoHomeworkPage()

            # 连接信号
            self.photo_homework_page.back_requested.connect(self.on_photo_page_back)
            self.photo_homework_page.process_started.connect(self.on_photo_page_process_started)

            # 连接拍照搜题处理器的信号
            self.photo_homework_handler.face_recognition_completed.connect(
                self.photo_homework_page.on_face_recognition_completed)
            self.photo_homework_handler.photo_capture_completed.connect(
                self.photo_homework_page.on_photo_captured)
            self.photo_homework_handler.upload_started.connect(
                self.photo_homework_page.on_analysis_started)
            self.photo_homework_handler.upload_completed.connect(
                self.photo_homework_page.on_upload_ready)
            self.photo_homework_handler.process_completed.connect(
                self.photo_homework_page.on_analysis_completed)

            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.photo_homework_page)
            self.stacked_widget.setCurrentWidget(self.photo_homework_page)

            logger.info("已切换到拍照搜题界面")

            # 根据环境启动相应模式
            if self.current_environment == "school":
                logger.info("🏫 学校环境，启动学校模式（含人脸识别）")
                
                # 🔧 作业批改学校模式需要人脸摄像头，确保其正确初始化
                logger.info("作业批改学校模式：强制重新初始化人脸摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("face")
                    if not success:
                        logger.error("人脸摄像头重新初始化失败")
                        self.show_notification("作业批改", "人脸摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 人脸摄像头重新初始化成功")
                
                # 🔧 作业批改学校模式也需要拍照摄像头，确保其正确初始化
                logger.info("作业批改学校模式：强制重新初始化拍照摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                    if not success:
                        logger.error("拍照摄像头重新初始化失败")
                        self.show_notification("作业批改", "拍照摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 拍照摄像头重新初始化成功")
                
                face_camera = self.photo_homework_handler.camera_handler.get_face_camera()
                photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                self.photo_homework_page.start_school_mode(face_camera, photo_camera)
            elif self.current_environment == "home":
                logger.info("🏠 家庭环境，启动家庭模式（直接拍照）")
                
                # 🔧 作业批改家庭模式只需要拍照摄像头，确保其正确初始化
                logger.info("作业批改家庭模式：强制重新初始化拍照摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                    if not success:
                        logger.error("拍照摄像头重新初始化失败")
                        self.show_notification("作业批改", "拍照摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 拍照摄像头重新初始化成功")
                
                photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                
                # 检查摄像头是否正确初始化
                if photo_camera is None:
                    logger.warning("拍照摄像头未正确初始化，尝试重新初始化...")
                    try:
                        # 重新初始化摄像头
                        self.photo_homework_handler.camera_handler.restart_cameras()
                        photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                        
                        if photo_camera is None:
                            logger.error("拍照摄像头重新初始化失败")
                            self.show_notification("拍照搜题", "拍照摄像头初始化失败")
                            return False
                    except Exception as e:
                        logger.error(f"摄像头重新初始化失败: {e}")
                        self.show_notification("拍照搜题", "摄像头初始化失败")
                        return False
                
                self.photo_homework_page.start_home_mode(photo_camera)
                # 启动家庭模式处理流程
                self.photo_homework_handler.start_home_mode_process()
            else:
                logger.error(f"未知环境: {self.current_environment}")
                self.show_notification("拍照搜题", "未知环境，请重新选择")
                return False

            return True

        except Exception as e:
            logger.error(f"打开拍照搜题功能失败: {e}")
            self.show_notification("拍照搜题", "拍照搜题功能启动失败")
            return False

    def handle_thinking_guidance(self):
        """处理思路解答功能"""        
        try:
            logger.info(f"🎯 打开思路解答功能 - 当前环境: {self.current_environment}")

            # 🆕 暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()

            # 延迟初始化拍照搜题处理器（思路解答需要复用摄像头）
            if not self._init_photo_homework_handler():
                logger.error("拍照搜题处理器初始化失败，无法进入思路解答功能")
                # 🆕 出错时恢复坐姿检测
                self._resume_posture_detection()
                return False

            # 延迟初始化思路解答处理器
            if not self._init_thinking_guidance_handler():
                logger.error("思路解答处理器初始化失败，无法进入功能")
                # 🆕 出错时恢复坐姿检测
                self._resume_posture_detection()
                return False

            # 复用拍照搜题页面（思路解答功能）
            self.thinking_guidance_page = PhotoHomeworkPage()

            # 连接信号
            self.thinking_guidance_page.back_requested.connect(self.on_thinking_guidance_back)
            self.thinking_guidance_page.process_started.connect(self.on_thinking_guidance_page_process_started)

            # 连接思路解答处理器的信号到页面
            self.thinking_guidance_handler.face_recognition_completed.connect(
                self.thinking_guidance_page.on_face_recognition_completed)
            self.thinking_guidance_handler.photo_capture_completed.connect(
                self.thinking_guidance_page.on_photo_captured)
            self.thinking_guidance_handler.upload_started.connect(
                self.thinking_guidance_page.on_analysis_started)
            self.thinking_guidance_handler.upload_completed.connect(
                self.thinking_guidance_page.on_upload_ready)
            self.thinking_guidance_handler.process_completed.connect(
                self.thinking_guidance_page.on_analysis_completed)

            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.thinking_guidance_page)
            self.stacked_widget.setCurrentWidget(self.thinking_guidance_page)

            logger.info("已切换到思路解答界面")

            # 根据环境启动相应模式
            if self.current_environment == "school":
                logger.info("🏫 学校环境，启动学校模式（含人脸识别）")
                
                # 🔧 思路解答学校模式需要人脸摄像头，确保其正确初始化
                logger.info("思路解答学校模式：强制重新初始化人脸摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("face")
                    if not success:
                        logger.error("人脸摄像头重新初始化失败")
                        self.show_notification("思路解答", "人脸摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 人脸摄像头重新初始化成功")
                
                # 🔧 思路解答学校模式也需要拍照摄像头，确保其正确初始化
                logger.info("思路解答学校模式：强制重新初始化拍照摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                    if not success:
                        logger.error("拍照摄像头重新初始化失败")
                        self.show_notification("思路解答", "拍照摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 拍照摄像头重新初始化成功")
                
                face_camera = self.photo_homework_handler.camera_handler.get_face_camera()
                photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                self.thinking_guidance_page.start_school_mode(face_camera, photo_camera)
                # 启动学校模式处理流程
                self.thinking_guidance_handler.start_school_mode_process()
                
            elif self.current_environment == "home":
                logger.info("🏠 家庭环境，启动家庭模式（直接拍照）")
                
                # 🔧 思路解答家庭模式只需要拍照摄像头，确保其正确初始化
                logger.info("思路解答家庭模式：强制重新初始化拍照摄像头...")
                if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                    success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                    if not success:
                        logger.error("拍照摄像头重新初始化失败")
                        self.show_notification("思路解答", "拍照摄像头初始化失败")
                        self._resume_posture_detection()
                        return False
                    logger.info("✅ 拍照摄像头重新初始化成功")
                
                photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                
                # 检查摄像头是否正确初始化
                if photo_camera is None:
                    logger.warning("拍照摄像头未正确初始化，尝试重新初始化...")
                    try:
                        # 重新初始化摄像头
                        self.photo_homework_handler.camera_handler.restart_cameras()
                        photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                        
                        if photo_camera is None:
                            logger.error("拍照摄像头重新初始化失败")
                            self.show_notification("思路解答", "拍照摄像头初始化失败")
                            return False
                    except Exception as e:
                        logger.error(f"摄像头重新初始化失败: {e}")
                        self.show_notification("思路解答", "摄像头初始化失败")
                        return False
                
                self.thinking_guidance_page.start_home_mode(photo_camera)
                # 启动家庭模式处理流程
                self.thinking_guidance_handler.start_home_mode_process()
            else:
                logger.error(f"未知环境: {self.current_environment}")
                self.show_notification("思路解答", "未知环境，请重新选择")
                return False

            return True

        except Exception as e:
            logger.error(f"打开思路解答功能失败: {e}")
            self.show_notification("思路解答", "思路解答功能启动失败")
            return False

    def handle_homework_qa(self):
        """处理作业问答功能"""        
        try:
            logger.info("打开作业问答功能")
            
            # 🆕 暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()
            
            # 创建作业问答页面
            from homework_qa_page import HomeworkQAPage
            self.answer_photo_page = HomeworkQAPage()
            
            # 连接信号
            self.answer_photo_page.back_requested.connect(self.on_answer_page_back)
            self.answer_photo_page.process_completed.connect(self.on_answer_upload_completed)
            
            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.answer_photo_page)
            self.stacked_widget.setCurrentWidget(self.answer_photo_page)
            
            logger.info("已切换到作业问答界面")
            
        except Exception as e:
            logger.error(f"打开作业问答功能失败: {e}")
            self.show_notification("作业问答", "作业问答功能启动失败")

    def handle_batch_homework(self):
        """处理批量批改功能"""        
        try:
            logger.info("打开批量批改功能")
            
            # 检查是否为学校模式
            if self.current_environment != "school":
                logger.warning("批量批改功能仅在学校模式下可用")
                self.show_notification("批量批改", "批量批改功能仅在学校模式下可用")
                return False
            
            # 🆕 在学校模式下暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()
            
            # 延迟初始化拍照搜题处理器（复用摄像头）
            if not self._init_photo_homework_handler():
                logger.error("摄像头处理器初始化失败，无法进入批量批改功能")
                # 🆕 出错时恢复坐姿检测
                self._resume_posture_detection()
                return False
            
            # 初始化批量批改处理器
            if self.batch_homework_handler is None:
                self.batch_homework_handler = BatchHomeworkHandler()
                self.batch_homework_handler.set_camera_handler(self.photo_homework_handler.camera_handler)
                
                # 连接信号
                self.batch_homework_handler.process_started.connect(self.on_batch_homework_process_started)
                self.batch_homework_handler.photo_captured.connect(self.on_batch_homework_photo_captured)
                self.batch_homework_handler.analysis_started.connect(self.on_batch_homework_analysis_started)
                self.batch_homework_handler.analysis_progress.connect(self.on_batch_homework_analysis_progress)
                self.batch_homework_handler.upload_completed.connect(self.on_batch_homework_upload_completed)
                self.batch_homework_handler.error_occurred.connect(self.on_batch_homework_error)
                self.batch_homework_handler.back_requested.connect(self.on_batch_homework_back)
                logger.info("批量批改处理器初始化完成")
            
            # 创建批量批改页面
            if self.batch_homework_page is None:
                self.batch_homework_page = BatchHomeworkPage()
                self.batch_homework_page.back_requested.connect(self.on_batch_homework_back)
                self.stacked_widget.addWidget(self.batch_homework_page)
                logger.info("批量批改页面创建完成")
            
            # 切换到批量批改页面
            self.stacked_widget.setCurrentWidget(self.batch_homework_page)
            
            # 🔧 批量批改功能只需要拍照摄像头，确保其正确初始化
            logger.info("批量批改功能：强制重新初始化拍照摄像头...")
            if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                if not success:
                    logger.error("拍照摄像头重新初始化失败")
                    self.show_notification("批量批改", "拍照摄像头初始化失败")
                    self._resume_posture_detection()
                    return False
                logger.info("✅ 拍照摄像头重新初始化成功")
            
            # 启动批量批改模式
            self.batch_homework_page.start_batch_homework_mode(self.photo_homework_handler.camera_handler)
            self.batch_homework_handler.start_batch_homework_process()
            
            logger.info("已切换到批量批改界面")
            return True
            
        except Exception as e:
            logger.error(f"打开批量批改功能失败: {e}")
            self.show_notification("批量批改", "批量批改功能启动失败")
            return False

    def handle_book_management(self):
        """处理图书管理功能"""        
        try:
            logger.info("打开图书管理功能")
            
            # 检查是否为学校模式
            if self.current_environment != "school":
                logger.warning("图书管理功能仅在学校模式下可用")
                self.show_notification("图书管理", "图书管理功能仅在学校模式下可用")
                return False
            
            # 🆕 在学校模式下暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()
            
            # 延迟初始化拍照搜题处理器（复用摄像头）
            if not self._init_photo_homework_handler():
                logger.error("摄像头处理器初始化失败，无法进入图书管理功能")
                # 🆕 出错时恢复坐姿检测
                self._resume_posture_detection()
                return False
            
            # 初始化图书管理处理器
            if self.book_management_handler is None:
                self.book_management_handler = BookManagementHandler()
                self.book_management_handler.set_camera_handler(self.photo_homework_handler.camera_handler)
                
                # 连接信号
                self.book_management_handler.process_started.connect(self.on_book_management_process_started)
                self.book_management_handler.face_recognition_started.connect(self.on_book_management_face_recognition_started)
                self.book_management_handler.face_recognition_completed.connect(self.on_book_management_face_recognition_completed)
                self.book_management_handler.photo_capture_completed.connect(self.on_book_management_photo_captured)
                self.book_management_handler.analysis_started.connect(self.on_book_management_analysis_started)
                self.book_management_handler.analysis_progress.connect(self.on_book_management_analysis_progress)
                self.book_management_handler.analysis_completed.connect(self.on_book_management_analysis_completed)
                self.book_management_handler.upload_completed.connect(self.on_book_management_upload_completed)
                self.book_management_handler.error_occurred.connect(self.on_book_management_error)
                self.book_management_handler.back_requested.connect(self.on_book_management_back)
                logger.info("图书管理处理器初始化完成")
            
            # 创建图书管理页面
            if self.book_management_page is None:
                self.book_management_page = BookManagementPage()
                self.book_management_page.back_requested.connect(self.on_book_management_back)
                self.stacked_widget.addWidget(self.book_management_page)
                
                # 🔧 复用作业批改逻辑：设置人脸预览组件引用（用于释放摄像头资源）
                self.book_management_handler.set_face_preview_widget(self.book_management_page.face_camera_widget)
                logger.info("图书管理页面创建完成，已设置人脸预览组件引用")
            
            # 切换到图书管理页面
            self.stacked_widget.setCurrentWidget(self.book_management_page)
            
            # 🔧 图书管理功能需要人脸摄像头，确保其正确初始化
            logger.info("图书管理功能：强制重新初始化人脸摄像头...")
            if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                success = self.photo_homework_handler.camera_handler._release_camera_if_needed("face")
                if not success:
                    logger.error("人脸摄像头重新初始化失败")
                    self.show_notification("图书管理", "人脸摄像头初始化失败")
                    self._resume_posture_detection()
                    return False
                logger.info("✅ 人脸摄像头重新初始化成功")
            
            # 🔧 图书管理功能也需要拍照摄像头，确保其正确初始化
            logger.info("图书管理功能：强制重新初始化拍照摄像头...")
            if hasattr(self.photo_homework_handler.camera_handler, '_release_camera_if_needed'):
                success = self.photo_homework_handler.camera_handler._release_camera_if_needed("photo")
                if not success:
                    logger.error("拍照摄像头重新初始化失败")
                    self.show_notification("图书管理", "拍照摄像头初始化失败")
                    self._resume_posture_detection()
                    return False
                logger.info("✅ 拍照摄像头重新初始化成功")
            
            # 启动图书管理模式
            face_camera = self.photo_homework_handler.camera_handler.get_face_camera()
            photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
            self.book_management_page.start_book_management_mode(face_camera, photo_camera)
            self.book_management_handler.start_book_management_process()
            
            logger.info("已切换到图书管理界面")
            return True
            
        except Exception as e:
            logger.error(f"打开图书管理功能失败: {e}")
            self.show_notification("图书管理", "图书管理功能启动失败")
            return False

    def handle_notifications(self):
        """处理通知功能"""
        logger.info("打开通知功能")
        
        # 创建通知页面（如果不存在）
        if not hasattr(self, 'notification_page') or self.notification_page is None:
            from notification_page import NotificationPage
            self.notification_page = NotificationPage()
            self.notification_page.back_requested.connect(self.on_notification_back)
            self.stacked_widget.addWidget(self.notification_page)
        
        # 切换到通知页面
        self.stacked_widget.setCurrentWidget(self.notification_page)
        
        # 显示通知页面打开提示
        self.show_notification("系统通知", "已打开通知中心")

    def on_notification_back(self):
        """通知页面返回处理"""
        logger.info("从通知页面返回到功能选择")
        
        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
        
        # 显示返回提示
        self.show_notification("系统通知", "已返回功能选择页面")
        
    def _start_meeting(self, room_id):
        """开始会议"""
        try:
            logger.info(f"开始会议，房间号: {room_id}")
            
            # 创建会议页面（如果不存在）
            if self.meeting_page is None:
                self.meeting_page = MeetingPage()
                self.meeting_page.back_requested.connect(self.on_meeting_back)
                self.stacked_widget.addWidget(self.meeting_page)
            
            # 启动会议
            self.meeting_page.start_meeting(room_id)
            
            # 切换到会议页面
            self.stacked_widget.setCurrentWidget(self.meeting_page)
            
            # 加入视频会议房间
            self.video_handler.join_room(room_id)
            
            logger.info("会议页面已显示，正在启动视频会议")
            
        except Exception as e:
            logger.error(f"开始会议失败: {e}")
            self.show_notification("视频会议", "启动会议失败")
            
    def _exit_meeting(self):
        """退出会议"""
        try:
            logger.info("退出会议")
            
            # 🔧 修复：向 roomclose topic 发送 exit 消息
            if self.mqtt_handler:
                self.mqtt_handler.send_message("roomclose", "exit")
                logger.info("已向 roomclose topic 发送 exit 消息")
            
            # 关闭视频会议
            self.video_handler.close_current_room()
            
            # 如果会议页面存在，调用退出方法并清理
            if self.meeting_page:
                self.meeting_page.exit_meeting()
                # 清理会议页面
                self.stacked_widget.removeWidget(self.meeting_page)
                self.meeting_page = None
                logger.info("会议页面已清理")
            
            # 返回现代化界面
            self.stacked_widget.setCurrentWidget(self.modern_ui)
            self.show_notification("视频会议", "已退出会议")
            
        except Exception as e:
            logger.error(f"退出会议失败: {e}")
            
    def on_meeting_back(self):
        """会议页面返回处理"""
        logger.info("从会议页面返回到功能选择")
        
        # 🔧 修复：通过_exit_meeting统一处理退出逻辑
        self._exit_meeting()

    def handle_gesture_word(self):
        """处理指尖单词功能"""
        # 显示功能打开通知
        self.show_notification("系统通知", "正在打开指尖单词功能...")
        
        try:
            logger.info("打开指尖单词功能")
            
            # 🆕 暂停坐姿检测（避免摄像头冲突）
            self._pause_posture_detection()
            
            # 创建指尖单词页面
            from gesture_word_page import GestureWordPage
            self.gesture_word_page = GestureWordPage()
            
            # 连接信号
            self.gesture_word_page.back_requested.connect(self.on_gesture_word_back)
            self.gesture_word_page.process_completed.connect(self.on_gesture_word_completed)
            
            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.gesture_word_page)
            self.stacked_widget.setCurrentWidget(self.gesture_word_page)
            
            logger.info("已切换到指尖单词界面")
            
        except Exception as e:
            logger.error(f"打开指尖单词功能失败: {e}")
            # 🆕 出错时恢复坐姿检测
            self._resume_posture_detection()
            self.show_notification("指尖单词", "指尖单词功能启动失败")

    def on_gesture_word_back(self):
        """指尖单词页面返回"""
        logger.info("从指尖单词页面返回")

        # 清理页面
        if hasattr(self, 'gesture_word_page') and self.gesture_word_page:
            try:
                self.gesture_word_page.cleanup()
            except Exception as e:
                logger.warning(f"清理指尖单词页面时出错: {e}")
            
            self.stacked_widget.removeWidget(self.gesture_word_page)
            self.gesture_word_page = None

        # 🔧 修复：强制释放所有摄像头资源，确保不占用摄像头权限
        try:
            # 如果有拍照搜题处理器也在运行，确保其摄像头资源释放
            if hasattr(self, 'photo_homework_handler') and self.photo_homework_handler:
                if hasattr(self.photo_homework_handler, 'camera_handler') and self.photo_homework_handler.camera_handler:
                    logger.info("释放拍照搜题处理器的摄像头资源...")
                    self.photo_homework_handler.camera_handler.close_cameras()
            
            logger.info("所有摄像头资源释放完成")
        except Exception as e:
            logger.warning(f"释放摄像头资源时出错: {e}")

        # 🆕 返回主页面时恢复坐姿检测（仅在家庭模式下）
        self._resume_posture_detection()

        # 🔧 额外保障：确保语音助手服务正常运行
        try:
            if hasattr(self, 'voice_assistant_service') and self.voice_assistant_service:
                logger.info("检查语音助手服务状态...")
                # 确保语音助手从暂停状态中恢复
                self.voice_assistant_service.resume_after_external_audio()
                logger.info("✅ 已确保语音助手服务正常运行")
        except Exception as e:
            logger.warning(f"检查语音助手服务状态失败: {e}")

        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)

    def on_gesture_word_completed(self, word: str):
        """指尖单词识别完成"""
        logger.info(f"指尖单词识别完成: {word}")
        # 可以在这里添加额外的处理逻辑
    
    def exit_voice_assistant(self):
        """退出语音助手"""
        logger.info("退出语音助手")
        
        try:
            # 停止语音助手服务
            if hasattr(self, 'voice_assistant_service') and self.voice_assistant_service:
                logger.info("正在停止语音助手服务...")
                
                # 强制停止服务
                try:
                    self.voice_assistant_service.stop()
                    logger.info("语音助手服务已停止")
                    
                    # 等待一段时间确保所有线程完全停止
                    import time
                    time.sleep(1)
                    
                    # 强制检查是否还有残留的监控线程
                    if (hasattr(self.voice_assistant_service, 'monitor_thread') and 
                        self.voice_assistant_service.monitor_thread and 
                        self.voice_assistant_service.monitor_thread.isRunning()):
                        logger.info("强制终止监控线程...")
                        self.voice_assistant_service.monitor_thread.terminate()
                        self.voice_assistant_service.monitor_thread.wait(2000)
                        
                except Exception as stop_e:
                    logger.error(f"停止语音助手服务失败: {stop_e}")
                
                # 强制设置为None，确保服务被完全清理
                self.voice_assistant_service = None
                
                # 额外的清理：确保监控线程完全停止
                try:
                    import gc
                    gc.collect()  # 强制垃圾回收
                    logger.info("语音助手服务资源已完全清理")
                except Exception as gc_e:
                    logger.warning(f"垃圾回收失败: {gc_e}")
            
            # 清理页面
            if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
                self.stacked_widget.removeWidget(self.voice_assistant_page)
                self.voice_assistant_page = None
            
            # 显示退出通知
            self.show_notification("语音助手", "语音助手已完全退出")
            
            # 返回现代化界面
            self.stacked_widget.setCurrentWidget(self.modern_ui)
            
        except Exception as e:
            logger.error(f"退出语音助手失败: {e}")
            self.show_notification("语音助手", "语音助手退出失败")
    
    def on_voice_assistant_back(self):
        """语音助手页面返回"""
        logger.info("从语音助手页面返回")
        
        # 清理页面
        if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
            self.stacked_widget.removeWidget(self.voice_assistant_page)
            self.voice_assistant_page = None
        
        # 语音助手服务保持后台运行，不需要停止
        logger.info("语音助手服务继续后台运行")
        
        # 显示后台运行通知
        self.show_notification("语音助手", "语音助手正在后台运行")
        
        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
    
    def show_notification(self, title, message):
        """显示通知"""
        self.notification_widget.show_notification(title, message)
    
    # 语音助手信号处理方法
    @pyqtSlot()
    def on_voice_assistant_ready(self):
        """语音助手准备就绪"""
        logger.info("🎤 语音助手准备就绪")
    
    @pyqtSlot(dict)
    def on_voice_wake_detected(self, wake_event):
        """检测到唤醒词"""
        logger.info(f"🎯 检测到唤醒词: {wake_event}")
        # 如果语音助手页面存在，切换到对话界面并更新状态
        if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
            self.voice_assistant_page.switch_to_chat()
            self.voice_assistant_page.update_status("正在等待您的问题...")
    
    @pyqtSlot(str)
    def on_voice_user_speaking(self, user_input):
        """用户说话"""
        logger.info(f"🗣️ 用户输入: {user_input}")
        
        # 检查是否为退出语音命令
        if user_input and ("退出语音" in user_input or "退出助手" in user_input):
            logger.info("🚪 检测到退出语音命令，正在停止语音助手...")
            self.exit_voice_assistant()
            return
        
        # 如果语音助手页面存在，添加用户消息
        if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
            self.voice_assistant_page.add_user_message(user_input)
            self.voice_assistant_page.update_status("正在思考...")
    
    @pyqtSlot(str)
    def on_voice_assistant_responding(self, response):
        """语音助手回复"""
        logger.info(f"🤖 助手回复: {response}")
        # 如果语音助手页面存在，添加AI回复
        if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
            self.voice_assistant_page.add_ai_message(response)
            self.voice_assistant_page.update_status("正在回答...")
            
            # 设置定时器，在5秒后清除状态（模拟TTS播放完成）
            QTimer.singleShot(5000, lambda: self.voice_assistant_page.update_status("") 
                            if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page else None)
    
    @pyqtSlot(str)
    def on_voice_assistant_error(self, error_msg):
        """语音助手错误"""
        logger.error(f"❌ 语音助手错误: {error_msg}")
        # 如果语音助手页面存在，更新状态显示错误
        if hasattr(self, 'voice_assistant_page') and self.voice_assistant_page:
            self.voice_assistant_page.update_status(f"错误: {error_msg}")
        # 显示错误通知
        self.show_notification("语音助手错误", error_msg)
    
    # 拍照搜题三级页面信号处理方法
    @pyqtSlot()
    def on_photo_page_back(self):
        """从拍照搜题页面返回"""
        logger.info("从拍照搜题页面返回主功能界面")

        # 清理拍照搜题页面
        if self.photo_homework_page:
            self.photo_homework_page.cleanup()
            self.stacked_widget.removeWidget(self.photo_homework_page)
            self.photo_homework_page = None

        # 彻底释放拍照搜题处理器和摄像头资源
        if self.photo_homework_handler:
            logger.info("释放拍照搜题处理器和摄像头资源...")
            self.photo_homework_handler.stop()
            self.photo_homework_handler = None
            logger.info("拍照搜题处理器已释放")
            
        # 🆕 恢复坐姿检测
        self._resume_posture_detection()
            
        try:
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                logger.info("✅ 已发送退出作业批改消息: 8-2-0")
        except Exception as e:
            logger.error(f"❌ 发送退出作业批改消息失败: {e}")

        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)

    @pyqtSlot()
    def on_answer_page_back(self):
        """从作业问答页面返回"""
        logger.info("从作业问答页面返回主功能界面")

        # 清理作业问答页面
        if self.answer_photo_page:
            self.answer_photo_page.cleanup()
            self.stacked_widget.removeWidget(self.answer_photo_page)
            self.answer_photo_page = None

        # 🆕 恢复坐姿检测
        self._resume_posture_detection()

        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)

    @pyqtSlot(dict)
    def on_answer_upload_completed(self, result):
        """作业问答流程完成"""
        logger.info("作业问答流程完成")
        success = result.get('success', False)
        if success:
            logger.info(f"作业问答成功：科目={result.get('subject', '未知')}, 难点={result.get('difficulty', '未知')}")
        # 可以在这里添加成功提示或其他处理

    @pyqtSlot(str)
    def on_photo_page_process_started(self, mode):
        """三级页面启动流程处理器"""
        logger.info(f"三级页面启动{mode}模式流程")
        if mode == 'school':
            self.photo_homework_handler.start_school_mode_process()
        elif mode == 'home':
            self.photo_homework_handler.start_home_mode_process()
    

    
    # 拍照搜题信号处理方法
    @pyqtSlot(str)
    def on_photo_process_started(self, mode):
        """拍照搜题流程开始"""
        mode_name = "学校" if mode == 'school' else "家庭"
        logger.info(f"拍照搜题流程开始 - {mode_name}模式")
        # 不再显示任何通知
    
    @pyqtSlot(dict)
    def on_face_recognition_completed(self, student_info):
        """人脸识别完成"""
        try:
            student_name = student_info.get('name', '未知')
            logger.info(f"人脸识别成功: {student_name}")
            # 不再显示通知
            
            # 更新三级页面状态
            if self.photo_homework_page:
                self.photo_homework_page.on_face_recognition_completed(student_info)
                
                # 🔄 重要：切换当前预览组件为拍照摄像头
                if self.photo_homework_page.photo_camera_widget:
                    self.photo_homework_handler.set_current_preview_widget(
                        self.photo_homework_page.photo_camera_widget
                    )
                    logger.info("已切换当前预览组件为拍照摄像头")
                
                # 重要：人脸识别完成后，必须重新初始化并启动拍照摄像头预览
                logger.info("人脸识别完成，准备重新设置拍照摄像头...")
                
                # 先确保拍照摄像头资源可用
                if self.photo_homework_handler.camera_handler._release_camera_if_needed("photo"):
                    photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                    if photo_camera and self.photo_homework_page.photo_camera_widget:
                        logger.info(f"重新设置拍照摄像头: {photo_camera}")
                        
                        # 停止当前预览并重新设置
                        self.photo_homework_page.photo_camera_widget.stop_preview()
                        self.photo_homework_page.photo_camera_widget.set_camera(photo_camera)
                        
                        # 强制启动拍照摄像头预览
                        if photo_camera == "SIMULATED_CAMERA":
                            self.photo_homework_page.photo_camera_widget.start_preview()
                            logger.info("拍照摄像头预览已重新启动（模拟模式）")
                        elif photo_camera and hasattr(photo_camera, 'isOpened') and photo_camera.isOpened():
                            self.photo_homework_page.photo_camera_widget.start_preview()
                            logger.info("拍照摄像头预览已重新启动（真实摄像头）")
                        else:
                            logger.warning(f"拍照摄像头状态异常，尝试重新初始化: {photo_camera}")
                            # 尝试重启摄像头
                            self.photo_homework_handler.camera_handler.restart_cameras()
                            photo_camera = self.photo_homework_handler.camera_handler.get_photo_camera()
                            if photo_camera and hasattr(photo_camera, 'isOpened') and photo_camera.isOpened():
                                self.photo_homework_page.photo_camera_widget.set_camera(photo_camera)
                                self.photo_homework_page.photo_camera_widget.start_preview()
                                logger.info("拍照摄像头重启成功，预览已启动")
                            else:
                                logger.error("拍照摄像头重启失败")
                    else:
                        logger.error("拍照摄像头对象或预览组件不可用")
                else:
                    logger.error("拍照摄像头资源释放失败")
                
                # ✅ 注意：人脸识别完成后，photo_homework_handler 已经自动设置了等待拍照状态
                # 不需要再次手动调用 _wait_for_photo_signal，避免重复设置导致状态混乱
                logger.info("人脸识别完成后的摄像头切换已完成，等待用户发送拍照指令...")
                
        except Exception as e:
            logger.error(f"人脸识别完成处理异常: {e}")
            # 异常情况下记录错误，但不强制启动等待状态
            logger.info("异常情况下，等待用户手动发送拍照指令...")
    
    def _start_photo_homework_waiting(self):
        """已移除：避免重复调用_wait_for_photo_signal导致状态混乱"""
        # 这个方法已经不再需要，因为 photo_homework_handler 在人脸识别完成后
        # 已经正确设置了等待拍照状态，重复调用会导致状态混乱
        logger.info("⚠️ 注意：此方法已废弃，等待状态由 photo_homework_handler 自动管理")
    
    @pyqtSlot()
    def on_face_recognition_failed(self):
        """人脸识别失败，重启摄像头预览"""
        logger.info("收到人脸识别失败信号，重启摄像头预览")
        
        try:
            if self.photo_homework_page and self.photo_homework_page.face_camera_widget:
                # 重新获取人脸识别摄像头
                if self.photo_homework_handler and self.photo_homework_handler.camera_handler:
                    face_camera = self.photo_homework_handler.camera_handler.get_face_camera()
                    
                    if face_camera:
                        logger.info(f"重新设置人脸识别摄像头: {face_camera}")
                        
                        # 停止当前预览并重新设置
                        self.photo_homework_page.face_camera_widget.stop_preview()
                        self.photo_homework_page.face_camera_widget.set_camera(face_camera)
                        
                        # 强制启动人脸识别摄像头预览
                        if face_camera == "SIMULATED_CAMERA":
                            self.photo_homework_page.face_camera_widget.start_preview()
                            logger.info("人脸识别摄像头预览已重新启动（模拟模式）")
                        elif face_camera and hasattr(face_camera, 'isOpened') and face_camera.isOpened():
                            self.photo_homework_page.face_camera_widget.start_preview()
                            logger.info("人脸识别摄像头预览已重新启动（真实摄像头）")
                        else:
                            logger.warning(f"人脸识别摄像头状态异常，尝试重新初始化: {face_camera}")
                            # 尝试重启摄像头
                            self.photo_homework_handler.camera_handler.restart_cameras()
                            face_camera = self.photo_homework_handler.camera_handler.get_face_camera()
                            if face_camera and hasattr(face_camera, 'isOpened') and face_camera.isOpened():
                                self.photo_homework_page.face_camera_widget.set_camera(face_camera)
                                self.photo_homework_page.face_camera_widget.start_preview()
                                logger.info("人脸识别摄像头重启成功，预览已启动")
                            else:
                                logger.error("人脸识别摄像头重启失败")
                    else:
                        logger.error("人脸识别摄像头对象不可用")
                else:
                    logger.error("拍照搜题处理器或摄像头处理器不可用")
            else:
                logger.error("拍照搜题页面或人脸摄像头组件不可用")
                
        except Exception as e:
            logger.error(f"重启人脸识别摄像头预览失败: {e}")
    
    @pyqtSlot(bool)
    def on_photo_capture_completed(self, success):
        """拍照完成"""
        if success:
            logger.info("拍照成功")
        else:
            logger.error("拍照失败")
        # 不再显示任何通知
        
        # 更新三级页面状态
        if self.photo_homework_page:
            self.photo_homework_page.on_photo_captured()
    
    @pyqtSlot()
    def on_upload_started(self):
        """开始上传分析"""
        logger.info("开始上传分析")
        
        # 更新三级页面状态
        if self.photo_homework_page:
            self.photo_homework_page.on_analysis_started()
    
    @pyqtSlot(dict)
    def on_upload_completed(self, result):
        """上传分析完成"""
        logger.info("作业分析完成")
        # 不再显示通知
        
        # 更新三级页面状态
        if self.photo_homework_page:
            self.photo_homework_page.on_upload_ready()
    
    @pyqtSlot(bool)
    def on_database_saved(self, success):
        """数据库保存完成"""
        if success:
            logger.info("数据保存成功")
        else:
            logger.error("数据保存失败")
        # 不再显示任何通知
    
    @pyqtSlot(dict)
    def on_photo_process_completed(self, result_data):
        """拍照搜题流程完成"""
        logger.info("拍照搜题流程完成，显示结果")
        # 不再显示通知
        
        # 清理三级页面
        if self.photo_homework_page:
            self.photo_homework_page.cleanup()
            self.stacked_widget.removeWidget(self.photo_homework_page)
            self.photo_homework_page = None
        
        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
        
        # 显示结果界面
        self.show_homework_result(result_data)
    
    @pyqtSlot(str)
    def on_photo_error_occurred(self, error_msg):
        """拍照搜题流程出错"""
        logger.error(f"拍照搜题流程错误: {error_msg}")
        # 不显示错误通知，通知框专用于MQTT消息
    
    def show_homework_result(self, result_data):
        """显示作业批改结果"""
        try:
            # 清理之前的结果显示界面
            if self.result_display:
                if self.result_display in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
                    self.stacked_widget.removeWidget(self.result_display)
                self.result_display = None

            # 创建嵌入式结果显示界面
            self.result_display = ResultDisplayWidget(embedded=True)
            self.result_display.close_requested.connect(self.on_result_display_closed)
            self.result_display.back_requested.connect(self.on_result_display_back)
            self.result_display.display_result(result_data)

            # 添加到堆栈并切换
            self.stacked_widget.addWidget(self.result_display)
            self.stacked_widget.setCurrentWidget(self.result_display)

            logger.info("嵌入式结果显示界面已打开")

        except Exception as e:
            logger.error(f"显示结果界面失败: {e}")
            # 不显示错误通知
    
    # 批量批改信号处理方法
    @pyqtSlot(str)
    def on_batch_homework_process_started(self, process_type):
        """批量批改流程开始"""
        logger.info(f"批量批改流程开始: {process_type}")
    
    @pyqtSlot()
    def on_batch_homework_photo_captured(self):
        """批量批改拍照完成"""
        logger.info("批量批改拍照完成")
        if self.batch_homework_page:
            self.batch_homework_page.on_photo_captured()
    
    @pyqtSlot()
    def on_batch_homework_analysis_started(self):
        """批量批改AI分析开始"""
        logger.info("批量批改AI分析开始")
        if self.batch_homework_page:
            self.batch_homework_page.on_analysis_started()
    
    @pyqtSlot(str)
    def on_batch_homework_analysis_progress(self, progress_msg):
        """批量批改AI分析进度更新"""
        logger.info(f"批量批改AI分析进度: {progress_msg}")
        if self.batch_homework_page:
            self.batch_homework_page.on_analysis_progress(progress_msg)
    
    @pyqtSlot(dict)
    def on_batch_homework_upload_completed(self, analysis_result):
        """批量批改分析完成"""
        logger.info("批量批改分析完成，显示全屏结果")
        
        # 创建并显示批量批改结果页面
        self.show_batch_homework_result(analysis_result)
    
    @pyqtSlot(str)
    def on_batch_homework_error(self, error_msg):
        """批量批改流程出错"""
        logger.error(f"批量批改流程错误: {error_msg}")
        if self.batch_homework_page:
            self.batch_homework_page.on_error_occurred(error_msg)
    
    @pyqtSlot()
    def on_batch_homework_back(self):
        """从批量批改页面返回"""
        logger.info("从批量批改页面返回功能选择")
        
        # 清理批量批改处理器
        if self.batch_homework_handler:
            self.batch_homework_handler.cleanup()
        
        # 清理批量批改页面
        if self.batch_homework_page:
            self.batch_homework_page.cleanup()
            self.stacked_widget.removeWidget(self.batch_homework_page)
            self.batch_homework_page = None
        
        # 清理批量批改结果页面
        if self.batch_homework_result_page:
            self.batch_homework_result_page.cleanup()
            self.stacked_widget.removeWidget(self.batch_homework_result_page)
            self.batch_homework_result_page = None
        
        # 🔧 释放拍照摄像头资源，为其他功能让路
        if hasattr(self, 'photo_homework_handler') and self.photo_homework_handler:
            if hasattr(self.photo_homework_handler, 'camera_handler') and self.photo_homework_handler.camera_handler:
                try:
                    logger.info("批量批改退出：释放拍照摄像头资源...")
                    if self.photo_homework_handler.camera_handler.photo_camera and self.photo_homework_handler.camera_handler.photo_camera != "SIMULATED_CAMERA":
                        self.photo_homework_handler.camera_handler.photo_camera.release()
                        self.photo_homework_handler.camera_handler.photo_camera = None
                        logger.info("✅ 拍照摄像头资源已释放")
                except Exception as e:
                    logger.warning(f"释放拍照摄像头资源时出错: {e}")
        
        # 🆕 返回主页面时恢复坐姿检测（仅在家庭模式下）
        self._resume_posture_detection()
        
        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)

    # 图书管理信号处理方法
    @pyqtSlot(str)
    def on_book_management_process_started(self, process_type):
        """图书管理流程开始"""
        logger.info(f"图书管理流程开始: {process_type}")

    @pyqtSlot()
    def on_book_management_face_recognition_started(self):
        """图书管理人脸识别开始"""
        logger.info("图书管理人脸识别开始")
        if self.book_management_page:
            self.book_management_page.on_face_recognition_started()

    @pyqtSlot(dict)  
    def on_book_management_face_recognition_completed(self, student_info):
        """图书管理人脸识别完成"""
        logger.info(f"图书管理人脸识别完成: {student_info}")
        if self.book_management_page:
            self.book_management_page.on_face_recognition_completed(student_info)

    @pyqtSlot()
    def on_book_management_photo_captured(self):
        """图书管理拍照完成"""
        logger.info("图书管理拍照完成")
        if self.book_management_page:
            self.book_management_page.on_photo_captured()
        try:
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                logger.info("✅ 已发送退出作业批改消息: 8-2-0")
        except Exception as e:
            logger.error(f"❌ 发送退出作业批改消息失败: {e}")

    @pyqtSlot()
    def on_book_management_analysis_started(self):
        """图书管理AI分析开始"""
        logger.info("图书管理AI分析开始")
        if self.book_management_page:
            self.book_management_page.on_analysis_started()

    @pyqtSlot(str)
    def on_book_management_analysis_progress(self, progress_msg):
        """图书管理AI分析进度更新"""
        logger.info(f"图书管理AI分析进度: {progress_msg}")
        if self.book_management_page:
            self.book_management_page.on_analysis_progress(progress_msg)

    @pyqtSlot(str)
    def on_book_management_analysis_completed(self, book_name):
        """图书管理AI分析完成"""
        logger.info(f"图书管理AI分析完成: {book_name}")
        if self.book_management_page:
            self.book_management_page.on_analysis_completed(book_name)

    @pyqtSlot(dict)
    def on_book_management_upload_completed(self, result):
        """图书管理上传完成"""
        logger.info(f"图书管理上传完成: {result}")
        if self.book_management_page:
            self.book_management_page.on_upload_completed(result)

    @pyqtSlot(str)
    def on_book_management_error(self, error_msg):
        """图书管理错误处理"""
        logger.error(f"图书管理错误: {error_msg}")
        if self.book_management_page:
            self.book_management_page.on_error_occurred(error_msg)

    @pyqtSlot()
    def on_book_management_back(self):
        """从图书管理页面返回"""
        logger.info("从图书管理页面返回功能选择")
        
        # 清理图书管理处理器
        if self.book_management_handler:
            self.book_management_handler.cleanup()
        
        # 清理图书管理页面
        if self.book_management_page:
            self.book_management_page.cleanup()
            self.stacked_widget.removeWidget(self.book_management_page)
            self.book_management_page = None
        
        # 🔧 释放人脸摄像头资源，为其他功能让路
        if hasattr(self, 'photo_homework_handler') and self.photo_homework_handler:
            if hasattr(self.photo_homework_handler, 'camera_handler') and self.photo_homework_handler.camera_handler:
                try:
                    logger.info("图书管理退出：释放人脸摄像头资源...")
                    if self.photo_homework_handler.camera_handler.face_camera and self.photo_homework_handler.camera_handler.face_camera != "SIMULATED_CAMERA":
                        self.photo_homework_handler.camera_handler.face_camera.release()
                        self.photo_homework_handler.camera_handler.face_camera = None
                        logger.info("✅ 人脸摄像头资源已释放")
                except Exception as e:
                    logger.warning(f"释放人脸摄像头资源时出错: {e}")
        
        # 🆕 返回主页面时恢复坐姿检测（仅在家庭模式下）
        self._resume_posture_detection()
        
        # 返回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
        try:
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                logger.info("✅ 已发送退出作业批改消息: 8-2-0")
        except Exception as e:
            logger.error(f"❌ 发送退出作业批改消息失败: {e}")
    
    def show_batch_homework_result(self, analysis_result):
        """显示批量批改结果页面"""
        try:
            logger.info("创建并显示批量批改结果页面")
            
            # 创建批量批改结果页面
            if self.batch_homework_result_page:
                self.batch_homework_result_page.cleanup()
                self.stacked_widget.removeWidget(self.batch_homework_result_page)
            
            self.batch_homework_result_page = BatchHomeworkResultPage()
            self.batch_homework_result_page.back_requested.connect(self.on_batch_homework_back)
            self.stacked_widget.addWidget(self.batch_homework_result_page)
            
            # 显示分析结果
            self.batch_homework_result_page.display_analysis_result(analysis_result)
            
            # 切换到结果页面
            self.stacked_widget.setCurrentWidget(self.batch_homework_result_page)
            logger.info("已切换到批量批改结果页面")
            
        except Exception as e:
            logger.error(f"显示批量批改结果失败: {e}")
            self.show_notification("错误", f"显示结果失败: {e}")
    
    @pyqtSlot()
    def on_result_display_closed(self):
        """结果显示界面关闭"""
        if self.result_display:
            if self.result_display in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
                self.stacked_widget.removeWidget(self.result_display)
            self.result_display = None
            # 返回现代化界面
            self.stacked_widget.setCurrentWidget(self.modern_ui)
            logger.info("结果显示界面已关闭")

    @pyqtSlot()
    def on_result_display_back(self):
        """结果显示界面返回主页"""
        if self.result_display:
            if self.result_display in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
                self.stacked_widget.removeWidget(self.result_display)
            self.result_display = None
            # 返回现代化界面
            self.stacked_widget.setCurrentWidget(self.modern_ui)
            logger.info("从结果显示界面返回主页")

    @pyqtSlot()
    def on_settings_back(self):
        """设置页面返回"""
        logger.info("从设置页面返回")
        
        # 切换回现代化界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)

    # 🆕 坐姿检测管理方法
    def _start_posture_detection(self):
        """启动坐姿检测线程（仅家庭模式）"""
        try:
            if not self.posture_monitoring_enabled:
                logger.info("坐姿监控已禁用，跳过启动")
                return
                
            # if self.posture_detection_thread is None:
            #     logger.info("正在启动坐姿检测线程...")
                
            #     # 导入坐姿检测线程
            #     from pose_detection_thread import PoseDetectionThread
                
            #     # 创建线程实例
            #     self.posture_detection_thread = PoseDetectionThread()
                
            #     # 连接信号
            #     self.posture_detection_thread.detection_completed.connect(self.on_posture_detection_completed)
            #     self.posture_detection_thread.posture_alert.connect(self.on_posture_alert)
            #     self.posture_detection_thread.myopia_risk_alert.connect(self.on_myopia_risk_alert)
            #     self.posture_detection_thread.error_occurred.connect(self.on_posture_detection_error)
            #     self.posture_detection_thread.status_changed.connect(self.on_posture_status_changed)
            #     self.posture_detection_thread.latest_photo_ready.connect(self.on_posture_photo_ready)
                
            #     # 启动检测
            #     self.posture_detection_thread.start_detection()
                
            #     logger.info("✅ 坐姿检测线程启动成功")
            #     self.show_notification("坐姿监控", "坐姿检测已启动，将定期监控您的坐姿")
                
            # elif not self.posture_detection_thread.is_running:
            #     # 如果线程存在但未运行，重新启动
            #     logger.info("重新启动坐姿检测...")
            #     self.posture_detection_thread.start_detection()
                
        except Exception as e:
            ssh=1
            # logger.error(f"启动坐姿检测线程失败: {e}")
            # self.show_notification("坐姿监控", "坐姿检测启动失败")

    def _stop_posture_detection(self, close_cameras=True):
        """停止坐姿检测线程"""
        try:
            ssh=1
            # if self.posture_detection_thread:
            #     logger.info("正在停止坐姿检测线程...")
            #     self.posture_detection_thread.stop_detection(close_cameras)
                
            #     # 等待线程结束
            #     if self.posture_detection_thread.isRunning():
            #         self.posture_detection_thread.wait(3000)
                
            #     logger.info("✅ 坐姿检测线程已停止")
                
        except Exception as e:
            logger.error(f"停止坐姿检测线程失败: {e}")

    def _pause_posture_detection(self):
        pass
        """暂停坐姿检测（在使用摄像头的功能期间）"""
        # try:
        #     if self.posture_detection_thread and self.posture_detection_thread.is_running:
        #         logger.info("暂停坐姿检测（摄像头被其他功能占用）")
        #         self.posture_detection_thread.pause_detection()
        # except Exception as e:
        #     logger.error(f"暂停坐姿检测失败: {e}")

    def _resume_posture_detection(self):
        pass
        """恢复坐姿检测（其他功能释放摄像头后）"""
        # try:
        #     if (self.posture_detection_thread and 
        #         self.posture_detection_thread.is_paused and 
        #         self.current_environment == 'home'):
        #         logger.info("恢复坐姿检测")
        #         self.posture_detection_thread.resume_detection()
        # except Exception as e:
        #     logger.error(f"恢复坐姿检测失败: {e}")

    # 🆕 坐姿检测信号处理方法
    @pyqtSlot(dict)
    def on_posture_detection_completed(self, result_data):
        """坐姿检测完成"""
        detection_count = result_data.get('detection_count', 0)
        detection_data = result_data.get('detection_data', {})
        severity = detection_data.get('severity', '正常')
        
        logger.info(f"坐姿检测 #{detection_count} 完成: {severity}")
        # 可以在这里添加UI更新逻辑，比如在状态栏显示最新检测结果

    @pyqtSlot(str, int)
    def on_posture_alert(self, alert_message, consecutive_count):
        """坐姿警告"""
        logger.warning(f"坐姿警告: {alert_message}")
        self.show_notification("坐姿提醒", alert_message)

    @pyqtSlot(str, int)
    def on_myopia_risk_alert(self, alert_message, consecutive_count):
        """近视风险警告"""
        logger.warning(f"近视风险警告: {alert_message}")
        self.show_notification("护眼提醒", alert_message)

    @pyqtSlot(str)
    def on_posture_detection_error(self, error_msg):
        """坐姿检测错误"""
        logger.error(f"坐姿检测错误: {error_msg}")
        # 不显示错误通知，避免干扰用户

    @pyqtSlot(str)
    def on_posture_status_changed(self, status):
        """坐姿检测状态变化"""
        logger.info(f"坐姿检测状态: {status}")

    @pyqtSlot(object, object)
    def on_posture_photo_ready(self, frame, timestamp):
        """坐姿检测照片准备就绪"""
        # 这里可以选择是否在UI中显示最新的检测照片
        # 由于是后台监控，通常不需要显示
        pass

    def closeEvent(self, event):
        """关闭事件处理"""
        logger.info("应用程序正在关闭...")
        
        # 🆕 停止坐姿检测线程
        self._stop_posture_detection()
        
        # 停止语音助手服务
        if hasattr(self, 'voice_assistant_service') and self.voice_assistant_service:
            logger.info("停止语音助手服务...")
            self.voice_assistant_service.stop()
        
        # 停止拍照搜题处理器
        if hasattr(self, 'photo_homework_handler') and self.photo_homework_handler:
            self.photo_homework_handler.stop()
        
        # 关闭结果显示界面
        if hasattr(self, 'result_display') and self.result_display:
            self.result_display.close()
        
        # 停止MQTT处理器
        if hasattr(self, 'mqtt_handler'):
            self.mqtt_handler.stop()
            
        # 关闭视频会议
        if hasattr(self, 'video_handler'):
            self.video_handler.close_current_room()
            
        event.accept()

    # 🆕 思路解答信号处理方法
    @pyqtSlot(str)
    def on_thinking_guidance_process_started(self, mode):
        """思路解答流程开始"""
        logger.info(f"思路解答流程开始: {mode}")

    @pyqtSlot(dict)
    def on_thinking_guidance_face_recognition_completed(self, result):
        """思路解答人脸识别完成"""
        logger.info(f"思路解答人脸识别完成: {result}")

    @pyqtSlot()
    def on_thinking_guidance_face_recognition_failed(self):
        """思路解答人脸识别失败"""
        logger.warning("思路解答人脸识别失败")

    @pyqtSlot(bool)
    def on_thinking_guidance_photo_capture_completed(self, success):
        """思路解答拍照完成"""
        logger.info(f"思路解答拍照完成: {success}")
        try:
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                logger.info("✅ 已发送退出作业批改消息: 8-2-0")
        except Exception as e:
            logger.error(f"❌ 发送退出作业批改消息失败: {e}")

    @pyqtSlot()
    def on_thinking_guidance_upload_started(self):
        """思路解答上传开始"""
        logger.info("思路解答上传分析开始")

    @pyqtSlot(dict)
    def on_thinking_guidance_upload_completed(self, result):
        """思路解答上传完成"""
        logger.info(f"思路解答上传完成: {result}")

    @pyqtSlot(bool)
    def on_thinking_guidance_database_saved(self, success):
        """思路解答数据库保存完成"""
        logger.info(f"思路解答数据库保存: {success}")

    @pyqtSlot(dict)
    def on_thinking_guidance_process_completed(self, result):
        """思路解答流程完成"""
        logger.info(f"思路解答流程完成: {result}")
        
        # 显示思路解答结果
        self._show_thinking_guidance_result(result)

    @pyqtSlot()
    def on_thinking_guidance_back(self):
        """从思路解答页面返回"""
        logger.info("从思路解答页面返回功能选择")
        try:
            if self.mqtt_handler:
                self.mqtt_handler.send_esp32_control_command("8-2-0")
                logger.info("✅ 已发送退出作业批改消息: 8-2-0")
        except Exception as e:
            logger.error(f"❌ 发送退出作业批改消息失败: {e}")
        
        # 🆕 恢复坐姿检测
        self._resume_posture_detection()
        
        # 停止思路解答处理器
        if self.thinking_guidance_handler:
            self.thinking_guidance_handler.stop()
        
        # 移除思路解答页面
        if self.thinking_guidance_page:
            if self.thinking_guidance_page in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
                self.stacked_widget.removeWidget(self.thinking_guidance_page)
            self.thinking_guidance_page = None
        
        # 返回功能选择界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
        self.modern_ui.show_function_selection()

    @pyqtSlot(str)  
    def on_thinking_guidance_page_process_started(self, process_type):
        """思路解答页面流程开始"""
        logger.info(f"思路解答页面流程开始: {process_type}")

    @pyqtSlot(str)
    def on_thinking_guidance_error_occurred(self, error_msg):
        """思路解答错误处理"""
        logger.error(f"思路解答错误: {error_msg}")
        self.show_notification("思路解答", f"错误: {error_msg}")

    def _show_thinking_guidance_result(self, result_data):
        """显示思路解答结果"""
        try:
            logger.info("显示思路解答结果")
            
            # 🔧 使用专门的思路解答结果展示页面
            self.thinking_result_display = ThinkingResultDisplayWidget()
            self.thinking_result_display.back_requested.connect(self.on_thinking_guidance_result_closed)
            
            # 准备思路解答的显示内容，转换为ResultDisplayWidget期望的格式
            upload_result = result_data.get('upload_result', {})
            thinking_process = upload_result.get('thinking_process', '暂无思路分析')
            key_points = upload_result.get('key_points', [])
            knowledge_areas = upload_result.get('knowledge_areas', [])
            tips = upload_result.get('tips', [])
            
            # 构建analysis_content格式的内容
            analysis_content = f"**🧠 解题思路分析:**\n\n{thinking_process}\n\n"
            
            if key_points:
                analysis_content += "**📝 关键解题步骤:**\n"
                for i, point in enumerate(key_points, 1):
                    analysis_content += f"{i}. {point}\n"
                analysis_content += "\n"
            
            if knowledge_areas:
                analysis_content += "**📚 相关知识点:**\n"
                for area in knowledge_areas:
                    analysis_content += f"• {area}\n"
                analysis_content += "\n"
            
            if tips:
                analysis_content += "**💡 解题提示:**\n"
                for tip in tips:
                    analysis_content += f"• {tip}\n"
            
            # 构造ResultDisplayWidget期望的数据格式
            display_data = {
                'mode': result_data.get('mode', 'home'),
                'student_info': result_data.get('student_info'),
                'upload_result': {
                    'error_numbers': [],  # 思路解答没有错误题号
                    'weak_areas': [],     # 不显示薄弱点分析
                    'analysis_content': analysis_content
                }
            }
            
            self.thinking_result_display.display_result(display_data)
            
            # 添加到堆栈并显示
            self.stacked_widget.addWidget(self.thinking_result_display)
            self.stacked_widget.setCurrentWidget(self.thinking_result_display)
            
            logger.info("思路解答结果页面已显示")
            
        except Exception as e:
            logger.error(f"显示思路解答结果失败: {e}")
            self.show_notification("错误", f"显示结果失败: {e}")

    @pyqtSlot()
    def on_thinking_guidance_result_closed(self):
        """思路解答结果页面关闭"""
        # 处理思路解答专用结果展示页面
        if hasattr(self, 'thinking_result_display') and self.thinking_result_display:
            if self.thinking_result_display in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
                self.stacked_widget.removeWidget(self.thinking_result_display)
            self.thinking_result_display = None
            
        # 返回功能选择界面
        self.stacked_widget.setCurrentWidget(self.modern_ui)
        self.modern_ui.show_function_selection()
        
        # 🆕 恢复坐姿检测
        self._resume_posture_detection()
        
        logger.info("思路解答结果页面已关闭")


class FunctionDetailWidget(QWidget):
    """功能详情页面基类"""
    
    def __init__(self, function_name, parent=None):
        super().__init__(parent)
        self.function_name = function_name
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # 功能标题
        title_label = QLabel(self.function_name)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-bottom: 20px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 功能内容
        content_label = QLabel("功能开发中...")
        content_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #666;
            }
        """)
        content_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(content_label)
        
        self.setLayout(layout)


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(WINDOW_CONFIG['title'])
    app.setOrganizationName("智能学习助手")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 创建主窗口
    main_window = MainWindow()
    main_window.show()

    # 设置窗口全屏显示
    # main_window.showFullScreen()
    
    logger.info("应用程序启动完成")
    
    # 运行应用程序
    try:
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"应用程序运行时发生错误: {e}")
        sys.exit(1)



if __name__ == '__main__':
    main() 