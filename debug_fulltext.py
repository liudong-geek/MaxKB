# coding=utf-8
"""
诊断脚本：测试全文搜索是否正常工作
运行方式: python apps/manage.py shell < debug_fulltext.py
"""
import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from common.utils.ts_vecto_util import to_ts_vector, to_query
from common.db.sql_execute import select_list

# 测试查询词
test_query = "项目状态"
print(f"测试查询: {test_query}")

# 1. 测试 to_query 分词
query_result = to_query(test_query)
print(f"to_query 分词结果: '{query_result}'")

# 2. 测试 plainto_tsquery 在数据库中的行为
sql = "SELECT plainto_tsquery('simple', %s) as tsquery"
result = select_list(sql, [query_result])
print(f"plainto_tsquery 结果: {result}")

# 3. 检查 embedding 表中的 search_vector 样本
sql = """
SELECT id, LEFT(search_vector::text, 100) as search_vector_sample
FROM embedding 
WHERE knowledge_id = (SELECT id FROM knowledge LIMIT 1)
LIMIT 3
"""
result = select_list(sql, [])
print(f"search_vector 样本:")
for row in result:
    print(f"  ID: {row['id']}, search_vector: {row['search_vector_sample']}")

# 4. 测试匹配
sql = """
SELECT COUNT(*) as match_count
FROM embedding 
WHERE knowledge_id = (SELECT id FROM knowledge LIMIT 1)
  AND search_vector @@ plainto_tsquery('simple', %s)
"""
result = select_list(sql, [query_result])
print(f"匹配的记录数: {result[0]['match_count'] if result else 0}")

# 5. 测试 ts_rank_cd
sql = """
SELECT id, ts_rank_cd(search_vector, plainto_tsquery('simple', %s), 32) as rank
FROM embedding 
WHERE knowledge_id = (SELECT id FROM knowledge LIMIT 1)
ORDER BY rank DESC
LIMIT 5
"""
result = select_list(sql, [query_result])
print(f"ts_rank_cd 排名:")
for row in result:
    print(f"  ID: {row['id']}, rank: {row['rank']}")
