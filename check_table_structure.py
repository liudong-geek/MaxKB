#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查 problem_paragraph_mapping 表结构
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def check_table_structure():
    """检查 problem_paragraph_mapping 表结构"""
    try:
        with connection.cursor() as cursor:
            # 查看表结构
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'problem_paragraph_mapping'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("=== problem_paragraph_mapping 表结构 ===")
            for column in columns:
                print(f"  {column[0]}: {column[1]}")
                
            # 查看 CREATE TABLE 语句
            cursor.execute("""
                SELECT 
                    pg_get_tabledef('problem_paragraph_mapping'::regclass, true)
            """)
            
            create_table = cursor.fetchone()[0]
            print("\n=== CREATE TABLE 语句 ===")
            print(create_table)
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    check_table_structure()