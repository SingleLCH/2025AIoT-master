# -*- coding: utf-8 -*-
"""
数据库处理模块
用于管理MySQL数据库连接和数据操作
"""

import pymysql
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import DATABASE_CONFIG, DATABASE_TABLES

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseHandler:
    """数据库处理器"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=DATABASE_CONFIG['host'],
                port=DATABASE_CONFIG['port'],
                user=DATABASE_CONFIG['user'],
                password=DATABASE_CONFIG['password'],
                charset=DATABASE_CONFIG['charset'],
                autocommit=True
            )
            logger.info("数据库连接成功")
            self._ensure_databases_exist()
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def _ensure_databases_exist(self):
        """确保数据库和表存在"""
        try:
            cursor = self.connection.cursor()
            
            # 创建student_info数据库和student表
            school_config = DATABASE_TABLES['school_mode']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {school_config['database']}")
            cursor.execute(f"USE {school_config['database']}")
            
            # 创建student表
            columns_def = []
            for col_name, col_type in school_config['columns'].items():
                columns_def.append(f"{col_name} {col_type}")
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {school_config['table']} (
                {', '.join(columns_def)}
            )
            """
            cursor.execute(create_table_sql)
            logger.info(f"确保表 {school_config['database']}.{school_config['table']} 存在")
            
            # 创建error数据库和error_details表
            home_config = DATABASE_TABLES['home_mode']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {home_config['database']}")
            cursor.execute(f"USE {home_config['database']}")
            
            # 创建error_details表
            columns_def = []
            for col_name, col_type in home_config['columns'].items():
                columns_def.append(f"{col_name} {col_type}")
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {home_config['table']} (
                {', '.join(columns_def)}
            )
            """
            cursor.execute(create_table_sql)
            logger.info(f"确保表 {home_config['database']}.{home_config['table']} 存在")
            
            # 创建data_info数据库和studentinfo表（批量批改）
            batch_config = DATABASE_TABLES['batch_homework']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {batch_config['database']}")
            cursor.execute(f"USE {batch_config['database']}")
            
            # 创建studentinfo表
            columns_def = []
            for col_name, col_type in batch_config['columns'].items():
                columns_def.append(f"{col_name} {col_type}")
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {batch_config['table']} (
                {', '.join(columns_def)}
            )
            """
            cursor.execute(create_table_sql)
            logger.info(f"确保表 {batch_config['database']}.{batch_config['table']} 存在")
            
            # 创建data_info数据库的book表（图书管理）
            book_config = DATABASE_TABLES['book_management']
            # book_management也使用data_info数据库，所以不需要重复创建数据库
            cursor.execute(f"USE {book_config['database']}")
            
            # 创建book表
            columns_def = []
            for col_name, col_type in book_config['columns'].items():
                columns_def.append(f"{col_name} {col_type}")
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {book_config['table']} (
                {', '.join(columns_def)}
            )
            """
            cursor.execute(create_table_sql)
            logger.info(f"确保表 {book_config['database']}.{book_config['table']} 存在")
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"创建数据库和表失败: {e}")
            raise
    
    def save_school_result(self, student_name: str, weak_areas: List[str], 
                          gender: str = "", teacher: str = "") -> bool:
        """
        保存学校模式的结果到student表
        
        Args:
            student_name: 学生姓名（来自人脸识别）
            weak_areas: 薄弱知识点列表
            gender: 性别
            teacher: 教师姓名
            
        Returns:
            是否保存成功
        """
        try:
            cursor = self.connection.cursor()
            config = DATABASE_TABLES['school_mode']
            
            # 使用对应的数据库
            cursor.execute(f"USE {config['database']}")
            student_name = student_name.replace(".jpg", "")
            # 读取原有 subject 字段内容
            check_sql = f"SELECT subject FROM {config['table']} WHERE name = %s"
            cursor.execute(check_sql, (student_name,))
            existing = cursor.fetchone()
            
            # 新内容处理
            subject_str = "\n".join(weak_areas)
            
            if existing:
                # 追加到原有内容
                old_subject = existing[0] or ""
                if old_subject:
                    # 若原内容为json，先转为字符串
                    try:
                        old_list = json.loads(old_subject)
                        if isinstance(old_list, list):
                            old_subject = "\n".join(old_list)
                    except Exception:
                        pass
                    subject_str = old_subject + "\n" + subject_str if old_subject else subject_str
                update_sql = f"""
                UPDATE {config['table']} 
                SET subject = %s
                WHERE name = %s
                """
                cursor.execute(update_sql, (subject_str, student_name))
            else:
                insert_sql = f"""
                INSERT INTO {config['table']} (name, gender, subject, teacher)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (student_name, gender, subject_str, teacher))
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"保存学校模式结果失败: {e}")
            return False
    
    def save_home_result(self, error_numbers: List[int], weak_areas: List[str]) -> bool:
        """
        保存家庭模式的结果到error_details表
        
        Args:
            error_numbers: 错误题号列表
            weak_areas: 薄弱知识点列表
            
        Returns:
            是否保存成功
        """
        try:
            cursor = self.connection.cursor()
            config = DATABASE_TABLES['home_mode']
            
            # 使用对应的数据库
            cursor.execute(f"USE {config['database']}")
            
            # 将列表转换为JSON字符串
            error_json = json.dumps(error_numbers, ensure_ascii=False)
            details_json = json.dumps(weak_areas, ensure_ascii=False)
            
            # 插入新记录
            insert_sql = f"""
            INSERT INTO {config['table']} (time, error, details)
            VALUES (%s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_sql, (current_time, error_json, details_json))
            
            logger.info(f"保存家庭模式结果: 错误题号{error_numbers}, 薄弱知识点{weak_areas}")
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"保存家庭模式结果失败: {e}")
            return False
    
    def get_student_info(self, student_name: str) -> Optional[Dict[str, Any]]:
        """
        获取学生信息
        
        Args:
            student_name: 学生姓名
            
        Returns:
            学生信息字典或None
        """
        try:
            cursor = self.connection.cursor()
            config = DATABASE_TABLES['school_mode']
            
            cursor.execute(f"USE {config['database']}")
            
            select_sql = f"""
            SELECT id, name, gender, subject, teacher 
            FROM {config['table']} 
            WHERE name = %s
            """
            cursor.execute(select_sql, (student_name,))
            result = cursor.fetchone()
            
            if result:
                student_info = {
                    'id': result[0],
                    'name': result[1],
                    'gender': result[2],
                    'subject': json.loads(result[3]) if result[3] else [],
                    'teacher': result[4]
                }
                cursor.close()
                return student_info
            
            cursor.close()
            return None
            
        except Exception as e:
            logger.error(f"获取学生信息失败: {e}")
            return None
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的错误记录
        
        Args:
            limit: 获取记录数量限制
            
        Returns:
            错误记录列表
        """
        try:
            cursor = self.connection.cursor()
            config = DATABASE_TABLES['home_mode']
            
            cursor.execute(f"USE {config['database']}")
            
            select_sql = f"""
            SELECT id, time, error, details 
            FROM {config['table']} 
            ORDER BY time DESC 
            LIMIT %s
            """
            cursor.execute(select_sql, (limit,))
            results = cursor.fetchall()
            
            error_records = []
            for result in results:
                record = {
                    'id': result[0],
                    'time': result[1],
                    'error_numbers': json.loads(result[2]) if result[2] else [],
                    'weak_areas': json.loads(result[3]) if result[3] else []
                }
                error_records.append(record)
            
            cursor.close()
            return error_records
            
        except Exception as e:
            logger.error(f"获取错误记录失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            try:
                # 检查连接是否仍然打开
                if hasattr(self.connection, 'open') and self.connection.open:
                    self.connection.close()
                    logger.info("数据库连接已关闭")
                else:
                    logger.info("数据库连接已经关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接时出现异常: {e}")
            finally:
                self.connection = None
    
    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except Exception as e:
            logger.warning(f"析构函数执行时出现异常: {e}") 