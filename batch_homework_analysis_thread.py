# -*- coding: utf-8 -*-
"""
批量批改AI分析线程
专门用于在后台处理AI分析请求，避免阻塞UI线程导致Qt死亡
"""

from PyQt5.QtCore import QThread, pyqtSignal
import logging
import json
import glob
from typing import List, Optional

logger = logging.getLogger(__name__)


class BatchHomeworkAnalysisThread(QThread):
    """批量批改AI分析线程"""
    
    # 信号定义
    analysis_started = pyqtSignal()  # 分析开始
    analysis_progress = pyqtSignal(str)  # 分析进度更新
    analysis_completed = pyqtSignal(dict)  # 分析完成
    analysis_failed = pyqtSignal(str)  # 分析失败
    
    def __init__(self, photo_paths: List[str]):
        super().__init__()
        self.photo_paths = photo_paths
        self.analysis_result = None
    
    def run(self):
        """运行AI分析"""
        try:
            logger.info(f"AI分析线程开始运行，待分析照片数量: {len(self.photo_paths)}")
            
            # 发出开始信号
            self.analysis_started.emit()
            
            # 更新进度
            self.analysis_progress.emit(f"开始分析 {len(self.photo_paths)} 张照片...")
            
            # 调用home_work.py进行分析
            self.analysis_progress.emit("正在连接AI服务...")
            
            import home_work
            success = home_work.batch_analyze_homework(self.photo_paths)
            
            if success:
                self.analysis_progress.emit("AI分析完成，正在处理结果...")
                
                # 查找最新的分析结果文件
                result_file = self._find_latest_analysis_result()
                if result_file:
                    # 读取分析结果
                    with open(result_file, 'r', encoding='utf-8') as f:
                        self.analysis_result = json.load(f)
                    
                    self.analysis_progress.emit("结果处理完成")
                    logger.info("AI分析成功完成")
                    
                    # 发出完成信号
                    self.analysis_completed.emit(self.analysis_result)
                else:
                    error_msg = "未找到分析结果文件"
                    logger.error(error_msg)
                    self.analysis_failed.emit(error_msg)
            else:
                error_msg = "AI分析请求失败"
                logger.error(error_msg)
                self.analysis_failed.emit(error_msg)
                
        except Exception as e:
            error_msg = f"AI分析过程出错: {e}"
            logger.error(error_msg)
            self.analysis_failed.emit(error_msg)
    
    def _find_latest_analysis_result(self) -> Optional[str]:
        """查找最新的分析结果文件"""
        try:
            pattern = "homework_analysis_result_*.json"
            result_files = glob.glob(pattern)
            
            if not result_files:
                logger.warning("未找到任何分析结果文件")
                return None
            
            # 按修改时间排序，获取最新的
            latest_file = max(result_files, key=lambda f: os.path.getmtime(f))
            logger.info(f"找到最新的分析结果文件: {latest_file}")
            return latest_file
            
        except Exception as e:
            logger.error(f"查找分析结果文件失败: {e}")
            return None
    
    def stop_analysis(self):
        """停止分析（请求线程结束）"""
        logger.info("请求停止AI分析线程")
        self.requestInterruption()
        if self.isRunning():
            self.wait(3000)  # 等待3秒
            if self.isRunning():
                logger.warning("AI分析线程未能正常结束")
                self.terminate()  # 强制结束


# 导入os模块
import os 