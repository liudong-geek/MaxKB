#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试文档和段落
"""

import os
import sys
import django
import uuid_utils.compat as uuid

# 设置Django环境
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')

os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

try:
    django.setup()
    print("✅ Django setup successful")
    
    from knowledge.models import Document, Knowledge, Paragraph
    
    def create_test_document():
        """创建测试文档和段落"""
        print("\n=== 创建测试文档 ===")
        
        # 获取第一个知识库
        knowledge = Knowledge.objects.first()
        if not knowledge:
            print("❌ 没有找到知识库")
            return None
        
        print(f"📚 使用知识库: {knowledge.name} (ID: {knowledge.id})")
        
        # 创建测试文档
        document_id = uuid.uuid7()
        document = Document(
            id=document_id,
            knowledge=knowledge,
            name="测试文档-PageIndex功能",
            char_length=0,
            type=0  # BASE
        )
        document.save()
        
        print(f"📄 创建文档: {document.name} (ID: {document.id})")
        
        # 创建测试段落（包含Markdown标题结构）
        test_paragraphs = [
            {
                'title': '第一章',
                'content': '''# 第一章：系统概述

## 1.1 简介

这是一个测试文档的第一章节，用于验证PageIndex功能。

## 1.2 背景

系统的主要目的是提高检索效率和准确性。
'''
            },
            {
                'title': '第二章', 
                'content': '''# 第二章：技术架构

## 2.1 整体设计

系统采用分层架构设计，包含以下层次：

1. 表示层
2. 业务层  
3. 数据层

## 2.2 核心组件

核心组件包括：

- 检索引擎
- 向量数据库
- 知识图谱
'''
            },
            {
                'title': '第三章',
                'content': '''# 第三章：实施步骤

## 3.1 准备工作

实施前的准备工作包括环境搭建和依赖安装。

## 3.2 部署流程

详细的部署流程将在后续文档中说明。
'''
            },
            {
                'title': '总结',
                'content': '''# 总结

本文档介绍了系统的基本架构和实施步骤。

通过PageIndex功能，可以实现更好的文档结构化管理和检索。
'''
            }
        ]
        
        # 创建段落记录
        created_paragraphs = []
        for i, para_data in enumerate(test_paragraphs, 1):
            paragraph = Paragraph(
                id=uuid.uuid7(),
                document=document,
                knowledge=knowledge,
                title=para_data['title'],
                content=para_data['content'],
                position=i,
                is_active=True
            )
            paragraph.save()
            created_paragraphs.append(paragraph)
            print(f"📝 创建段落 {i}: {para_data['title']}")
        
        # 更新文档字符数
        total_chars = sum(len(p.content) for p in created_paragraphs)
        document.char_length = total_chars
        document.save()
        
        print(f"✅ 创建完成：{len(created_paragraphs)} 个段落，总字符数：{total_chars}")
        return document
    
    if __name__ == '__main__':
        document = create_test_document()
        if document:
            print(f"\n🎉 测试文档创建成功！")
            print(f"📄 文档ID: {document.id}")
            print(f"📚 知识库ID: {document.knowledge_id}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()