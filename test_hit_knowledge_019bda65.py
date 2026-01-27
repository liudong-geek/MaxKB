#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
命中测试脚本（针对指定知识库ID与固定测试问题）

使用方法:
    python test_hit_knowledge_019bda65.py
    python test_hit_knowledge_019bda65.py --knowledge-id <知识库ID>
"""
import os
import sys
import django
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(PROJECT_ROOT, 'apps')
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from common.config.embedding_config import VectorStore
from knowledge.models import Knowledge, Paragraph, Embedding, PageIndexNode, Document, SearchMode
from knowledge.page_index.page_index_retriever import PageIndexRetriever
from knowledge.serializers.common import get_embedding_model_by_knowledge_id, list_paragraph
from knowledge.serializers.knowledge import KnowledgeSerializer
from knowledge.vector.pg_vector import EmbeddingSearch, KeywordsSearch, BlendSearch

DEFAULT_KNOWLEDGE_ID = "019bda65-e3f7-79b1-8dad-f677d66da05c"

TEST_CASES = [
    {
        "query": "公司名称是什么？",
        "expected": ["爱才神（北京）文化科技有限公司"]
    },
    {
        "query": "成立时间是什么时候？",
        "expected": ["2025年7月30日"]
    },
    {
        "query": "注册地址在哪里？",
        "expected": ["北京市大兴区兴礼货贸元宇北路1号自贸试验区大兴机场片区自贸创新服务中心W7栋1层0158号"]
    },
    {
        "query": "办公地址是什么？",
        "expected": ["北京市丰台区台北路18号院金唐中心A座21楼"]
    },
    {
        "query": "统一社会信用代码是多少？",
        "expected": ["91110115MAERTEU477"]
    },
    {
        "query": "法定代表人是谁？",
        "expected": ["邹金汝"]
    },
    {
        "query": "副董事长是谁？",
        "expected": ["张宁"]
    },
    {
        "query": "CEO是谁？",
        "expected": ["张占山"]
    },
    {
        "query": "CSO是谁？",
        "expected": ["施绍煜"]
    },
    {
        "query": "CTO是谁？",
        "expected": ["万仁亮"]
    },
    {
        "query": "首席专家是谁？",
        "expected": ["余昱钧"]
    }
]


def hit_test(knowledge_id: str, workspace_id: str, query_text: str, top_n: int, similarity: float, search_mode: str) -> List[Dict]:
    return KnowledgeSerializer.HitTest(
        data={
            'workspace_id': workspace_id,
            'knowledge_id': knowledge_id,
            'query_text': query_text,
            'top_number': top_n,
            'similarity': similarity,
            'search_mode': search_mode
        }
    ).hit_test()


def _build_hit_response(hit_list: List[Dict]) -> List[Dict]:
    if not hit_list:
        return []
    hit_dict = {str(hit.get('paragraph_id')): hit for hit in hit_list}
    paragraph_ids = [str(hit.get('paragraph_id')) for hit in hit_list if hit.get('paragraph_id')]
    paragraphs = list_paragraph(paragraph_ids)
    results = []
    for paragraph in paragraphs:
        paragraph_id = str(paragraph.get('id'))
        hit = hit_dict.get(paragraph_id) or {}
        results.append({
            **paragraph,
            'paragraph_id': paragraph.get('id'),
            'similarity': hit.get('similarity'),
            'comprehensive_score': hit.get('comprehensive_score'),
            'section_title': hit.get('section_title'),
            'section_path': hit.get('section_path'),
            'tree_level': hit.get('tree_level'),
            'tree_path': hit.get('tree_path')
        })
    return results


def _build_query_set(knowledge_id: str):
    query_set = Embedding.objects.filter(knowledge_id=knowledge_id, is_active=True, source_type=1)
    disabled_document_ids = list(
        Document.objects.filter(knowledge_id=knowledge_id, is_active=False).values_list('id', flat=True)
    )
    if disabled_document_ids:
        query_set = query_set.exclude(document_id__in=disabled_document_ids)
    return query_set


def traditional_hit_test(knowledge_id: str, query_text: str, top_n: int, similarity: float, search_mode: str) -> List[Dict]:
    vector_store = VectorStore.get_embedding_vector()
    embedding_model = get_embedding_model_by_knowledge_id(knowledge_id)
    query_embedding = embedding_model.embed_query(query_text)

    query_set = _build_query_set(knowledge_id)
    if search_mode == 'embedding':
        handle = EmbeddingSearch()
    elif search_mode == 'keywords':
        handle = KeywordsSearch()
    else:
        handle = BlendSearch()

    hit_list = handle.handle(query_set, query_text, query_embedding, top_n, similarity, SearchMode(search_mode))
    return _build_hit_response(hit_list)


def page_index_hit_test(
    knowledge_id: str,
    query_text: str,
    top_n: int,
    similarity: float,
    search_mode: str,
    use_tree_filter: bool,
    aggregate_by_section: bool
) -> List[Dict]:
    embedding_model = get_embedding_model_by_knowledge_id(knowledge_id)
    query_embedding = embedding_model.embed_query(query_text)

    retriever = PageIndexRetriever(
        knowledge_id=knowledge_id,
        use_tree_filter=use_tree_filter,
        search_mode=search_mode,
        top_n=top_n,
        similarity_threshold=similarity,
        aggregate_by_section=aggregate_by_section
    )

    hit_list = retriever.query(query_text=query_text, query_embedding=query_embedding, top_n=top_n,
                               similarity_threshold=similarity)
    return _build_hit_response(hit_list)


def build_paragraph_map(paragraph_ids: List[str]) -> Dict[str, Dict]:
    if not paragraph_ids:
        return {}
    rows = Paragraph.objects.filter(id__in=paragraph_ids).values('id', 'title', 'content', 'document_id')
    return {str(row['id']): row for row in rows}


def is_hit(content: str, expected_list: List[str]) -> bool:
    if not content:
        return False
    for expected in expected_list:
        if expected in content:
            return True
    return False


def _run_suite(title: str, query_func, knowledge_id: str, top_n: int, similarity: float, search_mode: str,
               expected_mode_label: str):
    print("\n" + "-" * 90)
    print(f"测试模式: {title} | 检索模式: {expected_mode_label}")
    print("-" * 90)

    total_hits = 0
    for index, case in enumerate(TEST_CASES, 1):
        query = case['query']
        expected = case['expected']
        results = query_func(query)
        paragraph_ids = [str(item.get('paragraph_id')) for item in results if item.get('paragraph_id')]
        paragraph_map = build_paragraph_map(paragraph_ids)

        if index == 1:
            print(f"  返回结果数: {len(results)}")
            for preview_index, result in enumerate(results[:3], 1):
                paragraph_id = str(result.get('paragraph_id'))
                paragraph = paragraph_map.get(paragraph_id, {})
                preview = (paragraph.get('content') or '')[:80].replace('\n', ' ')
                print(f"  Top{preview_index} id={paragraph_id} preview={preview}...")

        hit = False
        hit_at = None
        hit_content = ""
        for rank, result in enumerate(results, 1):
            paragraph_id = str(result.get('paragraph_id'))
            paragraph = paragraph_map.get(paragraph_id, {})
            content = paragraph.get('content', '')
            if is_hit(content, expected):
                hit = True
                hit_at = rank
                hit_content = content
                break

        status = "✓" if hit else "✗"
        if hit:
            total_hits += 1
        print(f"[{index}/{len(TEST_CASES)}] {status} {query}")
        if hit:
            print(f"  命中位置: Top{hit_at}")
            print(f"  命中内容片段: {hit_content[:120].strip()}...")
        else:
            print("  未在Top结果中命中预期答案")

    hit_rate = total_hits / len(TEST_CASES) * 100
    print("-" * 90)
    print(f"命中率: {hit_rate:.2f}% ({total_hits}/{len(TEST_CASES)})")
    print("-" * 90)
    return hit_rate


def run_tests(
    knowledge_id: str,
    top_n: int,
    similarity: float,
    search_mode: str,
    mode: str,
    page_index_similarity: float,
    page_index_tree_filter: bool,
    page_index_aggregate: bool
):
    knowledge = Knowledge.objects.filter(id=knowledge_id).first()
    if not knowledge:
        raise SystemExit(f"知识库不存在: {knowledge_id}")

    workspace_id = str(knowledge.workspace_id)

    knowledge_meta = knowledge.meta or {}
    search_mode_config = knowledge_meta.get('search_mode', 'traditional')
    inner_search_mode = knowledge_meta.get('inner_search_mode', 'blend')
    embedding_count = Embedding.objects.filter(knowledge_id=knowledge_id, is_active=True).count()
    page_index_count = PageIndexNode.objects.filter(knowledge_id=knowledge_id).count()
    paragraph_count = Paragraph.objects.filter(knowledge_id=knowledge_id).count()
    null_paragraph_embeddings = Embedding.objects.filter(
        knowledge_id=knowledge_id,
        is_active=True,
        source_type=1,
        paragraph_id__isnull=True
    ).count()
    sample_name_count = Paragraph.objects.filter(knowledge_id=knowledge_id, content__contains='爱才神').count()
    sample_ceo_count = Paragraph.objects.filter(knowledge_id=knowledge_id, content__contains='张占山').count()
    sample_paragraph = Paragraph.objects.filter(knowledge_id=knowledge_id).values('id', 'content').first()
    sample_preview = ''
    if sample_paragraph and sample_paragraph.get('content'):
        sample_preview = sample_paragraph.get('content')[:120].replace('\n', ' ')

    expected_terms = sorted({term for case in TEST_CASES for term in case['expected']})
    expected_counts = {
        term: Paragraph.objects.filter(knowledge_id=knowledge_id, content__contains=term).count()
        for term in expected_terms
    }

    print("=" * 90)
    print("命中测试脚本")
    print(f"知识库ID: {knowledge_id}")
    print(f"工作区ID: {workspace_id}")
    print(f"请求检索模式: {search_mode} | top_n: {top_n} | similarity: {similarity}")
    print(f"知识库检索配置: search_mode={search_mode_config} | inner_search_mode={inner_search_mode}")
    print(f"Counts(paragraph/embedding/page_index): {paragraph_count} / {embedding_count} / {page_index_count}")
    print(f"Embeddings with NULL paragraph_id (source_type=PARAGRAPH): {null_paragraph_embeddings}")
    print(f"Contains(sample keywords): company={sample_name_count} | ceo={sample_ceo_count}")
    if sample_paragraph:
        print(f"Sample paragraph id: {sample_paragraph.get('id')}")
        print(f"Sample paragraph preview: {sample_preview}...")
    if expected_counts:
        print("Expected term coverage:")
        for term, count in expected_counts.items():
            print(f"  - {term}: {count}")

    term_samples = {}
    for term in expected_counts.keys():
        paragraph = Paragraph.objects.filter(knowledge_id=knowledge_id, content__contains=term).values('id').first()
        if paragraph:
            term_samples[term] = str(paragraph.get('id'))

    if term_samples:
        print("Embedding coverage for expected terms:")
        for term, paragraph_id in term_samples.items():
            has_embedding = Embedding.objects.filter(
                knowledge_id=knowledge_id,
                paragraph_id=paragraph_id,
                source_type=1,
                is_active=True
            ).exists()
            print(f"  - {term}: paragraph={paragraph_id} embedding={has_embedding}")
    print(f"测试问题数: {len(TEST_CASES)}")
    print("=" * 90)

    if mode in ('auto', 'all'):
        _run_suite(
            title="Auto(HitTest)",
            query_func=lambda q: hit_test(knowledge_id, workspace_id, q, top_n, similarity, search_mode),
            knowledge_id=knowledge_id,
            top_n=top_n,
            similarity=similarity,
            search_mode=search_mode,
            expected_mode_label=f"HitTest({search_mode})"
        )

    if mode in ('traditional', 'all'):
        _run_suite(
            title="Traditional(Bypass PageIndex)",
            query_func=lambda q: traditional_hit_test(knowledge_id, q, top_n, similarity, search_mode),
            knowledge_id=knowledge_id,
            top_n=top_n,
            similarity=similarity,
            search_mode=search_mode,
            expected_mode_label=f"Traditional({search_mode})"
        )

    if mode in ('page_index', 'all'):
        page_index_mode = inner_search_mode if search_mode == 'blend' else search_mode
        _run_suite(
            title="PageIndex(Override Threshold)",
            query_func=lambda q: page_index_hit_test(
                knowledge_id=knowledge_id,
                query_text=q,
                top_n=top_n,
                similarity=page_index_similarity,
                search_mode=page_index_mode,
                use_tree_filter=page_index_tree_filter,
                aggregate_by_section=page_index_aggregate
            ),
            knowledge_id=knowledge_id,
            top_n=top_n,
            similarity=page_index_similarity,
            search_mode=page_index_mode,
            expected_mode_label=f"PageIndex({page_index_mode})"
        )


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='知识库命中测试脚本')
    parser.add_argument('--knowledge-id', default=DEFAULT_KNOWLEDGE_ID, help='知识库ID')
    parser.add_argument('--top-n', type=int, default=5, help='返回结果数量')
    parser.add_argument('--similarity', type=float, default=0.2, help='相似度阈值')
    parser.add_argument('--search-mode', default='blend', choices=['embedding', 'keywords', 'blend'], help='检索模式')
    parser.add_argument('--mode', default='all', choices=['auto', 'traditional', 'page_index', 'all'],
                        help='测试模式: auto=HitTest, traditional=绕过PageIndex, page_index=手动PageIndex, all=全部')
    parser.add_argument('--page-index-similarity', type=float, default=0.2, help='PageIndex测试的相似度阈值')
    parser.add_argument('--page-index-tree-filter', action='store_true', help='PageIndex是否使用树过滤')
    parser.add_argument('--page-index-aggregate', action='store_true', help='PageIndex是否按章节聚合')

    args = parser.parse_args()
    run_tests(
        knowledge_id=args.knowledge_id,
        top_n=args.top_n,
        similarity=args.similarity,
        search_mode=args.search_mode,
        mode=args.mode,
        page_index_similarity=args.page_index_similarity,
        page_index_tree_filter=args.page_index_tree_filter,
        page_index_aggregate=args.page_index_aggregate
    )
