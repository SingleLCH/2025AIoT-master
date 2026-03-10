# -*- coding: utf-8 -*-
"""
拍照搜题主程序入口
整合人脸识别、拍照、上传分析和结果展示功能
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
from photo_homework_handler import PhotoHomeworkHandler
from result_display import ResultDisplayWidget

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PhotoHomeworkMainWidget(QWidget):
    """拍照搜题主界面"""
    
    def __init__(self):
        super().__init__()
        
        # 核心处理器
        self.homework_handler = None
        self.result_display = None
        
        # 界面状态
        self.current_mode = None
        self.is_processing = False
        
        self.setup_ui()
        self.init_handler()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("智能拍照搜题系统")
        self.setGeometry(200, 200, 600, 400)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # 标题
        title_label = QLabel("📸 智能拍照搜题系统")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 20px;
                background-color: #ecf0f1;
                border-radius: 15px;
                margin-bottom: 20px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("请选择使用模式：")
        desc_label.setFont(QFont("Microsoft YaHei", 16))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #34495e; margin-bottom: 20px;")
        main_layout.addWidget(desc_label)
        
        # 模式选择按钮
        self.create_mode_buttons(main_layout)
        
        # 状态显示区域
        self.create_status_area(main_layout)
        
        self.setLayout(main_layout)
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
        """)
    
    def create_mode_buttons(self, main_layout):
        """创建模式选择按钮"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)
        
        # 学校模式按钮
        self.school_button = QPushButton("🏫 学校模式")
        self.school_button.setFont(QFont("Microsoft YaHei", 16))
        self.school_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 20px 30px;
                border-radius: 12px;
                font-weight: bold;
                min-width: 200px;
                min-height: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.school_button.clicked.connect(self.start_school_mode)
        
        # 家庭模式按钮
        self.home_button = QPushButton("🏠 家庭模式")
        self.home_button.setFont(QFont("Microsoft YaHei", 16))
        self.home_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 20px 30px;
                border-radius: 12px;
                font-weight: bold;
                min-width: 200px;
                min-height: 80px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.home_button.clicked.connect(self.start_home_mode)
        
        button_layout.addWidget(self.school_button)
        button_layout.addWidget(self.home_button)
        
        main_layout.addLayout(button_layout)
        
        # 模式说明
        school_desc = QLabel("需要人脸识别验证身份")
        school_desc.setAlignment(Qt.AlignCenter)
        school_desc.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        home_desc = QLabel("直接开始拍照搜题")
        home_desc.setAlignment(Qt.AlignCenter)
        home_desc.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(school_desc)
        desc_layout.addWidget(home_desc)
        
        main_layout.addLayout(desc_layout)
    
    def create_status_area(self, main_layout):
        """创建状态显示区域"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #95a5a6;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }
        """)
        
        status_layout = QVBoxLayout()
        
        # 状态标题
        status_title = QLabel("系统状态")
        status_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        status_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        status_layout.addWidget(status_title)
        
        # 状态信息
        self.status_label = QLabel("系统就绪，请选择模式")
        self.status_label.setFont(QFont("Microsoft YaHei", 12))
        self.status_label.setStyleSheet("color: #27ae60;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        # 进度信息
        self.progress_label = QLabel("")
        self.progress_label.setFont(QFont("Microsoft YaHei", 11))
        self.progress_label.setStyleSheet("color: #7f8c8d; margin-top: 5px;")
        self.progress_label.setWordWrap(True)
        status_layout.addWidget(self.progress_label)
        
        status_frame.setLayout(status_layout)
        main_layout.addWidget(status_frame)
    
    def init_handler(self):
        """初始化处理器"""
        try:
            self.homework_handler = PhotoHomeworkHandler()
            
            # 连接信号
            self.homework_handler.process_started.connect(self.on_process_started)
            self.homework_handler.face_recognition_completed.connect(self.on_face_recognition_completed)
            self.homework_handler.photo_capture_completed.connect(self.on_photo_capture_completed)
            self.homework_handler.upload_completed.connect(self.on_upload_completed)
            self.homework_handler.database_saved.connect(self.on_database_saved)
            self.homework_handler.process_completed.connect(self.on_process_completed)
            self.homework_handler.error_occurred.connect(self.on_error_occurred)
            
            self.update_status("系统初始化完成，就绪", "#27ae60")
            
        except Exception as e:
            logger.error(f"初始化处理器失败: {e}")
            self.update_status(f"系统初始化失败: {e}", "#e74c3c")
            self.school_button.setEnabled(False)
            self.home_button.setEnabled(False)
    
    def start_school_mode(self):
        """开始学校模式"""
        if self.is_processing:
            return
        
        logger.info("用户选择学校模式")
        self.current_mode = 'school'
        self.set_processing_state(True)
        
        if self.homework_handler:
            self.homework_handler.start_school_mode_process()
    
    def start_home_mode(self):
        """开始家庭模式"""
        if self.is_processing:
            return
        
        logger.info("用户选择家庭模式")
        self.current_mode = 'home'
        self.set_processing_state(True)
        
        if self.homework_handler:
            self.homework_handler.start_home_mode_process()
    
    def set_processing_state(self, processing: bool):
        """设置处理状态"""
        self.is_processing = processing
        self.school_button.setEnabled(not processing)
        self.home_button.setEnabled(not processing)
    
    def update_status(self, message: str, color: str = "#2c3e50"):
        """更新状态显示"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_progress(self, message: str):
        """更新进度信息"""
        self.progress_label.setText(message)
    
    # 信号处理方法
    def on_process_started(self, mode: str):
        """流程开始"""
        mode_name = "学校" if mode == 'school' else "家庭"
        self.update_status(f"开始 {mode_name} 模式流程", "#3498db")
        
        if mode == 'school':
            self.update_progress("等待人脸识别...")
        else:
            self.update_progress("等待拍照确认信号...")
    
    def on_face_recognition_completed(self, student_info: dict):
        """人脸识别完成"""
        student_name = student_info.get('name', '未知')
        self.update_status(f"识别成功：{student_name}", "#27ae60")
        self.update_progress("等待拍照确认信号...")
    
    def on_photo_capture_completed(self, success: bool):
        """拍照完成"""
        if success:
            self.update_status("拍照完成", "#27ae60")
            self.update_progress("等待上传确认信号...")
        else:
            self.update_status("拍照失败", "#e74c3c")
            self.set_processing_state(False)
    
    def on_upload_completed(self, result: dict):
        """上传完成"""
        self.update_status("作业分析完成", "#27ae60")
        self.update_progress("正在保存到数据库...")
    
    def on_database_saved(self, success: bool):
        """数据库保存完成"""
        if success:
            self.update_status("数据保存成功", "#27ae60")
            self.update_progress("准备显示结果...")
        else:
            self.update_status("数据保存失败", "#e74c3c")
            self.set_processing_state(False)
    
    def on_process_completed(self, result_data: dict):
        """整个流程完成"""
        self.update_status("流程完成！", "#27ae60")
        self.update_progress("正在准备结果展示...")
        
        # 显示结果界面
        self.show_result_display(result_data)
        
        # 重置状态
        self.set_processing_state(False)
        self.update_status("系统就绪，请选择模式", "#27ae60")
        self.update_progress("")
    
    def on_error_occurred(self, error_msg: str):
        """错误发生"""
        logger.error(f"流程错误: {error_msg}")
        self.update_status(f"错误：{error_msg}", "#e74c3c")
        self.update_progress("")
        
        # 显示错误对话框
        QMessageBox.critical(self, "错误", error_msg)
        
        # 重置状态
        self.set_processing_state(False)
        self.update_status("系统就绪，请选择模式", "#27ae60")
    
    def show_result_display(self, result_data: dict):
        """显示结果界面"""
        try:
            if self.result_display:
                self.result_display.close()
            
            self.result_display = ResultDisplayWidget()
            self.result_display.close_requested.connect(self.on_result_display_closed)
            self.result_display.display_result(result_data)
            self.result_display.show()
            
        except Exception as e:
            logger.error(f"显示结果界面失败: {e}")
            QMessageBox.critical(self, "错误", f"显示结果失败: {e}")
    
    def on_result_display_closed(self):
        """结果显示界面关闭"""
        if self.result_display:
            self.result_display = None
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            if self.homework_handler:
                self.homework_handler.stop()
            
            if self.result_display:
                self.result_display.close()
            
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭程序时出错: {e}")
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序图标和名称
    app.setApplicationName("智能拍照搜题系统")
    app.setApplicationVersion("1.0.0")
    
    try:
        # 创建主窗口
        main_widget = PhotoHomeworkMainWidget()
        main_widget.show()
        
        logger.info("应用程序启动成功")
        
        # 运行应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        QMessageBox.critical(None, "启动错误", f"应用程序启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 