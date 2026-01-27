#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接使用 SQL 检查表是否存在
"""

import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # 直接导入和配置
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': 'maxkb',
                    'USER': 'postgres',
                    'PASSWORD': 'postgres',
                    'HOST': 'localhost',
                    'PORT': '5432',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
            SECRET_KEY='dummy-key-for-check'
        )
    
    import django
    django.setup()
    
    from django.db import connection
    
    def check_table():
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
                print("表不存在，正在创建...")
                # 创建表
                cursor.execute("""
                    CREATE TABLE problem_paragraph_mapping (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        update_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        knowledge_id UUID NOT NULL,
                        document_id UUID NOT NULL,
                        problem_id UUID NOT NULL,
                        paragraph_id UUID NOT NULL
                    );
                """)
                print("✓ 创建表成功")
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_paragraph_id ON problem_paragraph_mapping(paragraph_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_problem_id ON problem_paragraph_mapping(problem_id);")
                print("✓ 创建索引成功")
            else:
                print("表已存在")
                # 检查字段
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'problem_paragraph_mapping';
                """)
                columns = [row[0] for row in cursor.fetchall()]
                print(f"字段: {columns}")
                
                if 'paragraph_id' not in columns:
                    print("❌ paragraph_id 字段不存在!")
                else:
                    print("✓ paragraph_id 字段存在")
    
    if __name__ == "__main__":
        check_table()
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()