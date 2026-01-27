#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调试 problem 查询的 SQL 生成
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import models
from django.db.models import QuerySet
from common.db.search import compiler_queryset, get_dynamics_model
from common.util.file import get_file_content

def debug_problem_query():
    """调试 problem 查询生成"""
    paragraph_id = '019bf8d1-0000-0000-0000-000000000001'  # 示例 ID
    
    print("=== 调试 Problem QuerySet 生成 ===")
    
    # 当前的动态模型创建方式
    dynamic_model = get_dynamics_model({'paragraph.id': models.CharField()})
    print(f"动态模型创建成功: {dynamic_model}")
    
    # 创建 QuerySet
    problem_queryset = QuerySet(dynamic_model).filter(**{'paragraph.id': paragraph_id})
    print(f"Problem QuerySet 创建成功: {problem_queryset}")
    
    # 编译 SQL
    try:
        sql, params = compiler_queryset(
            problem_queryset, 
            {'paragraph.id': 'problem_paragraph_mapping.paragraph_id'}, 
            with_table_name=True
        )
        print(f"生成的 SQL: {sql}")
        print(f"参数: {params}")
    except Exception as e:
        print(f"编译 SQL 时出错: {e}")
    
    print("\n=== 尝试不同的字段定义 ===")
    
    # 尝试使用正确的表名和字段名
    try:
        # 直接指定表名
        dynamic_model2 = get_dynamics_model({'paragraph_id': models.CharField()}, 'problem_paragraph_mapping')
        problem_queryset2 = QuerySet(dynamic_model2).filter(paragraph_id=paragraph_id)
        
        sql2, params2 = compiler_queryset(
            problem_queryset2, 
            None, 
            with_table_name=True
        )
        print(f"方法2生成的 SQL: {sql2}")
        print(f"方法2参数: {params2}")
    except Exception as e:
        print(f"方法2出错: {e}")

if __name__ == "__main__":
    debug_problem_query()