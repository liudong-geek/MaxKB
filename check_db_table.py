#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用项目的数据库配置检查表
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

def check_database_table():
    """检查数据库表"""
    try:
        import django
        django.setup()
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            print("=== 检查 problem_paragraph_mapping 表 ===")
            
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'problem_paragraph_mapping'
                );
            """)
            table_exists = cursor.fetchone()[0]
            print(f"表是否存在: {table_exists}")
            
            if not table_exists:
                print("正在创建表...")
                # 创建表
                create_sql = """
                    CREATE TABLE problem_paragraph_mapping (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        update_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        knowledge_id UUID NOT NULL,
                        document_id UUID NOT NULL,
                        problem_id UUID NOT NULL,
                        paragraph_id UUID NOT NULL
                    );
                """
                cursor.execute(create_sql)
                print("✓ 创建表成功")
                
                # 创建索引
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_paragraph_id ON problem_paragraph_mapping(paragraph_id);",
                    "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_problem_id ON problem_paragraph_mapping(problem_id);",
                    "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_knowledge_id ON problem_paragraph_mapping(knowledge_id);",
                    "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_document_id ON problem_paragraph_mapping(document_id);"
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                print("✓ 创建索引成功")
                
            else:
                print("表已存在，检查字段...")
                # 检查字段
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'problem_paragraph_mapping'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                print("表结构:")
                for column in columns:
                    print(f"  {column[0]}: {column[1]}")
                
                # 检查是否有 paragraph_id 字段
                has_paragraph_id = any(col[0] == 'paragraph_id' for col in columns)
                if not has_paragraph_id:
                    print("❌ 缺少 paragraph_id 字段，正在添加...")
                    cursor.execute("""
                        ALTER TABLE problem_paragraph_mapping 
                        ADD COLUMN paragraph_id UUID NOT NULL DEFAULT gen_random_uuid();
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_paragraph_id 
                        ON problem_paragraph_mapping(paragraph_id);
                    """)
                    print("✓ 添加 paragraph_id 字段成功")
                else:
                    print("✓ paragraph_id 字段存在")
            
            # 提交事务
            from django.db import transaction
            transaction.commit()
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_table()