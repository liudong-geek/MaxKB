#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证 SQL 修复
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import QuerySet, CharField
from knowledge.models import Paragraph
from common.db.search import generate_sql_by_query_dict, get_dynamics_model
from common.util.file import get_file_content

def verify_sql_fix():
    """验证 SQL 修复"""
    paragraph_id = '019bf8ea-9acd-7e83-91c9-6ce8e043a289'  # 使用错误信息中的 ID
    
    print("=== 验证 SQL 修复 ===")
    
    try:
        # 1. 检查 SQL 模板中的占位符数量
        sql_content = get_file_content(
            os.path.join(os.path.dirname(__file__), "apps", "common", 'sql', 'list_embedding_text.sql')
        )
        
        placeholders = []
        for placeholder in ['${problem}', '${paragraph}', '${paragraph_title}', '${paragraph_summary}']:
            if placeholder in sql_content:
                placeholders.append(placeholder)
        
        print(f"1. SQL 模板中的占位符: {placeholders}")
        print(f"   占位符数量: {len(placeholders)}")
        
        # 2. 检查 QuerySet 字典中的键
        queryset_dict = {
            'problem': QuerySet(get_dynamics_model({'paragraph_id': CharField()}, 'problem_paragraph_mapping')).filter(paragraph_id=paragraph_id),
            'paragraph': QuerySet(Paragraph).filter(id=paragraph_id),
            'paragraph_title': QuerySet(Paragraph).filter(id=paragraph_id),
            'paragraph_summary': QuerySet(Paragraph).filter(id=paragraph_id)
        }
        
        print(f"2. QuerySet 字典中的键: {list(queryset_dict.keys())}")
        print(f"   QuerySet 数量: {len(queryset_dict)}")
        
        # 3. 测试 SQL 和参数生成
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
        
        exec_sql, exec_params = generate_sql_by_query_dict(
            queryset_dict, 
            sql_content, 
            field_replace_dict, 
            with_table_name=True
        )
        
        print(f"3. 生成的 SQL 长度: {len(exec_sql)} 字符")
        print(f"   参数数量: {len(exec_params)}")
        print(f"   参数: {exec_params}")
        
        # 4. 统计 SQL 中的占位符数量
        placeholder_count = exec_sql.count('%s')
        print(f"   SQL 中的 %s 占位符数量: {placeholder_count}")
        
        # 5. 验证匹配
        if len(exec_params) == placeholder_count:
            print("✅ 参数数量与占位符数量匹配！")
        else:
            print(f"❌ 参数数量 ({len(exec_params)}) 与占位符数量 ({placeholder_count}) 不匹配")
        
        # 6. 检查 UNION 结构
        union_count = exec_sql.count("UNION")
        print(f"4. UNION 数量: {union_count} (应该是 3)")
        
        if union_count == 3:
            print("✅ UNION 结构正确！")
        else:
            print(f"❌ UNION 结构不正确，期望 3 个，实际 {union_count} 个")
        
        print("\n=== SQL 内容预览 ===")
        lines = exec_sql.split('\n')
        for i, line in enumerate(lines[:20]):  # 显示前20行
            print(f"{i+1:2d}: {line}")
        if len(lines) > 20:
            print(f"... (还有 {len(lines) - 20} 行)")
        
    except Exception as e:
        print(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_sql_fix()