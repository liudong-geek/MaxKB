#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试查询修复
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

def test_query_fix():
    """测试查询修复"""
    try:
        import django
        django.setup()
        
        from common.db.search import get_dynamics_model, generate_sql_by_query_dict
        from django.db.models import QuerySet
        import django.db.models
        
        # 模拟 listener_manage.py 中的查询
        paragraph_id = '019bf8ea-test-paragraph-id'
        
        queryset_dict = {
            'problem': QuerySet(get_dynamics_model({'paragraph_id': django.db.models.CharField()}, 'problem_paragraph_mapping')).filter(
                paragraph_id=paragraph_id),
            'paragraph': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id),
            'paragraph_title': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id),
            'paragraph_summary': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id)
        }
        
        # 读取SQL模板
        sql_file = os.path.join("apps", "common", "sql", "list_embedding_text.sql")
        with open(sql_file, 'r', encoding='utf-8') as f:
            select_string = f.read()
        
        field_replace_dict = {
            'paragraph': {
                'paragraph_id': 'paragraph.id'
            },
            'paragraph_title': {
                'paragraph_id': 'paragraph.id'
            },
            'paragraph_summary': {
                'paragraph_id': 'paragraph.id'
            }
        }
        
        print("=== 测试 SQL 生成 ===")
        print("SQL 模板:")
        print(select_string[:200] + "...")
        
        # 测试 without with_table_name (should fail)
        try:
            print("\n--- 测试 with_table_name=False ---")
            sql, params = generate_sql_by_query_dict(queryset_dict, select_string, field_replace_dict, with_table_name=False)
            print(f"生成的 SQL (前100字符): {sql[:100]}")
            print(f"参数数量: {len(params)}")
        except Exception as e:
            print(f"with_table_name=False 出错: {e}")
        
        # 测试 with with_table_name (should work)
        try:
            print("\n--- 测试 with_table_name=True ---")
            sql, params = generate_sql_by_query_dict(queryset_dict, select_string, field_replace_dict, with_table_name=True)
            print(f"生成的完整 SQL:")
            print(sql)
            print(f"\n参数: {params}")
            print(f"参数数量: {len(params)}")
            
            # 检查 WHERE 子句
            if "WHERE" in sql:
                print("\n✓ 发现 WHERE 子句")
                # 提取 WHERE 部分进行验证
                lines = sql.split('\n')
                for i, line in enumerate(lines):
                    if 'WHERE' in line:
                        print(f"WHERE 子句在第 {i+1} 行: {line.strip()}")
                        # 显示更多上下文
                        for j in range(max(0, i-2), min(len(lines), i+3)):
                            prefix = ">>> " if j == i else "    "
                            print(f"{prefix}{j+1}: {lines[j].strip()}")
                        break
            else:
                print("\n❌ 未发现 WHERE 子句")
            
            print("\n✓ with_table_name=True 成功生成 SQL")
        except Exception as e:
            print(f"with_table_name=True 出错: {e}")
            
    except Exception as e:
        print(f"测试错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_query_fix()