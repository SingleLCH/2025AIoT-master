# -*- coding: utf-8 -*-
"""
批量批改结果展示页面
专门用于展示批量批改的分析结果，包括错题分析、总结和建议
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class BatchHomeworkResultPage(QWidget):
    """批量批改结果展示页面"""
    
    # 信号定义
    back_requested = pyqtSignal()  # 返回功能选择信号
    
    def __init__(self):
        super().__init__()
        self.analysis_result = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建标题
        self.create_title_section(main_layout)
        
        # 创建滚动区域
        self.create_scroll_area(main_layout)
        
        self.setLayout(main_layout)
    
    def create_title_section(self, main_layout):
        """创建标题区域"""
        title_label = QLabel("📊 批量作业分析报告")
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
        
        # 操作提示
        tip_label = QLabel("按 6-0-2 返回功能选择页面")
        tip_label.setFont(QFont("Microsoft YaHei", 16))
        tip_label.setAlignment(Qt.AlignCenter)
        tip_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                background-color: #d5dbdb;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 15px;
            }
        """)
        main_layout.addWidget(tip_label)
    
    def create_scroll_area(self, main_layout):
        """创建滚动区域"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 初始化各个区域
        self.create_error_analysis_section()
        self.create_summary_section()
        self.create_recommendations_section()
        
        self.content_widget.setLayout(self.content_layout)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)
    
    def create_error_analysis_section(self):
        """创建错题分析区域"""
        error_frame = QFrame()
        error_frame.setFrameStyle(QFrame.Box)
        error_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 3px solid #e74c3c;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)
        
        error_layout = QVBoxLayout()
        error_layout.setSpacing(15)
        
        # 标题
        error_title = QLabel("❌ 错题分析")
        error_title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        error_title.setStyleSheet("color: #e74c3c; margin-bottom: 15px;")
        error_title.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(error_title)
        
        # 常见错误区域
        self.common_mistakes_label = QLabel("正在加载错题分析...")
        self.common_mistakes_label.setFont(QFont("Microsoft YaHei", 16))
        self.common_mistakes_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #ffeaa7;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #fdcb6e;
                line-height: 1.6;
            }
        """)
        self.common_mistakes_label.setWordWrap(True)
        self.common_mistakes_label.setAlignment(Qt.AlignTop)
        error_layout.addWidget(self.common_mistakes_label)
        
        # 薄弱知识点区域
        weak_title = QLabel("📚 薄弱知识点")
        weak_title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        weak_title.setStyleSheet("color: #e74c3c; margin-top: 15px; margin-bottom: 10px;")
        weak_title.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(weak_title)
        
        self.weak_points_label = QLabel("正在加载薄弱知识点...")
        self.weak_points_label.setFont(QFont("Microsoft YaHei", 16))
        self.weak_points_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #fab1a0;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #e17055;
                line-height: 1.6;
            }
        """)
        self.weak_points_label.setWordWrap(True)
        self.weak_points_label.setAlignment(Qt.AlignTop)
        error_layout.addWidget(self.weak_points_label)
        
        error_frame.setLayout(error_layout)
        self.content_layout.addWidget(error_frame)
    
    def create_summary_section(self):
        """创建总结区域"""
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.Box)
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 3px solid #3498db;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)
        
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(15)
        
        # 标题
        summary_title = QLabel("📋 总体分析")
        summary_title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        summary_title.setStyleSheet("color: #3498db; margin-bottom: 15px;")
        summary_title.setAlignment(Qt.AlignCenter)
        summary_layout.addWidget(summary_title)
        
        # 总结内容
        self.summary_label = QLabel("正在加载总体分析...")
        self.summary_label.setFont(QFont("Microsoft YaHei", 16))
        self.summary_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #ebf3fd;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #85c1e9;
                line-height: 1.8;
            }
        """)
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignTop)
        summary_layout.addWidget(self.summary_label)
        
        summary_frame.setLayout(summary_layout)
        self.content_layout.addWidget(summary_frame)
    
    def create_recommendations_section(self):
        """创建建议区域"""
        recommendations_frame = QFrame()
        recommendations_frame.setFrameStyle(QFrame.Box)
        recommendations_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 3px solid #27ae60;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
            }
        """)
        
        recommendations_layout = QVBoxLayout()
        recommendations_layout.setSpacing(15)
        
        # 标题
        recommendations_title = QLabel("💡 教学建议")
        recommendations_title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        recommendations_title.setStyleSheet("color: #27ae60; margin-bottom: 15px;")
        recommendations_title.setAlignment(Qt.AlignCenter)
        recommendations_layout.addWidget(recommendations_title)
        
        # 建议内容
        self.recommendations_label = QLabel("正在加载教学建议...")
        self.recommendations_label.setFont(QFont("Microsoft YaHei", 16))
        self.recommendations_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background-color: #d5f4e6;
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #a9dfbf;
                line-height: 1.8;
            }
        """)
        self.recommendations_label.setWordWrap(True)
        self.recommendations_label.setAlignment(Qt.AlignTop)
        recommendations_layout.addWidget(self.recommendations_label)
        
        recommendations_frame.setLayout(recommendations_layout)
        self.content_layout.addWidget(recommendations_frame)
    
    def display_analysis_result(self, analysis_result):
        """显示分析结果"""
        try:
            logger.info(f"显示批量批改分析结果: {analysis_result}")
            self.analysis_result = analysis_result
            
            # 处理错误分析
            self.display_error_analysis(analysis_result.get('error_analysis', {}))
            
            # 处理教学建议
            self.display_teaching_advice(analysis_result.get('ai_teaching_advice', {}))
            
        except Exception as e:
            logger.error(f"显示分析结果失败: {e}")
            self.common_mistakes_label.setText(f"显示结果时出错: {e}")
    
    def display_error_analysis(self, error_analysis):
        """显示错误分析"""
        try:
            # 处理常见错误
            common_mistakes = error_analysis.get('common_mistakes', [])
            if common_mistakes:
                mistakes_text = "🔍 本次作业中发现的主要错误：\n\n"
                for i, mistake in enumerate(common_mistakes, 1):
                    question_id = mistake.get('question_id', f'Q{i}')
                    error_rate = mistake.get('error_rate', 0)
                    reason = mistake.get('reason', '未知原因')
                    
                    mistakes_text += f"{i}. {question_id}题 (错误率: {error_rate*100:.0f}%)\n"
                    mistakes_text += f"   ❌ 错误原因: {reason}\n\n"
                    
                self.common_mistakes_label.setText(mistakes_text)
            else:
                self.common_mistakes_label.setText("🎉 本次作业完成情况良好，未发现明显的共性错误！")
            
            # 处理薄弱知识点
            weak_points = error_analysis.get('class_weak_points', [])
            if weak_points:
                weak_text = "📈 需要重点关注的知识点：\n\n"
                for i, point in enumerate(weak_points, 1):
                    knowledge_point = point.get('knowledge_point', '未知知识点')
                    wrong_rate = point.get('wrong_rate', 0)
                    related_questions = point.get('related_questions', [])
                    
                    weak_text += f"{i}. {knowledge_point} (错误率: {wrong_rate*100:.0f}%)\n"
                    weak_text += f"   📝 相关题目: {', '.join(related_questions)}\n\n"
                    
                self.weak_points_label.setText(weak_text)
            else:
                self.weak_points_label.setText("🌟 学生们对各个知识点掌握良好，没有发现明显的薄弱环节！")
                
        except Exception as e:
            logger.error(f"显示错误分析失败: {e}")
            self.common_mistakes_label.setText(f"错误分析显示失败: {e}")
    
    def display_teaching_advice(self, teaching_advice):
        """显示教学建议"""
        try:
            # 处理总结
            summary = teaching_advice.get('summary', '')
            if summary:
                self.summary_label.setText(f"📊 {summary}")
            else:
                self.summary_label.setText("暂无总体分析内容")
            
            # 处理建议
            recommendations = teaching_advice.get('recommendations', [])
            if recommendations:
                recommendations_text = "🎯 针对性教学建议：\n\n"
                for i, rec in enumerate(recommendations, 1):
                    recommendations_text += f"{i}. {rec}\n\n"
                    
                self.recommendations_label.setText(recommendations_text)
            else:
                self.recommendations_label.setText("暂无具体的教学建议")
                
        except Exception as e:
            logger.error(f"显示教学建议失败: {e}")
            self.summary_label.setText(f"教学建议显示失败: {e}")
    
    def handle_control_command(self, command):
        """处理控制指令"""
        logger.info(f"批量批改结果页面收到控制指令: {command}")
        
        if command == '6-0-2':
            # 返回功能选择页面
            logger.info("从批量批改结果页面返回功能选择")
            self.back_requested.emit()
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理批量批改结果页面")
        self.analysis_result = None 