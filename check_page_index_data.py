# coding=utf-8
"""检查PageIndex数据"""
import os
import sys
import django

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import PageIndexNode, Knowledge

print("检查PageIndex数据...")

# 检查PageIndex节点总数
count = PageIndexNode.objects.count()
print(f"PageIndex节点总数: {count}")

# 检查各知识库的PageIndex数据
print("\n按知识库统计:")
for knowledge in Knowledge.objects.all():
    node_count = PageIndexNode.objects.filter(knowledge_id=knowledge.id).count()
    print(f"  - {knowledge.name}: {node_count} 节点")

if count == 0:
    print("\n❌ 无PageIndex数据，需要先构建PageIndex")
else:
    print("\n✅ PageIndex数据存在")
