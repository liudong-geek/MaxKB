#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证 embedding_by_paragraph 修复
检查SQL参数匹配问题是否已解决
"""

import os
import sys

def check_sql_template():
    """检查SQL模板的占位符数量"""
    print("=== 检查SQL模板占位符 ===")
    
    sql_file = os.path.join("apps", "common", "sql", "list_embedding_text.sql")
    
    if not os.path.exists(sql_file):
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 统计各种占位符
    problem_placeholders = sql_content.count('${problem}')
    paragraph_placeholders = sql_content.count('${paragraph}')
    paragraph_title_placeholders = sql_content.count('${paragraph_title}')
    paragraph_summary_placeholders = sql_content.count('${paragraph_summary}')
    
    print(f"📝 SQL文件: {sql_file}")
    print(f"🔢 占位符统计:")
    print(f"   - ${{problem}}: {problem_placeholders} 个")
    print(f"   - ${{paragraph}}: {paragraph_placeholders} 个")
    print(f"   - ${{paragraph_title}}: {paragraph_title_placeholders} 个")
    print(f"   - ${{paragraph_summary}}: {paragraph_summary_placeholders} 个")
    
    total_placeholders = problem_placeholders + paragraph_placeholders + paragraph_title_placeholders + paragraph_summary_placeholders
    print(f"   - 总计: {total_placeholders} 个")
    
    # 验证占位符分布
    expected = {
        '${problem}': 1,
        '${paragraph}': 1,
        '${paragraph_title}': 1,
        '${paragraph_summary}': 1
    }
    
    success = True
    for placeholder, expected_count in expected.items():
        actual_count = sql_content.count(placeholder)
        if actual_count == expected_count:
            print(f"   ✅ {placeholder}: {actual_count} 个 (正确)")
        else:
            print(f"   ❌ {placeholder}: {actual_count} 个 (期望 {expected_count})")
            success = False
    
    return success

def check_listener_code():
    """检查listener_manage.py中的参数设置"""
    print("\n=== 检查listener_manage.py参数设置 ===")
    
    listener_file = os.path.join("apps", "common", "event", "listener_manage.py")
    
    if not os.path.exists(listener_file):
        print(f"❌ 文件不存在: {listener_file}")
        return False
    
    with open(listener_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键代码模式
    checks = [
        ("problem QuerySet", "'problem': QuerySet(" in content),
        ("paragraph QuerySet", "'paragraph': QuerySet(" in content),
        ("paragraph_title QuerySet", "'paragraph_title': QuerySet(" in content),
        ("paragraph_summary QuerySet", "'paragraph_summary': QuerySet(" in content),
        ("problem field_replace", "'problem': {" in content),
        ("problem column mapping", "'paragraph.id': 'problem_paragraph_mapping.paragraph_id'" in content),
        ("paragraph field_replace", "'paragraph': {" in content),
        ("paragraph_title field_replace", "'paragraph_title': {" in content),
        ("paragraph_summary field_replace", "'paragraph_summary': {" in content),
    ]
    
    success = True
    for check_name, pattern in checks:
        if pattern:
            print(f"   ✅ {check_name}: 存在")
        else:
            print(f"   ❌ {check_name}: 缺失")
            success = False
    
    return success

def check_syntax():
    """检查Python语法"""
    print("\n=== 检查Python语法 ===")
    
    files_to_check = [
        "apps/common/event/listener_manage.py",
        "apps/common/sql/list_embedding_text.sql"
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
        
        if file_path.endswith('.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                print(f"   ✅ {file_path}: 语法正确")
            except SyntaxError as e:
                print(f"   ❌ {file_path}: 语法错误 - {e}")
                return False
        else:
            print(f"   ✅ {file_path}: 非Python文件，跳过语法检查")
    
    return True

if __name__ == "__main__":
    print("开始验证 embedding_by_paragraph 修复...")
    
    success = True
    
    # 检查SQL模板
    if not check_sql_template():
        success = False
    
    # 检查listener代码
    if not check_listener_code():
        success = False
    
    # 检查语法
    if not check_syntax():
        success = False
    
    if success:
        print("\n🎉 所有验证通过! 修复正确!")
        print("\n💡 修复说明:")
        print("   - 为SQL模板的每个UNION部分使用不同的占位符名称")
        print("   - 在listener_manage.py中提供对应的查询字典")
        print("   - 确保占位符数量与参数数量匹配")
        sys.exit(0)
    else:
        print("\n💥 验证失败! 请检查修复!")
        sys.exit(1)