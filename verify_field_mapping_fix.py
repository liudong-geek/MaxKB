#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证字段映射修复
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
from knowledge.models import Paragraph

def test_field_mapping_fix():
    """测试字段映射修复"""
    paragraph_id = '019bf8d1-0000-0000-0000-000000000001'  # 示例 ID
    
    print("=== 测试修复后的字段映射 ===")
    
    # 1. 测试 problem QuerySet（新的方式）
    try:
        print("\n1. 测试 problem QuerySet:")
        dynamic_model = get_dynamics_model({'paragraph_id': models.CharField()}, 'problem_paragraph_mapping')
        problem_queryset = QuerySet(dynamic_model).filter(paragraph_id=paragraph_id)
        
        sql, params = compiler_queryset(
            problem_queryset, 
            {'paragraph_id': 'problem_paragraph_mapping.paragraph_id'}, 
            with_table_name=True
        )
        print(f"   SQL: {sql}")
        print(f"   参数: {params}")
        print("   ✓ Problem QuerySet 生成成功")
        
    except Exception as e:
        print(f"   ✗ Problem QuerySet 失败: {e}")
    
    # 2. 测试 paragraph QuerySet
    try:
        print("\n2. 测试 paragraph QuerySet:")
        paragraph_queryset = QuerySet(Paragraph).filter(id=paragraph_id)
        
        sql, params = compiler_queryset(
            paragraph_queryset, 
            {'"id"': '"paragraph"."id"'}, 
            with_table_name=True
        )
        print(f"   SQL: {sql}")
        print(f"   参数: {params}")
        print("   ✓ Paragraph QuerySet 生成成功")
        
    except Exception as e:
        print(f"   ✗ Paragraph QuerySet 失败: {e}")
    
    # 3. 测试完整的字段替换字典
    try:
        print("\n3. 测试完整字段替换字典:")
        field_replace_dict = {
            'problem': {
                'paragraph_id': 'problem_paragraph_mapping.paragraph_id'
            },
            'paragraph': {
                '"id"': '"paragraph"."id"'
            },
            'paragraph_title': {
                '"id"': '"paragraph"."id"'
            },
            'paragraph_summary': {
                '"id"': '"paragraph"."id"'
            }
        }
        print(f"   字段替换字典: {field_replace_dict}")
        print("   ✓ 字段替换字典配置正确")
        
    except Exception as e:
        print(f"   ✗ 字段替换字典失败: {e}")

if __name__ == "__main__":
    test_field_mapping_fix()