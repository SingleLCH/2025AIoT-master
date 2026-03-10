# -*- coding: utf-8 -*-
"""
批量批改页面
用于显示批量批改流程的界面
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QStackedWidget, QFrame,
                           QScrollArea, QGridLayout, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QPalette

from embedded_camera_widget import EmbeddedCameraWidget
from todo_step_components import TodoFlowPanel
from result_display import ResultDisplayWidget

logger = logging.getLogger(__name__)


class BatchHomeworkPage(QWidget):
    """批量批改页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状态变量
        self.current_stage = 'waiting'  # 'waiting', 'photo_captured', 'analyzing', 'completed'
        self.photo_count = 0
        
        # UI组件
        self.todo_flow_panel = None
        self.camera_widget = None
        self.content_stack = None
        self.result_display = None
        
        self.init_ui()
        logger.info("批量批改页面初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        # 使用水平布局，保持与作业批改页面风格一致
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧：TODO流程面板
        self.create_todo_panel(main_layout)
        
        # 右侧：内容面板
        self.create_content_panel(main_layout)
    
    def create_nav_bar(self):
        """创建导航栏"""
        nav_frame = QFrame()
        nav_frame.setFixedHeight(60)
        nav_frame.setStyleSheet("""
            QFrame {
                background-color: #4C566A;
                border-radius: 8px;
                border: none;
            }
        """)
        
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(20, 10, 20, 10)
        
        # 模式标签
        self.mode_label = QLabel("学校模式")
        self.mode_label.setFont(QFont("微软雅黑", 14, QFont.Bold))
        self.mode_label.setStyleSheet("color: #ECEFF4;")
        nav_layout.addWidget(self.mode_label)
        
        nav_layout.addStretch()
        
        # 标题标签
        self.title_label = QLabel("智能批量作业批改系统")
        self.title_label.setFont(QFont("微软雅黑", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #88C0D0;")
        nav_layout.addWidget(self.title_label)
        
        nav_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("等待开始...")
        self.status_label.setFont(QFont("微软雅黑", 12))
        self.status_label.setStyleSheet("color: #D8DEE9;")
        nav_layout.addWidget(self.status_label)
        
        return nav_frame
    
    def create_content_panel(self, main_layout):
        """创建内容面板"""
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border-radius: 10px;
                border: 1px solid #4C566A;
                color: #ECEFF4;
            }
        """)
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # 顶部导航栏
        nav_bar = self.create_nav_bar()
        content_layout.addWidget(nav_bar)
        
        # 主内容区域 - 使用堆叠布局切换不同阶段
        self.content_stack = QStackedWidget()
        
        # 等待页面
        self.waiting_page = self.create_waiting_page()
        self.content_stack.addWidget(self.waiting_page)
        
        # 拍照页面
        self.camera_page = self.create_camera_page()
        self.content_stack.addWidget(self.camera_page)
        
        # 结果页面
        self.result_page = self.create_result_page()
        self.content_stack.addWidget(self.result_page)
        
        content_layout.addWidget(self.content_stack)
        content_frame.setLayout(content_layout)
        
        main_layout.addWidget(content_frame, 1)
    
    def create_waiting_page(self):
        """创建等待页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 阶段标题
        stage_label = QLabel("批量作业批改")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        stage_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 10px;
                border-left: 5px solid #e67e22;
            }
        """)
        layout.addWidget(stage_label)
        
        # 提示内容
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(30)
        
        # 提示图标
        icon_label = QLabel()
        icon_label.setText("📷")
        icon_label.setFont(QFont("Arial", 72))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #88C0D0; margin: 20px;")
        content_layout.addWidget(icon_label)
        
        # 提示文字
        hint_label = QLabel("请使用手势指令控制批量批改流程")
        hint_label.setFont(QFont("微软雅黑", 16, QFont.Bold))
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #7f8c8d; margin: 20px;")
        content_layout.addWidget(hint_label)
        
        # 指令说明
        instructions = [
            "6-0-1: 拍摄作业照片",
            "6-0-2: 返回功能选择页面", 
            "6-0-4: 上传并分析照片"
        ]
        
        for instruction in instructions:
            inst_label = QLabel(instruction)
            inst_label.setFont(QFont("微软雅黑", 14))
            inst_label.setAlignment(Qt.AlignCenter)
            inst_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
            content_layout.addWidget(inst_label)
        
        layout.addWidget(content_widget)
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def create_camera_page(self):
        """创建摄像头预览页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 阶段标题
        stage_label = QLabel("拍摄作业")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        stage_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 10px;
                border-left: 5px solid #e74c3c;
            }
        """)
        layout.addWidget(stage_label)
        
        # 批量拍照摄像头预览 - 复用现有的EmbeddedCameraWidget
        self.camera_widget = EmbeddedCameraWidget(
            title="批量作业拍照摄像头", 
            preview_size=(720, 540),
            clip_mode=2  # 使用和作业拍照相同的模式
        )
        layout.addWidget(self.camera_widget)
        
        # 流程指示和状态
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setSpacing(10)
        
        # 拍照状态显示
        self.photo_status_label = QLabel("请将作业放在摄像头下方，使用手势指令拍照")
        self.photo_status_label.setAlignment(Qt.AlignCenter)
        self.photo_status_label.setFont(QFont("微软雅黑", 16))
        self.photo_status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                padding: 10px;
            }
        """)
        status_layout.addWidget(self.photo_status_label)
        
        # 拍照计数显示
        self.photo_count_label = QLabel("已拍摄: 0 张")
        self.photo_count_label.setFont(QFont("微软雅黑", 14))
        self.photo_count_label.setAlignment(Qt.AlignCenter)
        self.photo_count_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                padding: 5px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.photo_count_label)
        
        layout.addWidget(status_container)
        layout.addStretch()
        page.setLayout(layout)
        return page
    
    def create_result_page(self):
        """创建结果显示页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 阶段标题
        stage_label = QLabel("分析结果")
        stage_label.setAlignment(Qt.AlignCenter)
        stage_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        stage_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 10px;
                border-left: 5px solid #27ae60;
            }
        """)
        layout.addWidget(stage_label)
        
        # 创建结果显示组件
        self.result_display = ResultDisplayWidget()
        self.result_display.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.result_display)
        
        page.setLayout(layout)
        return page
    
    def create_todo_panel(self, main_layout):
        """创建TODO流程面板"""
        # 定义批量批改的流程步骤
        steps_data = [
            (1, "第一步：拍摄作业", "拍摄需要批改的作业照片"),
            (2, "第二步：AI分析", "上传照片进行智能批量分析"),
            (3, "第三步：结果展示", "显示分析结果和教学建议")
        ]
        
        self.todo_flow_panel = TodoFlowPanel("批量批改流程", steps_data)
        self.todo_panel_container = QWidget()
        
        container_layout = QVBoxLayout(self.todo_panel_container)
        container_layout.addWidget(self.todo_flow_panel)
        
        main_layout.addWidget(self.todo_panel_container)
    
    def start_batch_homework_mode(self, camera_handler):
        """开始批量批改模式"""
        logger.info("开始批量批改模式")
        
        # 重置状态
        self.current_stage = 'waiting'
        self.photo_count = 0
        self.update_photo_count()
        
        # 更新流程状态
        if self.todo_flow_panel:
            self.todo_flow_panel.set_step_current(1)
            self.todo_flow_panel.update_status("等待拍照指令...")
        
        # 设置摄像头并启动预览（参考家庭模式逻辑）
        if self.camera_widget and camera_handler:
            photo_camera = camera_handler.get_photo_camera()
            if photo_camera:
                logger.info(f"设置批量拍照摄像头: {photo_camera}")
                self.camera_widget.set_camera(photo_camera)
                # 强制启动预览
                if photo_camera == "SIMULATED_CAMERA" or (photo_camera and hasattr(photo_camera, 'isOpened') and photo_camera.isOpened()):
                    self.camera_widget.start_preview()
                    logger.info("批量拍照摄像头预览已启动")
        
        # 切换到拍照页面显示摄像头预览（参考家庭模式）
        self.content_stack.setCurrentIndex(1)
        self.update_status("请使用手势指令拍摄作业照片")
        
        logger.info("批量批改模式启动完成")
    
    @pyqtSlot()
    def on_photo_captured(self):
        """拍照完成"""
        logger.info("拍照完成")
        
        self.photo_count += 1
        self.update_photo_count()
        
        # 保持在摄像头页面，更新拍照状态
        self.content_stack.setCurrentIndex(1)
        self.photo_status_label.setText("拍照成功！可继续拍照或上传分析")
        
        # 更新TODO流程状态
        if self.todo_flow_panel:
            # 拍照成功，保持第一步进行中，更新状态提示
                         self.todo_flow_panel.update_status(f"已拍摄 {self.photo_count} 张照片，可继续拍照或使用6-0-4上传分析")
        
        # 更新状态
        self.update_status(f"已拍摄 {self.photo_count} 张，等待更多拍照或上传指令...")
    
    @pyqtSlot()
    def on_analysis_started(self):
        """AI分析开始"""
        logger.info("批量批改AI分析开始")
        
        # 更新TODO面板状态
        if self.todo_flow_panel:
            self.todo_flow_panel.set_step_completed(1)  # 拍摄作业完成
            self.todo_flow_panel.set_step_current(2)    # 当前AI分析
            self.todo_flow_panel.update_status("AI分析开始，请稍候...")
        
        # 更新状态
        self.update_status("正在进行AI分析...")
    
    @pyqtSlot(str)
    def on_analysis_progress(self, progress_msg):
        """AI分析进度更新"""
        logger.info(f"批量批改AI分析进度: {progress_msg}")
        
        # 更新TODO面板状态
        if self.todo_flow_panel:
            self.todo_flow_panel.update_status(f"AI分析中: {progress_msg}")
        
        # 更新状态
        self.update_status(f"AI分析中: {progress_msg}")
    
    @pyqtSlot(dict)
    def on_upload_completed(self, analysis_result):
        """上传分析完成"""
        logger.info(f"批量批改页面收到上传完成信号，结果类型: {type(analysis_result)}")
        logger.info(f"分析结果内容: {analysis_result}")
        
        # 更新流程状态
        if self.todo_flow_panel:
            logger.info("更新TODO流程状态")
            self.todo_flow_panel.set_step_completed(1)  # 拍摄作业完成
            self.todo_flow_panel.set_step_completed(2)  # AI分析完成
            self.todo_flow_panel.set_step_current(3)    # 当前显示结果
            self.todo_flow_panel.update_status("AI分析完成，正在显示结果")
        
        # 显示分析结果
        logger.info("开始显示分析结果")
        self.show_analysis_result(analysis_result)
        
        # 切换到结果页面
        logger.info("切换到结果页面")
        self.content_stack.setCurrentIndex(2)
        self.update_status("分析完成")
        
        # 标记流程完成
        if self.todo_flow_panel:
            self.todo_flow_panel.set_step_completed(3)
            self.todo_flow_panel.update_status("批量批改完成")
        
        logger.info("批量批改完成处理结束")
    
    def show_analysis_result(self, analysis_result):
        """显示分析结果"""
        if not self.result_display:
            return
        
        try:
            # 构建结果显示内容
            content_html = self.build_result_html(analysis_result)
            
            # 显示结果
            self.result_display.display_content(
                title="批量作业分析报告",
                content=content_html,
                show_back_button=False
            )
            
        except Exception as e:
            logger.error(f"显示分析结果失败: {e}")
    
    def build_result_html(self, analysis_result):
        """构建结果HTML内容"""
        try:
            html_parts = []
            
            # 添加CSS样式
            html_parts.append("""
            <style>
                body { 
                    font-family: 'Microsoft YaHei', sans-serif; 
                    line-height: 1.6; 
                    color: #2E3440; 
                    margin: 0; 
                    padding: 20px;
                }
                .section { 
                    margin-bottom: 30px; 
                    padding: 20px; 
                    background: #F8F9FA; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .section-title { 
                    color: #2E3440; 
                    font-size: 20px; 
                    font-weight: bold; 
                    margin-bottom: 15px; 
                    border-bottom: 2px solid #88C0D0; 
                    padding-bottom: 8px;
                }
                .mistake-item, .weak-item { 
                    margin: 10px 0; 
                    padding: 15px; 
                    background: white; 
                    border-left: 4px solid #88C0D0; 
                    border-radius: 5px;
                }
                .recommendation { 
                    margin: 8px 0; 
                    padding: 12px; 
                    background: #E8F4F8; 
                    border-radius: 5px; 
                    border-left: 3px solid #81A1C1;
                }
                .stat { 
                    color: #BF616A; 
                    font-weight: bold; 
                }
                .summary { 
                    background: #FFF9E6; 
                    border: 1px solid #EBCB8B; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin: 15px 0;
                }
            </style>
            """)
            
            html_parts.append("<h1 style='color: #2E3440; text-align: center; margin-bottom: 30px;'>📊 批量作业分析报告</h1>")
            
            # 错误分析部分
            error_analysis = analysis_result.get('error_analysis', {})
            if error_analysis:
                html_parts.append('<div class="section">')
                html_parts.append('<div class="section-title">🔍 错误分析</div>')
                
                # 常见错误
                common_mistakes = error_analysis.get('common_mistakes', [])
                if common_mistakes:
                    html_parts.append('<h3>常见错误：</h3>')
                    for mistake in common_mistakes:
                        question_id = mistake.get('question_id', 'N/A')
                        error_rate = mistake.get('error_rate', 0)
                        reason = mistake.get('reason', 'N/A')
                        
                        html_parts.append(f'''
                        <div class="mistake-item">
                            <strong>题目 {question_id}</strong><br>
                            <span class="stat">错误率: {error_rate:.1%}</span><br>
                            <strong>原因:</strong> {reason}
                        </div>
                        ''')
                
                # 薄弱知识点
                weak_points = error_analysis.get('class_weak_points', [])
                if weak_points:
                    html_parts.append('<h3>班级薄弱知识点：</h3>')
                    for point in weak_points:
                        knowledge_point = point.get('knowledge_point', 'N/A')
                        wrong_rate = point.get('wrong_rate', 0)
                        related_questions = point.get('related_questions', [])
                        
                        html_parts.append(f'''
                        <div class="weak-item">
                            <strong>{knowledge_point}</strong><br>
                            <span class="stat">错误率: {wrong_rate:.1%}</span><br>
                            <strong>相关题目:</strong> {', '.join(related_questions)}
                        </div>
                        ''')
                
                html_parts.append('</div>')
            
            # 教学建议部分
            teaching_advice = analysis_result.get('ai_teaching_advice', {})
            if teaching_advice:
                html_parts.append('<div class="section">')
                html_parts.append('<div class="section-title">💡 AI教学建议</div>')
                
                # 总结
                summary = teaching_advice.get('summary', '')
                if summary:
                    html_parts.append(f'<div class="summary"><strong>总结：</strong>{summary}</div>')
                
                # 建议列表
                recommendations = teaching_advice.get('recommendations', [])
                if recommendations:
                    html_parts.append('<h3>具体建议：</h3>')
                    for i, rec in enumerate(recommendations, 1):
                        html_parts.append(f'<div class="recommendation">{i}. {rec}</div>')
                
                html_parts.append('</div>')
            
            return ''.join(html_parts)
            
        except Exception as e:
            logger.error(f"构建结果HTML失败: {e}")
            return f"<p>结果显示出错: {e}</p>"
    
    def update_status(self, status_text):
        """更新状态显示"""
        self.status_label.setText(status_text)
    
    def update_photo_count(self):
        """更新拍照计数"""
        if hasattr(self, 'photo_count_label'):
            self.photo_count_label.setText(f"已拍摄: {self.photo_count} 张")
    
    @pyqtSlot()
    def on_back_requested(self):
        """处理返回请求"""
        logger.info("批量批改页面收到返回请求")
        self.back_requested.emit()
    
    @pyqtSlot(str)
    def on_error_occurred(self, error_message):
        """处理错误"""
        logger.error(f"批量批改过程出错: {error_message}")
        self.update_status(f"错误: {error_message}")
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理批量批改页面资源")
        
        # 停止摄像头预览
        if self.camera_widget:
            self.camera_widget.stop_preview()
            logger.info("摄像头预览已停止")
            
        # 重置状态
        self.current_stage = 'waiting'
        self.photo_count = 0
        
        # 重置TODO流程状态
        if self.todo_flow_panel:
            self.todo_flow_panel.set_step_current(1)
            self.todo_flow_panel.update_status("等待开始...")
        
        # 切换回等待页面
        if self.content_stack:
            self.content_stack.setCurrentIndex(0) 