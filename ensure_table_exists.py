#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
确保 problem_paragraph_mapping 表存在，使用原始SQL
"""

import psycopg2
import psycopg2.extras

def ensure_table_exists():
    """确保表存在"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='maxkb',
            user='postgres',
            password='postgres'
        )
        
        with conn.cursor() as cursor:
            print("=== 检查并创建 problem_paragraph_mapping 表 ===")
            
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
                
                conn.commit()
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
                        ADD COLUMN paragraph_id UUID NOT NULL;
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_problem_paragraph_mapping_paragraph_id 
                        ON problem_paragraph_mapping(paragraph_id);
                    """)
                    conn.commit()
                    print("✓ 添加 paragraph_id 字段成功")
                else:
                    print("✓ paragraph_id 字段存在")
        
        conn.close()
        print("\n✓ 表检查完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ensure_table_exists()