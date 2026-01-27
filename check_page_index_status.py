# coding=utf-8
"""检查PageIndex配置和文档上传情况"""
import os
import sys

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

import django
django.setup()

from knowledge.models import Knowledge, Document, PageIndexNode
from config.page_index_config import PageIndexConfig

print("=" * 60)
print("PageIndex配置检查")
print("=" * 60)

# 1. 检查全局开关
print(f"\n1. 全局开关状态:")
print(f"   PageIndex全局启用: {PageIndexConfig.is_enabled()}")

# 2. 检查知识库
knowledge = Knowledge.objects.first()
if not knowledge:
    print("\n❌ 没有找到知识库")
    sys.exit(1)

print(f"\n2. 知识库信息:")
print(f"   知识库ID: {knowledge.id}")
print(f"   知识库名称: {knowledge.name}")
print(f"   知识库类型: {knowledge.type}")
print(f"   检索模式: {knowledge.meta.get('search_mode', 'traditional')}")
print(f"   Meta完整信息: {knowledge.meta}")

# 3. 检查文档
print(f"\n3. 文档信息:")
documents = Document.objects.filter(knowledge=knowledge)
print(f"   文档总数: {documents.count()}")

for doc in documents:
    print(f"\n   - 文档: {doc.name} (ID: {doc.id})")
    print(f"     状态: {doc.status}")

# 4. 检查PageIndex节点
print(f"\n4. PageIndex节点:")
page_index_nodes = PageIndexNode.objects.filter(knowledge_id=knowledge.id)
print(f"   PageIndex节点总数: {page_index_nodes.count()}")

if page_index_nodes.count() > 0:
    print(f"\n   PageIndex节点分布:")
    for node in page_index_nodes:
        print(f"   - {node.title} (Level: {node.level})")

# 5. 检查PageIndex构建是否被触发
print(f"\n5. PageIndex自动构建条件:")
print(f"   - 全局开关: {PageIndexConfig.is_enabled()}")
print(f"   - 知识库检索模式: {knowledge.meta.get('search_mode', 'traditional')}")
print(f"   - 文档数量: {documents.count()}")

print("\n" + "=" * 60)
print("建议:")
print("=" * 60)

if knowledge.meta.get('search_mode') != 'page_index':
    print("\n⚠ 知识库未设置为PageIndex检索模式")
    print("请在知识库设置页面切换到'PageIndex 模式'")
else:
    print("\n✅ 知识库已设置为PageIndex检索模式")

if page_index_nodes.count() == 0 and documents.count() > 0:
    print("\n⚠ PageIndex节点为空，但文档已上传")
    print("可能的原因:")
    print("1. 文档上传时PageIndex还未启用")
    print("2. 文档没有段落数据")
    print("3. PageIndex构建失败")
    print("\n解决方案:")
    print("1. 删除现有文档")
    print("2. 切换到PageIndex检索模式")
    print("3. 重新上传文档")
