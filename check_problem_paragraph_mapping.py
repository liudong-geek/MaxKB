#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查 problem_paragraph_mapping 表是否存在及其结构
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def check_problem_paragraph_mapping_table():
    """检查 problem_paragraph_mapping 表是否存在及其结构"""
    try:
        with connection.cursor() as cursor:
            # 1. 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_schema = 'public' 
                   AND table_name = 'problem_paragraph_mapping'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"=== problem_paragraph_mapping 表是否存在 ===")
            print(f"表存在: {table_exists}")
            
            if not table_exists:
                print("表不存在！这是问题的根源。")
                return
            
            # 2. 如果表存在，查看表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'problem_paragraph_mapping'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print(f"\n=== problem_paragraph_mapping 表结构 ===")
            for column in columns:
                print(f"  {column[0]}: {column[1]} (nullable: {column[2]})")
                
            # 3. 查看 problem 表是否存在
            cursor.execute("""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_schema = 'public' 
                   AND table_name = 'problem'
                );
            """)
            
            problem_table_exists = cursor.fetchone()[0]
            print(f"\n=== problem 表是否存在 ===")
            print(f"表存在: {problem_table_exists}")
            
            # 4. 列出所有相关表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%problem%' OR table_name LIKE '%paragraph%'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            print(f"\n=== 相关表列表 ===")
            for table in tables:
                print(f"  {table[0]}")
                
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    check_problem_paragraph_mapping_table()