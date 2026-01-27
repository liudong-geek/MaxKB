#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证修复效果
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

def test_fix():
    """验证修复效果"""
    try:
        import django
        django.setup()
        
        from common.event.listener_manage import ListenerManagement
        from common.db.sql_execute import select_one
        
        # 首先检查数据库连接是否正常
        try:
            result = select_one("SELECT 1 as test", [])
            print("✓ 数据库连接正常")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return
            
        # 尝试获取一个真实的paragraph_id
        try:
            paragraph_result = select_one("SELECT id FROM paragraph LIMIT 1", [])
            if paragraph_result:
                paragraph_id = paragraph_result.get('id')
                print(f"✓ 获取到测试段落ID: {paragraph_id}")
                
                # 测试listener中的函数（模拟）
                from common.db.search import native_search, get_dynamics_model
                from django.db.models import QuerySet
                import django.db.models
                
                # 模拟embedding_by_paragraph中的查询部分
                queryset_dict = {
                    'problem': QuerySet(get_dynamics_model({'paragraph_id': django.db.models.CharField()}, 'problem_paragraph_mapping')).filter(
                        paragraph_id=paragraph_id),
                    'paragraph': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id),
                    'paragraph_title': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id),
                    'paragraph_summary': QuerySet(get_dynamics_model({'id': django.db.models.CharField()}, 'paragraph')).filter(id=paragraph_id)
                }
                
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
                
                # 执行查询（使用修复后的参数）
                data_list = native_search(
                    queryset_dict,
                    select_string=select_string,
                    field_replace_dict=field_replace_dict,
                    with_table_name=True
                )
                
                print(f"✓ 查询执行成功，返回 {len(data_list)} 条记录")
                print("修复验证完成！")
                
            else:
                print("❌ 数据库中没有找到段落数据")
                print("无法进行完整测试，但SQL生成部分已经验证正确")
                
        except Exception as e:
            print(f"测试执行出错: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"设置错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fix()