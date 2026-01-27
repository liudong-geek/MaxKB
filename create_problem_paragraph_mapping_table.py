#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建 problem_paragraph_mapping 表
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from knowledge.models import ProblemParagraphMapping

def create_problem_paragraph_mapping_table():
    """创建 problem_paragraph_mapping 表"""
    try:
        with connection.cursor() as cursor:
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_schema = 'public' 
                   AND table_name = 'problem_paragraph_mapping'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"=== problem_paragraph_mapping 表是否存在 ===")
            print(f"存在: {table_exists}")
            
            if not table_exists:
                print("\n=== 创建 problem_paragraph_mapping 表 ===")
                
                # 使用 Django ORM 创建表
                from django.core.management import call_command
                try:
                    # 尝试创建表（如果模型已经定义但未迁移）
                    from django.db import connections
                    with connections['default'].schema_editor() as schema_editor:
                        schema_editor.create_model(ProblemParagraphMapping)
                    print("✓ 使用 Django ORM 创建表成功")
                except Exception as e:
                    print(f"Django ORM 创建失败: {e}")
                    
                    # 手动创建表
                    print("\n=== 手动创建表 ===")
                    cursor.execute("""
                        CREATE TABLE problem_paragraph_mapping (
                            id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
                            create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            update_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            knowledge_id UUID NOT NULL REFERENCES knowledge(id),
                            document_id UUID NOT NULL REFERENCES document(id),
                            problem_id UUID NOT NULL REFERENCES problem(id),
                            paragraph_id UUID NOT NULL REFERENCES paragraph(id)
                        );
                    """)
                    print("✓ 手动创建表成功")
                
                # 创建索引
                print("\n=== 创建索引 ===")
                indexes = [
                    "CREATE INDEX problem_paragraph_mapping_paragraph_id_idx ON problem_paragraph_mapping(paragraph_id);",
                    "CREATE INDEX problem_paragraph_mapping_problem_id_idx ON problem_paragraph_mapping(problem_id);",
                    "CREATE INDEX problem_paragraph_mapping_knowledge_id_idx ON problem_paragraph_mapping(knowledge_id);",
                    "CREATE INDEX problem_paragraph_mapping_document_id_idx ON problem_paragraph_mapping(document_id);"
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        print(f"✓ 创建索引成功")
                    except Exception as e:
                        print(f"创建索引失败（可能已存在）: {e}")
                
            else:
                print("表已存在，检查表结构...")
                
                # 检查表结构
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'problem_paragraph_mapping'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                print(f"\n=== 表结构 ===")
                for column in columns:
                    print(f"  {column[0]}: {column[1]} (nullable: {column[2]})")
            
            print("\n=== 验证表创建 ===")
            cursor.execute("SELECT COUNT(*) FROM problem_paragraph_mapping")
            count = cursor.fetchone()[0]
            print(f"表中记录数: {count}")
            
            print("\n✓ problem_paragraph_mapping 表准备完成")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_problem_paragraph_mapping_table()