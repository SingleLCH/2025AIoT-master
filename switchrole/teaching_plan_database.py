#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
教案数据库操作模块
用于保存教案内容到远程数据库
"""

import os
import logging
import pymysql
from datetime import datetime
from typing import Optional, Dict, Any
import threading

logger = logging.getLogger(__name__)

class TeachingPlanDatabase:
    """教案数据库操作类"""
    
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
        
        logger.info("📚 教案数据库操作模块初始化完成")
    
    def set_credentials(self, username: str, password: str):
        """
        设置数据库认证信息
        
        Args:
            username: 数据库用户名
            password: 数据库密码
        """
        self.db_config['user'] = username
        self.db_config['password'] = password
        logger.info(f"🔑 数据库认证信息已更新，用户名: {username}")
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info("🔍 测试数据库连接...")
            
            connection = pymysql.connect(**self.db_config)
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            connection.close()
            
            if result:
                logger.info("✅ 数据库连接测试成功")
                return True
            else:
                logger.warning("⚠️ 数据库连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 数据库连接测试异常: {e}")
            return False
    
    def save_teaching_plan(self, teaching_plan_content: str, topic: str = None) -> bool:
        """
        保存教案到数据库
        
        Args:
            teaching_plan_content: 教案内容
            topic: 教案主题（可选，用于日志记录）
            
        Returns:
            bool: 保存是否成功
        """
        with self._lock:  # 确保线程安全
            try:
                logger.info(f"💾 开始保存教案到数据库，主题: {topic or '未指定'}")
                
                # 建立数据库连接
                connection = pymysql.connect(**self.db_config)
                
                try:
                    with connection.cursor() as cursor:
                        # 准备SQL语句
                        sql = """
                        INSERT INTO jiaoan (details, time) 
                        VALUES (%s, %s)
                        """
                        
                        # 当前时间
                        current_time = datetime.now()
                        
                        # 执行SQL插入
                        cursor.execute(sql, (teaching_plan_content, current_time))
                        
                        # 获取插入的记录ID
                        inserted_id = cursor.lastrowid
                        
                        logger.info(f"✅ 教案保存成功，记录ID: {inserted_id}, 时间: {current_time}")
                        return True
                        
                except Exception as db_error:
                    logger.error(f"❌ 数据库操作异常: {db_error}")
                    connection.rollback()
                    return False
                    
                finally:
                    connection.close()
                    
            except Exception as e:
                logger.error(f"❌ 保存教案异常: {e}")
                return False
    
    def get_recent_teaching_plans(self, limit: int = 10) -> Optional[list]:
        """
        获取最近的教案记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            list: 教案记录列表，失败时返回None
        """
        try:
            logger.info(f"📖 获取最近的{limit}条教案记录...")
            
            connection = pymysql.connect(**self.db_config)
            
            try:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    sql = """
                    SELECT id, details, time 
                    FROM jiaoan 
                    ORDER BY time DESC 
                    LIMIT %s
                    """
                    
                    cursor.execute(sql, (limit,))
                    results = cursor.fetchall()
                    
                    logger.info(f"✅ 成功获取{len(results)}条教案记录")
                    return results
                    
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"❌ 获取教案记录异常: {e}")
            return None
    
    def create_table_if_not_exists(self) -> bool:
        """
        如果表不存在则创建教案表
        
        Returns:
            bool: 创建是否成功
        """
        try:
            logger.info("🔧 检查并创建教案表...")
            
            connection = pymysql.connect(**self.db_config)
            
            try:
                with connection.cursor() as cursor:
                    # 创建表的SQL语句
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS jiaoan (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        details TEXT NOT NULL COMMENT '教案内容',
                        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间'
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教案表'
                    """
                    
                    cursor.execute(create_table_sql)
                    
                    logger.info("✅ 教案表检查/创建完成")
                    return True
                    
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"❌ 创建教案表异常: {e}")
            return False

# 全局实例
_database_instance = None

def get_teaching_plan_database() -> TeachingPlanDatabase:
    """获取教案数据库操作实例"""
    global _database_instance
    
    if _database_instance is None:
        _database_instance = TeachingPlanDatabase()
    
    return _database_instance

def save_teaching_plan_to_db(content: str, topic: str = None) -> bool:
    """
    保存教案到数据库的便捷函数
    
    Args:
        content: 教案内容
        topic: 教案主题
        
    Returns:
        bool: 保存是否成功
    """
    database = get_teaching_plan_database()
    return database.save_teaching_plan(content, topic)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 需要设置实际的数据库用户名和密码
    database = get_teaching_plan_database()
    
    # 注意：需要设置正确的数据库认证信息
    # database.set_credentials("your_username", "your_password")
    
    # 测试连接
    if database.test_connection():
        print("✅ 数据库连接正常")
        
        # 尝试创建表
        if database.create_table_if_not_exists():
            print("✅ 教案表准备就绪")
        else:
            print("❌ 教案表准备失败")
    else:
        print("❌ 数据库连接失败")