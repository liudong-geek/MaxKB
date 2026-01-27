#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查 problem_paragraph_mapping 表是否存在
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def check_table_existence():
    """检查表是否存在"""
    try:
        with connection.cursor() as cursor:
            print("=== 检查 problem_paragraph_mapping 表是否存在 ===")
            
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'problem_paragraph_mapping'
                );
            """)
            table_exists = cursor.fetchone()[0]
            print(f"表是否存在: {table_exists}")
            
            if table_exists:
                # 检查表结构
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'problem_paragraph_mapping'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                print("\n=== 表结构 ===")
                for column in columns:
                    print(f"  {column[0]}: {column[1]}")
                
                # 检查是否有数据
                cursor.execute("SELECT COUNT(*) FROM problem_paragraph_mapping;")
                count = cursor.fetchone()[0]
                print(f"\n数据行数: {count}")
                
                # 如果有数据，查看几条示例
                if count > 0:
                    cursor.execute("SELECT * FROM problem_paragraph_mapping LIMIT 3;")
                    rows = cursor.fetchall()
                    print("\n=== 示例数据 ===")
                    for row in rows:
                        print(f"  {row}")
            
            # 检查 paragraph 表的结构
            print("\n=== 检查 paragraph 表结构 ===")
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'paragraph'
                ORDER BY ordinal_position;
            """)
            
            paragraph_columns = cursor.fetchall()
            for column in paragraph_columns:
                print(f"  {column[0]}: {column[1]}")
                
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_table_existence()