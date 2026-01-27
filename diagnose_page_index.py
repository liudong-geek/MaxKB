# coding=utf-8
"""
PageIndex诊断脚本
用于诊断PageIndex未构建的问题
"""
import os
import sys

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
import django
django.setup()

from knowledge.models import Document, Knowledge, PageIndexNode, Paragraph
from config.page_index_config import PageIndexConfig
from knowledge.page_index import PageIndex


def diagnose():
    """诊断PageIndex构建问题"""
    print("=" * 60)
    print("PageIndex诊断工具")
    print("=" * 60)

    # 1. 检查全局开关
    print("\n【1】检查PageIndex全局开关")
    is_enabled = PageIndexConfig.is_enabled()
    print(f"PageIndex全局开关: {is_enabled}")
    if not is_enabled:
        print("❌ PageIndex未启用！请在 config/page_index_config.py 中设置 ENABLE_PAGE_INDEX = True")
        return

    # 2. 获取最近上传的文档
    print("\n【2】检查最近的文档")
    documents = list(Document.objects.all().order_by('-create_time')[:5])
    if not documents:
        print("❌ 没有找到文档")
        return

    print(f"找到 {len(documents)} 个最近文档:")
    for doc in documents:
        print(f"  - {doc.name} (ID: {doc.id}, Knowledge: {doc.knowledge.name})")

    # 3. 检查PageIndex数据
    print("\n【3】检查PageIndex数据")
    page_index_count = PageIndexNode.objects.count()
    print(f"PageIndex节点总数: {page_index_count}")

    if page_index_count > 0:
        print("\n按文档统计:")
        for doc in documents:
            count = PageIndexNode.objects.filter(document=doc).count()
            print(f"  - {doc.name}: {count} 节点")
    else:
        print("❌ PageIndex节点为空，需要构建")

    # 4. 尝试手动构建PageIndex
    print("\n【4】尝试手动构建PageIndex")
    for doc in documents[:1]:  # 只测试第一个文档
        print(f"\n测试文档: {doc.name} (ID: {doc.id})")

        # 检查段落数据
        paragraphs = Paragraph.objects.filter(
            document=doc,
            is_active=True
        ).order_by('position')

        print(f"  活跃段落数: {paragraphs.count()}")

        if paragraphs.count() == 0:
            print("  ❌ 文档没有活跃段落")
            continue

        # 检查段落内容
        sample_paras = paragraphs[:3]
        print("\n  前3个段落示例:")
        for i, para in enumerate(sample_paras, 1):
            content_preview = para.content[:100] + "..." if len(para.content) > 100 else para.content
            print(f"    {i}. Title: {para.title or '(无标题)'}")
            print(f"       Content: {content_preview}")

        # 检查是否包含标题
        has_title = False
        for para in paragraphs:
            if para.title and para.title.strip():
                has_title = True
                break

        print(f"\n  是否包含标题: {has_title}")

        if not has_title:
            print("  ⚠ 文档没有Markdown标题（#, ##, ###），PageIndex可能无法解析树结构")
            print("  建议：对于表格文件，PageIndex至少会创建根节点")

        # 尝试构建PageIndex
        try:
            print(f"\n  开始构建PageIndex...")
            knowledge = doc.knowledge

            # 清理旧数据
            PageIndexNode.objects.filter(document=doc).delete()

            # 构建PageIndex
            page_index = PageIndex.from_documents(
                documents=[doc],
                knowledge=knowledge,
                chunk_size=1000,
                chunk_overlap=200
            )

            # 获取统计信息
            stats = page_index.get_statistics()
            print(f"  ✅ PageIndex构建成功！")
            print(f"     - 总节点数: {stats['total_nodes']}")
            print(f"     - 最大深度: {stats['max_depth']}")
            print(f"     - 深度分布: {stats['depth_distribution']}")

            # 验证节点
            page_index_nodes = PageIndexNode.objects.filter(document=doc)
            print(f"\n  验证: 实际创建了 {page_index_nodes.count()} 个节点")

            for node in page_index_nodes[:5]:
                print(f"    - Level {node.level}: {node.title} (Path: {node.get_full_path()})")

        except Exception as e:
            print(f"  ❌ PageIndex构建失败: {e}")
            import traceback
            traceback.print_exc()

    # 5. 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    print(f"PageIndex全局开关: {'✅ 启用' if is_enabled else '❌ 未启用'}")
    print(f"PageIndex节点总数: {page_index_count}")

    if page_index_count == 0:
        print("\n建议：")
        print("1. 确认PageIndex全局开关已启用")
        print("2. 检查文档是否有标题（#, ##, ###）")
        print("3. 对于无标题文档，PageIndex会至少创建根节点")
        print("4. 重新上传文档或手动触发PageIndex构建")
    else:
        print("\n✅ PageIndex数据正常")


if __name__ == '__main__':
    diagnose()
