#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查分段字段的测试脚本
验证智能分段后，Paragraph表的section_title、section_path、summary字段是否正确保存
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import Paragraph, Document, Knowledge


def check_paragraph_fields(document_id=None, knowledge_id=None):
    """检查分段字段"""
    print("=== 分段字段检查 ===")
    
    # 构建查询条件
    query = {}
    if document_id:
        query['document_id'] = document_id
    if knowledge_id:
        query['knowledge_id'] = knowledge_id
    
    paragraphs = Paragraph.objects.filter(**query).order_by('position')
    
    if not paragraphs.exists():
        print("❌ 没有找到匹配的段落")
        return
    
    print(f"📊 找到 {paragraphs.count()} 个段落")
    
    for idx, paragraph in enumerate(paragraphs):
        print(f"\n--- 段落 {idx + 1} ---")
        print(f"ID: {paragraph.id}")
        print(f"标题: '{paragraph.title}'")
        print(f"章节标题: '{paragraph.section_title}'")
        print(f"章节路径: '{paragraph.section_path}'")
        print(f"摘要: '{paragraph.summary[:100] if paragraph.summary else ''}{'...' if len(paragraph.summary) > 100 else '' if paragraph.summary else '(空)'}'")
        print(f"内容长度: {len(paragraph.content) if paragraph.content else 0}")
        
        # 检查字段是否为空
        empty_fields = []
        if not paragraph.section_title.strip():
            empty_fields.append('section_title')
        if not paragraph.section_path.strip():
            empty_fields.append('section_path')
        if not paragraph.summary.strip():
            empty_fields.append('summary')
        
        if empty_fields:
            print(f"⚠️  空字段: {', '.join(empty_fields)}")
        else:
            print("✅ 所有字段都有值")


def check_recent_documents(knowledge_id=None, limit=5):
    """检查最近的文档"""
    print("\n=== 最近文档检查 ===")
    
    query = {}
    if knowledge_id:
        query['knowledge_id'] = knowledge_id
    
    documents = Document.objects.filter(**query).order_by('-create_time')[:limit]
    
    if not documents.exists():
        print("❌ 没有找到文档")
        return
    
    print(f"📄 最近的 {len(documents)} 个文档:")
    for doc in documents:
        paragraph_count = Paragraph.objects.filter(document=doc).count()
        print(f"- {doc.name} (ID: {doc.id}) - {paragraph_count} 个段落")


def check_knowledge():
    """检查知识库"""
    print("\n=== 知识库检查 ===")
    
    knowledges = Knowledge.objects.all()[:10]
    
    if not knowledges.exists():
        print("❌ 没有找到知识库")
        return
    
    print(f"📚 前 {len(knowledges)} 个知识库:")
    for knowledge in knowledges:
        doc_count = Document.objects.filter(knowledge=knowledge).count()
        print(f"- {knowledge.name} (ID: {knowledge.id}) - {doc_count} 个文档")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='检查分段字段')
    parser.add_argument('--document-id', help='文档ID')
    parser.add_argument('--knowledge-id', help='知识库ID')
    parser.add_argument('--all', action='store_true', help='检查所有分段')
    
    args = parser.parse_args()
    
    # 显示基本信息
    check_knowledge()
    check_recent_documents(args.knowledge_id)
    
    # 检查分段字段
    if args.all or args.document_id or args.knowledge_id:
        check_paragraph_fields(args.document_id, args.knowledge_id)
    else:
        print("\n💡 使用 --all 检查所有分段，或指定 --document-id 或 --knowledge-id")
    
    print("\n✅ 检查完成")