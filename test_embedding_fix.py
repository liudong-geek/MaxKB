#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 embedding_by_paragraph 修复
验证参数匹配问题是否已解决
"""

import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.common.db.search import generate_sql_by_query_dict
from apps.common.utils.common import get_file_content

def test_sql_generation():
    """测试SQL生成和参数匹配"""
    print("=== 测试多字段向量化SQL生成 ===")
    
    # 读取SQL模板
    sql_file = os.path.join("apps", "common", "sql", "list_embedding_text.sql")
    select_string = get_file_content(sql_file)
    
    # 模拟查询字典（修复后的格式）
    from django.db.models import QuerySet, CharField
    from apps.knowledge.models import Paragraph
    from apps.common.db.search import get_dynamics_model
    import django.db.models
    
    paragraph_id = "test-paragraph-id"
    
    queryset_dict = {
        'problem': QuerySet(get_dynamics_model({'paragraph.id': CharField()})).filter(
            **{'paragraph.id': paragraph_id}),
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
    
    try:
        # 生成SQL和参数
        exec_sql, exec_params = generate_sql_by_query_dict(
            queryset_dict, select_string, field_replace_dict, with_table_name=False
        )
        
        print(f"✅ SQL生成成功!")
        print(f"📝 SQL长度: {len(exec_sql)} 字符")
        print(f"🔢 参数数量: {len(exec_params)} 个")
        print(f"🔍 占位符检查:")
        
        # 统计占位符数量
        placeholder_count = exec_sql.count('%s')
        param_count = len(exec_params)
        
        print(f"   - 占位符数量: {placeholder_count}")
        print(f"   - 参数数量: {param_count}")
        
        if placeholder_count == param_count:
            print("✅ 参数匹配正确!")
        else:
            print("❌ 参数不匹配!")
            return False
            
        # 显示前100个字符的SQL
        print(f"📄 SQL预览 (前100字符): {exec_sql[:100]}...")
        
        # 显示参数类型
        print(f"📋 参数详情:")
        for i, param in enumerate(exec_params[:5]):  # 只显示前5个参数
            print(f"   参数 {i+1}: {type(param).__name__} = {param}")
        if len(exec_params) > 5:
            print(f"   ... 还有 {len(exec_params) - 5} 个参数")
            
        return True
        
    except Exception as e:
        print(f"❌ SQL生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ 数据库连接正常: {result}")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试 embedding_by_paragraph 修复...")
    
    # 测试数据库连接
    if not test_connection():
        print("数据库连接失败，退出测试")
        sys.exit(1)
    
    # 测试SQL生成
    if test_sql_generation():
        print("\n🎉 所有测试通过! 修复成功!")
        sys.exit(0)
    else:
        print("\n💥 测试失败! 请检查修复!")
        sys.exit(1)