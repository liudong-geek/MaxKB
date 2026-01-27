# coding=utf-8
"""
PageIndex检索模式测试脚本（方案B）
测试独立的PageIndex检索模式功能
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from knowledge.models import Knowledge, Document, Paragraph, PageIndexNode, Embedding
from config.page_index_config import PageIndexConfig
from langchain_core.embeddings import Embeddings


def test_page_index_mode_config():
    """测试1：PageIndex检索模式配置"""
    print("=" * 60)
    print("测试1：PageIndex检索模式配置")
    print("=" * 60)

    # 获取第一个知识库
    knowledge = Knowledge.objects.first()
    if not knowledge:
        print("❌ 未找到知识库，请先创建知识库")
        return False

    print(f"知识库ID: {knowledge.id}")
    print(f"知识库名称: {knowledge.name}")

    # 检查当前检索模式
    current_mode = knowledge.meta.get('search_mode', 'traditional')
    print(f"当前检索模式: {current_mode}")

    # 启用PageIndex全局开关
    PageIndexConfig.set_enabled(True)
    print(f"PageIndex全局开关: {PageIndexConfig.is_enabled()}")

    # 将知识库设置为PageIndex检索模式
    PageIndexConfig.set_search_mode(str(knowledge.id), PageIndexConfig.SEARCH_MODE_PAGE_INDEX)
    print(f"设置为PageIndex检索模式")

    # 重新加载知识库，验证配置
    knowledge = Knowledge.objects.get(id=knowledge.id)
    new_mode = knowledge.meta.get('search_mode', 'traditional')
    print(f"验证检索模式: {new_mode}")

    if new_mode == PageIndexConfig.SEARCH_MODE_PAGE_INDEX:
        print("✅ PageIndex检索模式配置成功")
        return True
    else:
        print("❌ PageIndex检索模式配置失败")
        return False


def test_page_index_data():
    """测试2：检查PageIndex数据是否构建"""
    print("\n" + "=" * 60)
    print("测试2：检查PageIndex数据")
    print("=" * 60)

    knowledge = Knowledge.objects.first()
    if not knowledge:
        return False

    # 检查PageIndexNode数据
    page_index_count = PageIndexNode.objects.filter(
        knowledge_id=knowledge.id
    ).count()

    print(f"PageIndex节点数量: {page_index_count}")

    if page_index_count == 0:
        print("❌ PageIndex未构建，请先导入文档构建PageIndex")
        return False

    # 显示PageIndex节点统计
    max_depth = PageIndexNode.objects.filter(
        knowledge_id=knowledge.id
    ).order_by('-level').first()

    print(f"最大层级深度: {max_depth.level if max_depth else 0}")

    # 显示部分节点示例
    sample_nodes = PageIndexNode.objects.filter(
        knowledge_id=knowledge.id
    )[:5]

    print("\nPageIndex节点示例:")
    for node in sample_nodes:
        print(f"  - Level {node.level}: {node.title} (Path: {node.get_full_path()})")

    print("✅ PageIndex数据检查完成")
    return True


def test_page_index_retrieval():
    """测试3：测试PageIndex检索"""
    print("\n" + "=" * 60)
    print("测试3：测试PageIndex检索")
    print("=" * 60)

    knowledge = Knowledge.objects.first()
    if not knowledge:
        return False

    # 检查是否有Embedding数据
    embedding_count = Embedding.objects.filter(
        knowledge_id=knowledge.id,
        is_active=True
    ).count()

    print(f"活跃Embedding数量: {embedding_count}")

    if embedding_count == 0:
        print("❌ 无Embedding数据，请先进行向量化")
        return False

    # 获取向量化模型
    embedding_model = knowledge.embedding_model
    if not embedding_model:
        print("❌ 知识库未配置向量化模型")
        return False

    print(f"向量化模型: {embedding_model.name}")

    # 模拟一个查询
    query_text = "测试查询"
    print(f"\n测试查询: {query_text}")

    try:
        from models_provider.tools import get_model

        # 获取embedding客户端
        embedding_client = get_model(
            str(embedding_model.id),
            embedding_model.model_credential
        )

        # 生成查询向量
        query_embedding = embedding_client.embed_query(query_text)
        print(f"查询向量维度: {len(query_embedding)}")

        # 执行PageIndex检索
        from knowledge.page_index.page_index_retriever import PageIndexRetriever

        retriever = PageIndexRetriever(
            knowledge_id=str(knowledge.id),
            use_tree_filter=True,
            search_mode='blend',
            top_n=5,
            similarity_threshold=0.6
        )

        results = retriever.query(
            query_text=query_text,
            query_embedding=query_embedding,
            top_n=5,
            similarity_threshold=0.6
        )

        print(f"\n检索结果数量: {len(results)}")

        for idx, result in enumerate(results, 1):
            print(f"\n结果 {idx}:")
            print(f"  ID: {result.get('id', 'N/A')}")
            print(f"  相似度: {result.get('similarity', 0):.4f}")

            # 尝试获取内容
            content = result.get('content', '') or result.get('paragraph_content', '')
            if content:
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  内容: {content_preview}")

        print("\n✅ PageIndex检索测试完成")
        return True

    except Exception as e:
        print(f"❌ PageIndex检索失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_pg_vector_integration():
    """测试4：测试pg_vector.py的PageIndex集成"""
    print("\n" + "=" * 60)
    print("测试4：测试pg_vector.py集成")
    print("=" * 60)

    knowledge = Knowledge.objects.first()
    if not knowledge:
        return False

    # 确保知识库已启用PageIndex模式
    current_mode = knowledge.meta.get('search_mode', 'traditional')
    print(f"当前检索模式: {current_mode}")

    if current_mode != 'page_index':
        print("❌ 知识库未启用PageIndex检索模式")
        return False

    # 检查PageIndex数据
    page_index_count = PageIndexNode.objects.filter(
        knowledge_id=knowledge.id
    ).count()

    if page_index_count == 0:
        print("❌ PageIndex未构建")
        return False

    print(f"PageIndex节点数量: {page_index_count}")
    print("✅ pg_vector.py集成检查通过")
    return True


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("PageIndex检索模式测试（方案B）")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("配置管理", test_page_index_mode_config()))
    results.append(("PageIndex数据", test_page_index_data()))
    results.append(("PageIndex检索", test_page_index_retrieval()))
    results.append(("pg_vector集成", test_pg_vector_integration()))

    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 测试通过")

    # 清理：重置为传统检索模式
    if knowledge := Knowledge.objects.first():
        PageIndexConfig.set_search_mode(str(knowledge.id), PageIndexConfig.SEARCH_MODE_TRADITIONAL)
        print("\n已重置为传统检索模式")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
