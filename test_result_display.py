#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果展示页面测试脚本
用于单独测试ResultDisplayWidget的布局效果
"""

import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 导入结果展示组件
from result_display import ResultDisplayWidget

class TestMainWindow(QMainWindow):
    """测试主窗口"""
    
    def __init__(self):
        super().__init__()
        self.result_widget = None
        self.setup_ui()
        self.load_test_data()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("结果展示页面测试")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 加载测试数据按钮
        load_button = QPushButton("加载测试数据")
        load_button.setFont(QFont("Microsoft YaHei", 12))
        load_button.clicked.connect(self.load_test_data)
        button_layout.addWidget(load_button)
        
        # 重载页面按钮
        reload_button = QPushButton("重载页面")
        reload_button.setFont(QFont("Microsoft YaHei", 12))
        reload_button.clicked.connect(self.reload_widget)
        button_layout.addWidget(reload_button)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 创建结果展示组件
        self.result_widget = ResultDisplayWidget(embedded=True)
        main_layout.addWidget(self.result_widget)
        
        central_widget.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
    
    def load_test_data(self):
        """加载测试数据"""
        # 尝试从result.json文件加载数据
        test_data = None
        
        if os.path.exists("result.json"):
            try:
                with open("result.json", "r", encoding="utf-8") as f:
                    test_data = json.load(f)
                print("✅ 成功加载result.json文件")
            except Exception as e:
                print(f"❌ 加载result.json失败: {e}")
        
        # 如果没有文件或加载失败，使用默认测试数据
        if not test_data:
            test_data = self.get_default_test_data()
            print("✅ 使用默认测试数据")
        
        # 显示数据
        if self.result_widget:
            self.result_widget.display_result(test_data)
    
    def get_default_test_data(self):
        """获取默认测试数据"""
        return {
            "mode": "school",
            "student_info": {
                "name": "张三",
                "class": "三年级一班"
            },
            "upload_result": {
                "error_numbers": [1, 3, 5, 7],
                "weak_areas": ["加减法运算", "分数概念", "应用题理解"],
                "analysis_content": """====================思考过程====================
让我分析一下这份数学作业的情况：

第1题：计算 25 + 37 = ?
学生答案：52
正确答案：62
错误原因：进位计算错误，5+7=12，但学生写成了2，没有正确进位

第3题：分数比较 3/4 和 2/3 的大小
学生答案：2/3 > 3/4
正确答案：3/4 > 2/3
错误原因：对分数大小比较方法掌握不够，需要通分或转换为小数比较

第5题：应用题 - 小明有24个苹果，分给6个同学，每人分几个？
学生答案：4个
正确答案：4个
这题做对了，除法运算掌握良好

第7题：计算 100 - 67 = ?
学生答案：43
正确答案：33
错误原因：退位减法计算错误

所以这次作业中，学生在基础运算（加减法）和分数概念方面需要加强练习。

====================模型回复====================
根据分析，建议重点练习：
1. 加减法进位和退位运算
2. 分数大小比较方法
3. 多做类似的练习题巩固
"""
            }
        }
    
    def reload_widget(self):
        """重载页面"""
        # 移除旧的组件
        if self.result_widget:
            self.result_widget.setParent(None)
        
        # 创建新的组件
        self.result_widget = ResultDisplayWidget(embedded=True)
        
        # 重新添加到布局
        layout = self.centralWidget().layout()
        layout.addWidget(self.result_widget)
        
        # 重新加载数据
        self.load_test_data()
        
        print("✅ 页面已重载")

def create_sample_json():
    """创建示例result.json文件"""
    sample_data = {
        "mode": "home",
        "student_info": {
            "name": "李四",
            "class": "四年级二班"
        },
        "upload_result": {
            "error_numbers": [2, 4, 6],
            "weak_areas": ["乘法口诀", "几何图形", "单位换算"],
            "analysis_content": """====================思考过程====================
这是一份数学练习的详细分析：

第2题：计算 7 × 8 = ?
学生答案：54
正确答案：56
错误原因：乘法口诀记忆不够熟练，七八五十六记成了五十四

第4题：计算长方形面积，长5cm，宽3cm
学生答案：8平方厘米
正确答案：15平方厘米
错误原因：面积公式掌握不够，用了周长公式

第6题：1米 = ? 厘米
学生答案：10厘米
正确答案：100厘米
错误原因：长度单位换算不熟练

总的来说，学生需要加强基础概念的理解和记忆。

====================模型回复====================
建议加强练习：
1. 乘法口诀表的背诵和应用
2. 几何图形面积和周长公式的区别
3. 常用单位换算的记忆
"""
        }
    }
    
    try:
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        print("✅ 已创建示例result.json文件")
    except Exception as e:
        print(f"❌ 创建result.json失败: {e}")

def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("结果展示页面测试")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 检查是否存在result.json，如果不存在就创建示例
    if not os.path.exists("result.json"):
        print("📝 result.json文件不存在，正在创建示例文件...")
        create_sample_json()
    
    # 创建主窗口
    main_window = TestMainWindow()
    main_window.show()
    
    print("🚀 测试应用程序已启动")
    print("💡 使用说明：")
    print("   - 点击'加载测试数据'按钮重新加载数据")
    print("   - 点击'重载页面'按钮重新创建页面组件")
    print("   - 可以编辑result.json文件来测试不同的数据")
    
    # 运行应用程序
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ 应用程序运行错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 