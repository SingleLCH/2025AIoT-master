#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PPT数据库操作模块
用于读取最新的PPT内容进行总结
"""

import os
import logging
import pymysql
from datetime import datetime
from typing import Optional, Dict, Any
import threading

logger = logging.getLogger(__name__)

class PPTDatabase:
    """PPT数据库操作类"""
    
    def __init__(self):
        # 数据库连接配置 - 从环境变量获取
        self.db_config = {
            'host': os.environ.get('DATABASE_HOST', 'localhost'),
            'port': int(os.environ.get('DATABASE_PORT', 3306)),
            'database': 'data_info',
            'user': os.environ.get('DATABASE_USER', 'root'),
            'password': os.environ.get('DATABASE_PASSWORD', ''),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        
        # 线程锁，确保数据库操作的线程安全
        self._lock = threading.Lock()
        
        logger.info("📊 PPT数据库操作模块初始化完成")
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info("🔍 测试PPT数据库连接...")
            
            connection = pymysql.connect(**self.db_config)
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            connection.close()
            
            if result:
                logger.info("✅ PPT数据库连接测试成功")
                return True
            else:
                logger.warning("⚠️ PPT数据库连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ PPT数据库连接测试异常: {e}")
            return False
    
    def get_latest_ppt_content(self) -> Optional[str]:
        """
        获取最新的PPT内容
        
        Returns:
            str: 最新的PPT内容，失败时返回None
        """
        with self._lock:  # 确保线程安全
            try:
                logger.info("📖 获取最新的PPT内容...")
                
                # 建立数据库连接
                connection = pymysql.connect(**self.db_config)
                
                try:
                    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                        # 查询最新的PPT记录
                        sql = """
                        SELECT data, time 
                        FROM ppt 
                        ORDER BY time DESC 
                        LIMIT 1
                        """
                        
                        cursor.execute(sql)
                        result = cursor.fetchone()
                        
                        if result:
                            ppt_content = result['data']
                            ppt_time = result['time']
                            
                            logger.info(f"✅ 成功获取最新PPT内容，时间: {ppt_time}，长度: {len(ppt_content)} 字符")
                            return ppt_content
                        else:
                            logger.warning("⚠️ 未找到PPT记录")
                            return None
                            
                finally:
                    connection.close()
                    
            except Exception as e:
                logger.error(f"❌ 获取PPT内容异常: {e}")
                return None
    
    def get_recent_ppt_contents(self, limit: int = 5) -> Optional[list]:
        """
        获取最近的PPT内容记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            list: PPT记录列表，失败时返回None
        """
        try:
            logger.info(f"📖 获取最近的{limit}条PPT记录...")
            
            connection = pymysql.connect(**self.db_config)
            
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    sql = """
                    SELECT data, time 
                    FROM ppt 
                    ORDER BY time DESC 
                    LIMIT %s
                    """
                    
                    cursor.execute(sql, (limit,))
                    results = cursor.fetchall()
                    
                    logger.info(f"✅ 成功获取{len(results)}条PPT记录")
                    return results
                    
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"❌ 获取PPT记录异常: {e}")
            return None
    
    def check_ppt_table_exists(self) -> bool:
        """
        检查PPT表是否存在
        
        Returns:
            bool: 表是否存在
        """
        try:
            logger.info("🔧 检查PPT表是否存在...")
            
            connection = pymysql.connect(**self.db_config)
            
            try:
                with connection.cursor() as cursor:
                    # 检查表是否存在
                    sql = """
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                    AND table_name = 'ppt'
                    """
                    
                    cursor.execute(sql, (self.db_config['database'],))
                    result = cursor.fetchone()
                    
                    exists = result[0] > 0
                    
                    if exists:
                        logger.info("✅ PPT表存在")
                    else:
                        logger.warning("⚠️ PPT表不存在")
                    
                    return exists
                    
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"❌ 检查PPT表异常: {e}")
            return False

# 全局实例
_ppt_database_instance = None

def get_ppt_database() -> PPTDatabase:
    """获取PPT数据库操作实例"""
    global _ppt_database_instance
    
    if _ppt_database_instance is None:
        _ppt_database_instance = PPTDatabase()
    
    return _ppt_database_instance

def get_latest_ppt_content() -> Optional[str]:
    """
    获取最新PPT内容的便捷函数
    
    Returns:
        str: 最新的PPT内容
    """
    database = get_ppt_database()
    return database.get_latest_ppt_content()

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    database = get_ppt_database()
    
    # 测试连接
    if database.test_connection():
        print("✅ PPT数据库连接正常")
        
        # 检查表是否存在
        if database.check_ppt_table_exists():
            print("✅ PPT表存在")
            
            # 尝试获取最新内容
            content = database.get_latest_ppt_content()
            if content:
                print(f"✅ 获取到PPT内容: {content[:100]}...")
            else:
                print("⚠️ 没有找到PPT内容")
        else:
            print("❌ PPT表不存在")
    else:
        print("❌ PPT数据库连接失败")