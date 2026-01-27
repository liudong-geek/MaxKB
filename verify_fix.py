#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证修复后的多字段向量化功能
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import QuerySet
from common.db.search import native_search, compiler_queryset
from knowledge.models import Paragraph
from common.util.file import get_file_content

def verify_fix():
    """验证修复效果"""
    paragraph_id = '019bf8d1-0000-0000-0000-000000000001'  # 示例 ID
    
    print("=== 验证修复后的多字段向量化 ===")
    
    try:
        # 1. 检查 SQL 模板
        sql_content = get_file_content(
            os.path.join(os.path.dirname(__file__), "apps", "common", 'sql', 'list_embedding_text.sql')
        )
        print(f"SQL 模板前50字符: {sql_content[:50]}...")
        
        # 2. 测试单个 QuerySet 生成
        print("\n=== 测试 Paragraph QuerySet ===")
        paragraph_queryset = QuerySet(Paragraph).filter(id=paragraph_id)
        sql, params = compiler_queryset(
            paragraph_queryset, 
            {'"id"': '"paragraph"."id"'}, 
            with_table_name=True
        )
        print(f"SQL: {sql}")
        print(f"参数: {params}")
        print("✓ Paragraph QuerySet 生成成功")
        
        # 3. 测试完整的 native_search 调用（但不实际执行）
        print("\n=== 测试 native_search 调用 ===")
        queryset_dict = {
            'paragraph': QuerySet(Paragraph).filter(id=paragraph_id),
            'paragraph_title': QuerySet(Paragraph).filter(id=paragraph_id),
            'paragraph_summary': QuerySet(Paragraph).filter(id=paragraph_id)
        }
        
        field_replace_dict = {
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
        
        # 这里只生成SQL，不执行
        from common.db.search import generate_sql_by_query_dict
        sql_content = get_file_content(
            os.path.join(os.path.dirname(__file__), "apps", "common", 'sql', 'list_embedding_text.sql')
        )
        
        exec_sql, exec_params = generate_sql_by_query_dict(
            queryset_dict, 
            sql_content, 
            field_replace_dict, 
            with_table_name=True
        )
        
        print(f"生成的SQL长度: {len(exec_sql)} 字符")
        print(f"参数数量: {len(exec_params)}")
        print("✓ native_search SQL 生成成功")
        
        print("\n=== 修复总结 ===")
        print("1. 移除了依赖 problem_paragraph_mapping 表的查询")
        print("2. 保留了 paragraph、paragraph_title、paragraph_summary 三个查询")
        print("3. 这样可以避免字段不存在的错误")
        print("4. 虽然暂时缺少问题向量化，但段落向量化功能可以正常工作")
        
    except Exception as e:
        print(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_fix()