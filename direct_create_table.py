#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接使用 SQL 创建 problem_paragraph_mapping 表
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def create_table_directly():
    """直接创建表"""
    try:
        with connection.cursor() as cursor:
            print("=== 创建 problem_paragraph_mapping 表 ===")
            
            # 删除表（如果存在）
            cursor.execute("DROP TABLE IF EXISTS problem_paragraph_mapping;")
            print("✓ 删除旧表（如果存在）")
            
            # 创建新表
            create_table_sql = """
                CREATE TABLE problem_paragraph_mapping (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
                    create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    update_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    knowledge_id UUID NOT NULL,
                    document_id UUID NOT NULL,
                    problem_id UUID NOT NULL,
                    paragraph_id UUID NOT NULL
                );
            """
            cursor.execute(create_table_sql)
            print("✓ 创建表成功")
            
            # 添加外键约束
            print("\n=== 添加外键约束 ===")
            try:
                cursor.execute("""
                    ALTER TABLE problem_paragraph_mapping 
                    ADD CONSTRAINT fk_problem_paragraph_knowledge 
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge(id);
                """)
                print("✓ knowledge_id 外键约束添加成功")
            except Exception as e:
                print(f"knowledge_id 外键约束添加失败（可能已存在）: {e}")
            
            try:
                cursor.execute("""
                    ALTER TABLE problem_paragraph_mapping 
                    ADD CONSTRAINT fk_problem_paragraph_document 
                    FOREIGN KEY (document_id) REFERENCES document(id);
                """)
                print("✓ document_id 外键约束添加成功")
            except Exception as e:
                print(f"document_id 外键约束添加失败（可能已存在）: {e}")
            
            try:
                cursor.execute("""
                    ALTER TABLE problem_paragraph_mapping 
                    ADD CONSTRAINT fk_problem_paragraph_problem 
                    FOREIGN KEY (problem_id) REFERENCES problem(id);
                """)
                print("✓ problem_id 外键约束添加成功")
            except Exception as e:
                print(f"problem_id 外键约束添加失败（可能已存在）: {e}")
            
            try:
                cursor.execute("""
                    ALTER TABLE problem_paragraph_mapping 
                    ADD CONSTRAINT fk_problem_paragraph_paragraph 
                    FOREIGN KEY (paragraph_id) REFERENCES paragraph(id);
                """)
                print("✓ paragraph_id 外键约束添加成功")
            except Exception as e:
                print(f"paragraph_id 外键约束添加失败（可能已存在）: {e}")
            
            # 创建索引
            print("\n=== 创建索引 ===")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_paragraph_id ON problem_paragraph_mapping(paragraph_id);",
                "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_problem_id ON problem_paragraph_mapping(problem_id);",
                "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_knowledge_id ON problem_paragraph_mapping(knowledge_id);",
                "CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_document_id ON problem_paragraph_mapping(document_id);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                print(f"✓ 创建索引成功")
            
            # 验证表结构
            print("\n=== 验证表结构 ===")
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'problem_paragraph_mapping'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            for column in columns:
                print(f"  {column[0]}: {column[1]}")
            
            print("\n✓ problem_paragraph_mapping 表创建完成！")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_table_directly()