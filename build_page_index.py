#!/usr/bin/env python
# coding=utf-8
"""
PageIndex树构建工具
用于从现有文档构建PageIndex树
"""
import os
import sys
import django

# 设置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.insert(0, APP_DIR)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import Document, Knowledge
from knowledge.page_index import PageIndex
from knowledge.serializers.common import get_embedding_model_id_by_knowledge_id
from knowledge.task.embedding import embedding_by_document



def build_for_knowledge(knowledge_id: str, chunk_size: int = 1000):
    """
    为指定知识库构建PageIndex
    
    Args:
        knowledge_id: 知识库ID
        chunk_size: 分块大小
    """
    print(f"开始为知识库 {knowledge_id} 构建PageIndex...")
    
    # 获取知识库
    try:
        knowledge = Knowledge.objects.get(id=knowledge_id)
    except Knowledge.DoesNotExist:
        print(f"❌ 知识库不存在: {knowledge_id}")
        return False
    
    # 获取所有文档
    documents = Document.objects.filter(
        knowledge=knowledge,
        status='SUCCESS'
    )
    
    print(f"📄 找到 {documents.count()} 个文档")
    
    if documents.count() == 0:
        print("⚠️  没有需要处理的文档")
        return True
    
    # 构建PageIndex
    try:
        page_index = PageIndex.from_documents(
            documents=list(documents),
            knowledge=knowledge,
            chunk_size=chunk_size
        )
        
        # 显示统计信息
        stats = page_index.get_statistics()
        print(f"\n✅ PageIndex构建成功！")
        print(f"   总节点数: {stats['total_nodes']}")
        print(f"   最大深度: {stats['max_depth']}")
        print(f"   深度分布: {stats['depth_distribution']}")
        
        # 显示树摘要
        print(f"\n📊 树结构摘要（前3层）：")
        print(page_index.get_tree_summary(max_depth=3))
        
        return True
        
    except Exception as e:
        print(f"❌ 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_all_knowledge():
    """为所有知识库构建PageIndex"""
    knowledges = Knowledge.objects.all()
    print(f"找到 {knowledges.count()} 个知识库\n")
    
    success_count = 0
    for kb in knowledges:
        print(f"{'='*60}")
        print(f"处理知识库: {kb.name} ({kb.id})")
        print(f"{'='*60}")
        
        if build_for_knowledge(str(kb.id)):
            success_count += 1
        print()
    
    print(f"\n{'='*60}")
    print(f"完成: {success_count}/{knowledges.count()} 个知识库构建成功")
    print(f"{'='*60}")


def rebuild_sections_and_embeddings(knowledge_id: str = None):
    """重建段落章节字段并重新向量化"""
    from knowledge.models import Knowledge, Document, Paragraph, ParagraphVectorModel
    
    print("[RebuildSections] Starting rebuild process...")
    
    if knowledge_id:
        knowledge_list = Knowledge.objects.filter(id=knowledge_id)
        if not knowledge_list.exists():
            print(f"[RebuildSections] Knowledge {knowledge_id} not found")
            return
    else:
        knowledge_list = Knowledge.objects.all()
    
    for knowledge in knowledge_list:
        print(f"\n[RebuildSections] Processing knowledge: {knowledge.id} - {knowledge.name}")
        
        # 1. 先构建 PageIndex（如果未构建）
        from knowledge.page_index.page_index_config import PageIndexConfig
        if PageIndexConfig.is_enabled(knowledge.id):
            print(f"[RebuildSections] Building PageIndex for knowledge {knowledge.id}...")
            build_for_knowledge(str(knowledge.id))
        
        # 2. 获取所有需要重新向量化的文档
        documents = Document.objects.filter(knowledge_id=knowledge.id, status='SUCCESS').all()
        print(f"[RebuildSections] Found {len(documents)} documents")
        
        for doc in documents:
            print(f"[RebuildSections] Processing document: {doc.id} - {doc.name}")
            
            # 3. 删除旧的 Embedding（让向量化任务重新生成）
            deleted_count = ParagraphVectorModel.objects.filter(document_id=doc.id).delete()[0]
            print(f"[RebuildSections] Deleted {deleted_count} old embeddings for document {doc.id}")
            
            # 4. 触发重新向量化
            try:
                embedding_model_id = get_embedding_model_id_by_knowledge_id(knowledge.id)
                if embedding_model_id:
                    print(f"[RebuildSections] Triggering re-embedding for document {doc.id} with model {embedding_model_id}")
                    embedding_by_document.delay(str(doc.id), str(knowledge.id), str(embedding_model_id))
                else:
                    print(f"[RebuildSections] No embedding model found for knowledge {knowledge.id}")
            except Exception as e:
                print(f"[RebuildSections] Failed to trigger embedding: {e}")
    
    print("\n[RebuildSections] Rebuild process completed!")


def print_usage():
    """打印使用说明"""
    print("用法:")
    print("  python build_page_index.py <knowledge_id> [chunk_size]")
    print("  python build_page_index.py --all")
    print("  python build_page_index.py --rebuild [knowledge_id]")
    print("\n示例:")
    print("  python build_page_index.py abc-123-def 1000")
    print("  python build_page_index.py --all")
    print("  python build_page_index.py --rebuild abc-123-def")
    print("  python build_page_index.py --rebuild")
    print("\n参数说明:")
    print("  knowledge_id: 知识库UUID")
    print("  chunk_size:   分块大小（默认1000）")
    print("  --all:        为所有知识库构建")
    print("  --rebuild:    重建章节字段并重新向量化（可指定知识库ID）")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        build_all_knowledge()
    elif sys.argv[1] == '--rebuild':
        knowledge_id = sys.argv[2] if len(sys.argv) > 2 else None
        rebuild_sections_and_embeddings(knowledge_id)
    else:
        knowledge_id = sys.argv[1]
        chunk_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        build_for_knowledge(knowledge_id, chunk_size)
