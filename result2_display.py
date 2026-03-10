# -*- coding: utf-8 -*-
"""
结果展示界面
用于显示拍照搜题的结果，包括错误题号和解题分析
"""

import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QScrollArea, QPushButton, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from config import RESULT_DISPLAY_CONFIG


class ResultDisplayWidgetnew(QWidget):
    """结果展示界面"""

    # 信号定义
    close_requested = pyqtSignal()  # 关闭请求信号
    back_requested = pyqtSignal()   # 返回主页信号

    def __init__(self, embedded=True):
        super().__init__()
        self.embedded = embedded
        self.scroll_area = None
        self.content_widget = None
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        if not self.embedded:
            self.setWindowTitle("作业批改结果")
            self.setGeometry(100, 100, 1000, 700)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容容器
        self.content_widget = QWidget()
        # 设置内容容器的大小策略，确保高度自适应内容
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(15, 15, 15, 15)
        # 确保布局紧凑，不添加额外空间
        content_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        
        # 标题
        title_label = QLabel("📝 作业批改结果")
        title_font = QFont()
        title_font.setPointSize(RESULT_DISPLAY_CONFIG['title_font_size'])
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 4px 8px;
                background-color: #ecf0f1;
                border-radius: 10px;
                margin-bottom: 10px;
            }
        """)
        content_layout.addWidget(title_label)

        # 结果概览区域
        self.create_summary_section(content_layout)

        # 错误题号区域
        self.create_error_numbers_section(content_layout)

        # 解题分析区域
        self.create_analysis_section(content_layout)

        # 按钮区域（仅在非嵌入模式显示）
        if not self.embedded:
            self.create_button_section(content_layout)

        # 设置内容到滚动区域
        self.content_widget.setLayout(content_layout)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

        # 确保内容加载后调整滚动区域
        self._adjust_scroll_area()
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
        """)

    def _adjust_scroll_area(self):
        """调整滚动区域大小，确保内容高度正确"""
        # 使用QTimer延迟调整，确保布局完全完成
        QTimer.singleShot(100, self._do_adjust_scroll_area)

    def _do_adjust_scroll_area(self):
        """实际执行滚动区域调整"""
        try:
            # 重置高度限制，让内容自然展开
            self.content_widget.setMinimumHeight(0)
            self.content_widget.setMaximumHeight(16777215)  # Qt的最大高度

            # 强制重新计算布局
            self.content_widget.layout().activate()
            self.content_widget.layout().update()
            self.content_widget.updateGeometry()
            self.content_widget.adjustSize()

            # 获取布局计算后的实际高度
            actual_height = self.content_widget.sizeHint().height()

            # 如果高度太小，使用最小合理高度
            min_height = 200
            if actual_height < min_height:
                actual_height = min_height

            # 设置内容容器的固定高度
            self.content_widget.setFixedHeight(actual_height)

            # 更新滚动区域
            self.scroll_area.updateGeometry()

            print(f"调整滚动区域: 内容高度 = {actual_height}")

        except Exception as e:
            print(f"调整滚动区域失败: {e}")

    def create_summary_section(self, main_layout):
        """创建结果概览区域"""
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.Box)
        summary_frame.setFixedHeight(80)  # 你可以根据实际需求调整数值
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 20px;
                padding: 4px 8px;          # 减小内边距
            }
        """)
        
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(5)                    # 设置间距
        # summary_layout.setContentsMargins(0, 0, 0, 0)  # 无边距
        
        # 学生信息（仅学校模式显示）
        self.student_info_label = QLabel("👤 学生：--")
        self.student_info_label.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size']))
        self.student_info_label.setStyleSheet("color: #34495e; font-weight: bold;")
        summary_layout.addWidget(self.student_info_label)

        # 模式信息
        self.mode_label = QLabel("🏠 模式：家庭")
        self.mode_label.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size']))
        self.mode_label.setStyleSheet("color: #34495e; font-weight: bold;")
        summary_layout.addWidget(self.mode_label)

        # 处理时间
        self.time_label = QLabel("⏰ 时间：--")
        self.time_label.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size']))
        self.time_label.setStyleSheet("color: #34495e; font-weight: bold;")
        summary_layout.addWidget(self.time_label)
        
        # 三个QLabel组件设置
        for label in [self.student_info_label, self.mode_label, self.time_label]:
            label.setMaximumHeight(50)  # 根据字体大小设置合适的最大高度
            label.setStyleSheet("""
                QLabel {
                    color: #34495e;
                    background-color: #f8f9fa;
                    border: 1px solid #bdc3c7;
                    border-radius: 8px;
                    padding: 2px 8px;
                    margin: 0 2px;
                    font-weight: bold;
                }
            """)
        
        summary_frame.setLayout(summary_layout)
        # main_layout.addWidget(summary_frame)
    
    def create_error_numbers_section(self, main_layout):
        """创建错误题号区域"""
        error_frame = QFrame()
        error_frame.setFrameStyle(QFrame.Box)
        error_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e74c3c;
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        
        error_layout = QVBoxLayout()
        error_layout.setSpacing(10)
        
        # 标题
        error_title = QLabel("❌ 错误题号")
        error_title.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['title_font_size'] - 2, QFont.Bold))
        error_title.setStyleSheet("color: #e74c3c; margin-bottom: 10px;")
        error_title.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(error_title)

        # 错误题号显示
        self.error_numbers_label = QLabel("暂无错误题目")
        self.error_numbers_label.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size'] + 2, QFont.Bold))
        self.error_numbers_label.setStyleSheet("""
            QLabel {
                color: #c0392b;
                background-color: #ffeaa7;
                padding: 15px;
                border-radius: 10px;
                border: 2px solid #fdcb6e;
                min-height: 40px;
            }
        """)
        self.error_numbers_label.setAlignment(Qt.AlignCenter)
        self.error_numbers_label.setWordWrap(True)
        # error_layout.addWidget(self.error_numbers_label)

        # 薄弱知识点
        weak_areas_title = QLabel("📚 薄弱知识点")
        weak_areas_title.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size'] + 2, QFont.Bold))
        weak_areas_title.setStyleSheet("color: #e74c3c; margin-top: 10px; margin-bottom: 10px;")
        weak_areas_title.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(weak_areas_title)

        self.weak_areas_label = QLabel("暂无薄弱知识点")
        self.weak_areas_label.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size']))
        self.weak_areas_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #fab1a0;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #e17055;
            }
        """)
        self.weak_areas_label.setAlignment(Qt.AlignCenter)
        self.weak_areas_label.setWordWrap(True)
        # error_layout.addWidget(self.weak_areas_label)
        
        error_frame.setLayout(error_layout)
        # main_layout.addWidget(error_frame)
        
        # 添加分割线
        # self.create_separator_line(main_layout)
    
    def create_separator_line(self, main_layout):
        """创建分割线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: #bdc3c7;
                background-color: #bdc3c7;
                border: none;
                height: 2px;
                margin: 20px 50px;
            }
        """)
        main_layout.addWidget(separator)
    
    def create_analysis_section(self, main_layout):
        """创建解题分析区域"""
        analysis_frame = QFrame()
        analysis_frame.setFrameStyle(QFrame.Box)
        analysis_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #3498db;
                border-radius: 15px;
                padding: 15px;
                margin-top: 10px;
            }
        """)
        
        analysis_layout = QVBoxLayout()
        analysis_layout.setSpacing(10)
        
        # 标题
        analysis_title = QLabel("🧠 详细分析过程")
        analysis_title.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['title_font_size'] - 2, QFont.Bold))
        analysis_title.setStyleSheet("color: #3498db; margin-bottom: 10px;")
        analysis_title.setAlignment(Qt.AlignCenter)
        analysis_layout.addWidget(analysis_title)

        # 分析内容标签（使用QLabel替代QTextEdit避免嵌套滚动）
        self.analysis_text = QLabel()
        self.analysis_text.setFont(QFont("Microsoft YaHei", RESULT_DISPLAY_CONFIG['font_size']+5))
        self.analysis_text.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                color: #2c3e50;
            }
        """)
        self.analysis_text.setWordWrap(True)
        self.analysis_text.setAlignment(Qt.AlignTop)
        self.analysis_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.analysis_text.setText("详细分析过程加载中...")

        analysis_layout.addWidget(self.analysis_text)

        analysis_frame.setLayout(analysis_layout)
        main_layout.addWidget(analysis_frame)
    
    def create_button_section(self, main_layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.setFont(QFont("Microsoft YaHei", 14))
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7b7c;
            }
        """)
        close_button.clicked.connect(self.close_requested.emit)
        
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def display_result(self, result_data: dict):
        """
        显示结果数据
        
        Args:
            result_data: 包含以下字段的字典
                - mode: 'school' 或 'home'
                - student_info: 学生信息（仅学校模式）
                - upload_result: 上传结果
                - analysis_content: 解题分析内容
        """
        try:
            # 更新模式信息
            mode = result_data.get('mode', 'home')
            # if mode == 'school':
            #     self.mode_label.setText("🏫 模式：学校")
                
            #     # 显示学生信息
            #     student_info = result_data.get('student_info', {})
            #     student_name = student_info.get('name', '未知')
            #     self.student_info_label.setText(f"👤 学生：{student_name}")
            #     self.student_info_label.show()
            # else:
            #     self.mode_label.setText("🏠 模式：家庭")
            #     self.student_info_label.hide()
            
            # 更新时间
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # self.time_label.setText(f"⏰ 时间：{current_time}")
            
            # 显示错误题号和薄弱知识点
            upload_result = result_data.get('upload_result', {})
            error_numbers = upload_result.get('error_numbers', [])
            weak_areas = upload_result.get('weak_areas', [])
            
            if error_numbers:
                # 格式化错误题号显示
                if len(error_numbers) == 1:
                    error_text = f"第 {error_numbers[0]} 题"
                else:
                    error_text = f"第 {', '.join(map(str, error_numbers))} 题"

                self.error_numbers_label.setText(error_text)
                self.error_numbers_label.setStyleSheet(f"""
                    QLabel {{
                        color: #c0392b;
                        background-color: #ffeaa7;
                        padding: 15px;
                        border-radius: 10px;
                        border: 2px solid #fdcb6e;
                        font-weight: bold;
                        min-height: 40px;
                        font-size: {RESULT_DISPLAY_CONFIG['font_size'] + 15}px;
                    }}
                """)
            else:
                self.error_numbers_label.setText("🎉 全部正确！")
                self.error_numbers_label.setStyleSheet(f"""
                    QLabel {{
                        color: #27ae60;
                        background-color: #d5f4e6;
                        padding: 15px;
                        border-radius: 10px;
                        border: 2px solid #a9dfbf;
                        font-weight: bold;
                        min-height: 40px;
                        font-size: {RESULT_DISPLAY_CONFIG['font_size'] + 2}px;
                    }}
                """)
            
            if weak_areas:
                weak_text = "、".join(weak_areas)
                self.weak_areas_label.setText(weak_text)
                self.weak_areas_label.setStyleSheet("""
                    QLabel {
                        color: #2c3e50;
                        background-color: #fab1a0;
                        padding: 15px;
                        border-radius: 8px;
                        border: 1px solid #e17055;
                    }
                """)
            else:
                self.weak_areas_label.setText("🌟 知识掌握良好")
                self.weak_areas_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        background-color: #d5f4e6;
                        padding: 15px;
                        border-radius: 8px;
                        border: 1px solid #a9dfbf;
                    }
                """)
            
            # 显示解题分析
            # 🔧 修复：analysis_content在upload_result中，不在result_data顶层
            analysis_content = upload_result.get('analysis_content', '')
            if analysis_content:
                # 解析思考过程
                formatted_analysis = self._format_analysis_content(analysis_content)
                self.analysis_text.setText(formatted_analysis)
            else:
                self.analysis_text.setText("暂无详细分析内容")
            
        except Exception as e:
            print(f"显示结果失败: {e}")
            self.analysis_text.setText(f"显示结果时出错: {e}")

        # 内容加载完成后，重新调整滚动区域大小
        self._adjust_scroll_area()
    
    def _format_analysis_content(self, content: str) -> str:
        """
        格式化分析内容，重点突出思考过程
        
        Args:
            content: 原始分析内容
            
        Returns:
            格式化后的内容
        """
        try:
            # 提取思考过程部分
            thinking_match = re.search(r'====================思考过程====================(.*?)(?:====================模型回复====================|$)', 
                                     content, re.DOTALL)
            
            if thinking_match:
                thinking_content = thinking_match.group(1).strip()
                
                # 更详细的格式化
                lines = thinking_content.split('\n')
                formatted_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 添加题目编号的标识
                    if '第' in line and '题' in line and ('错误' in line or '正确' in line or '对' in line):
                        formatted_lines.append(f"\n📝 {line}")
                    # 添加结论性语句的标识
                    elif '所以' in line or '因此' in line or '综上' in line:
                        formatted_lines.append(f"\n💡 {line}")
                    # 普通分析内容
                    else:
                        formatted_lines.append(line)
                
                formatted = '\n'.join(formatted_lines)
                
                # 添加头部说明
                header = "🤖 AI智能分析过程：\n" + "="*50 + "\n"
                
                return f"{header}{formatted}\n\n" + "="*50 + "\n✨ 分析完成"
            else:
                # 如果没有找到思考过程，尝试直接显示内容
                if content.strip():
                    return f"📋 分析内容：\n\n{content}"
                else:
                    return "暂无详细分析内容"
                
        except Exception as e:
            return f"❌ 分析内容格式化失败: {e}\n\n📄 原始内容：\n{content}"
    
    def scroll_up(self):
        """向上滚动"""
        if self.scroll_area:
            scrollbar = self.scroll_area.verticalScrollBar()
            current_value = scrollbar.value()
            new_value = max(0, current_value - RESULT_DISPLAY_CONFIG['scroll_step'])

            if RESULT_DISPLAY_CONFIG['scroll_smooth']:
                self._smooth_scroll_to(new_value)
            else:
                scrollbar.setValue(new_value)

    def scroll_down(self):
        """向下滚动"""
        if self.scroll_area:
            scrollbar = self.scroll_area.verticalScrollBar()
            current_value = scrollbar.value()
            max_value = scrollbar.maximum()
            new_value = min(max_value, current_value + RESULT_DISPLAY_CONFIG['scroll_step'])

            if RESULT_DISPLAY_CONFIG['scroll_smooth']:
                self._smooth_scroll_to(new_value)
            else:
                scrollbar.setValue(new_value)

    def _smooth_scroll_to(self, target_value):
        """平滑滚动到目标位置"""
        if not hasattr(self, '_scroll_animation'):
            self._scroll_animation = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value")
            self._scroll_animation.setDuration(200)
            self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(self.scroll_area.verticalScrollBar().value())
        self._scroll_animation.setEndValue(target_value)
        self._scroll_animation.start()

    def handle_control_command(self, action):
        """处理MQTT控制命令"""
        if action == 'up':
            self.scroll_up()
        elif action == 'down':
            self.scroll_down()
        elif action == 'next':  # 6-0-3 命令映射为返回主页
            self.back_requested.emit()
        elif action == 'back':
            self.back_requested.emit()

    def closeEvent(self, event):
        """关闭事件"""
        self.close_requested.emit()
        event.accept()