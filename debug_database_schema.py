#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调试数据库表结构
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def debug_database_schema():
    """调试数据库表结构"""
    try:
        with connection.cursor() as cursor:
            print("=== 检查所有相关表 ===")
            
            # 列出所有包含 problem 或 paragraph 的表
            cursor.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name LIKE '%problem%' OR table_name LIKE '%paragraph%')
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            for table in tables:
                print(f"  {table[0]} ({table[1]})")
            
            # 检查 problem_paragraph_mapping 表是否存在
            cursor.execute("""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_schema = 'public' 
                   AND table_name = 'problem_paragraph_mapping'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"\n=== problem_paragraph_mapping 表是否存在 ===")
            print(f"存在: {table_exists}")
            
            if table_exists:
                # 查看表结构
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'problem_paragraph_mapping'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                print(f"\n=== problem_paragraph_mapping 表结构 ===")
                for column in columns:
                    print(f"  {column[0]}: {column[1]} (nullable: {column[2]}, default: {column[3]})")
                
                # 尝试直接查询一个段落ID
                cursor.execute("""
                    SELECT COUNT(*) FROM problem_paragraph_mapping WHERE paragraph_id = %s
                """, ['019bf8d1-0000-0000-0000-000000000001'])
                
                count = cursor.fetchone()[0]
                print(f"\n=== 测试查询 ===")
                print(f"匹配的记录数: {count}")
            else:
                print("\n=== 尝试创建表 ===")
                print("表不存在，可能需要运行迁移来创建表")
                
                # 检查是否有待应用的迁移
                cursor.execute("""
                    SELECT app, name, applied 
                    FROM django_migrations 
                    WHERE app = 'knowledge' 
                    ORDER BY applied;
                """)
                
                migrations = cursor.fetchall()
                print(f"\n=== 已应用的知识库迁移 ===")
                for migration in migrations:
                    print(f"  {migration[0]}.{migration[1]} ({migration[2]})")
                
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    debug_database_schema()