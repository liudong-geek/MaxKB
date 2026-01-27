#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调试字段问题
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_field_issue():
    """调试字段映射问题"""
    print("=== 调试字段问题 ===")
    
    # 读取SQL模板
    sql_file = os.path.join("apps", "common", "sql", "list_embedding_text.sql")
    if os.path.exists(sql_file):
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("SQL模板内容:")
        print("=" * 50)
        print(sql_content)
        print("=" * 50)
        
        # 查找 WHERE 子句
        if "WHERE" in sql_content:
            print("\n找到 WHERE 子句:")
            lines = sql_content.split('\n')
            for i, line in enumerate(lines):
                if "WHERE" in line:
                    print(f"第 {i+1} 行: {line.strip()}")
                    # 显示前后几行
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        print(f"  {j+1}: {lines[j].strip()}")
    
    print("\n=== 问题分析 ===")
    print("1. SQL模板中的 WHERE 子句:")
    print('   WHERE "problem_paragraph_mapping.paragraph_id" = ...')
    print("")
    print("2. field_replace_dict 中的替换:")
    print('   将 paragraph_id 替换为 problem_paragraph_mapping.paragraph_id')
    print("")
    print("3. 可能的问题:")
    print("   - SQL模板中已经包含了完整字段名")
    print("   - field_replace_dict 可能造成重复替换")
    print("")
    print("4. 解决方案:")
    print("   移除 field_replace_dict 中的 problem 替换，因为SQL模板已经正确")

if __name__ == "__main__":
    debug_field_issue()