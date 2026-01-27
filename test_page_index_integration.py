#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PageIndex集成测试脚本
测试智能分段后，段落的section_title、section_path、summary字段是否正确生成
"""

import os
import sys
import django

# 设置Django环境（与main.py相同）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')

os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

try:
    django.setup()
    print("✅ Django setup successful")
    
    from knowledge.models import Document, Knowledge, Paragraph, PageIndexNode
    from knowledge.page_index.page_index_builder import PageIndex
    from knowledge.serializers.common import _build_page_index_after_paragraph_creation
    
    def test_page_index_integration():
        """测试PageIndex集成"""
        print("\n=== PageIndex集成测试 ===")
        
        # 获取第一个知识库
        knowledge = Knowledge.objects.first()
        if not knowledge:
            print("❌ 没有找到知识库")
            return
        
        print(f"📚 使用知识库: {knowledge.name} (ID: {knowledge.id})")
        
        # 获取第一个文档
        document = Document.objects.filter(knowledge=knowledge).first()
        if not document:
            print("❌ 没有找到文档")
            return
        
        print(f"📄 使用文档: {document.name} (ID: {document.id})")
        
        # 检查段落数量
        paragraph_count = Paragraph.objects.filter(document=document).count()
        print(f"📝 段落数量: {paragraph_count}")
        
        if paragraph_count == 0:
            print("❌ 文档没有段落，无法测试")
            return
        
        # 记录更新前的状态
        print("\n--- 更新前的字段状态 ---")
        paragraphs_before = list(Paragraph.objects.filter(document=document))
        for i, p in enumerate(paragraphs_before[:3], 1):
            print(f"段落 {i}: section_title='{p.section_title}', section_path='{p.section_path}', summary='{p.summary[:50] if p.summary else ''}...'")
        
        # 手动触发PageIndex构建
        print("\n--- 触发PageIndex构建 ---")
        try:
            _build_page_index_after_paragraph_creation([str(document.id)])
            print("✅ PageIndex构建完成")
        except Exception as e:
            print(f"❌ PageIndex构建失败: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 检查PageIndex节点
        node_count = PageIndexNode.objects.filter(document=document).count()
        print(f"🌳 PageIndex节点数量: {node_count}")
        
        # 记录更新后的状态
        print("\n--- 更新后的字段状态 ---")
        paragraphs_after = list(Paragraph.objects.filter(document=document))
        for i, p in enumerate(paragraphs_after[:3], 1):
            print(f"段落 {i}:")
            print(f"  section_title: '{p.section_title}'")
            print(f"  section_path: '{p.section_path}'")
            print(f"  summary: '{p.summary[:100] if p.summary else ''}{'...' if p.summary and len(p.summary) > 100 else ''}'")
            
            # 检查字段是否为空
            has_data = bool(p.section_title.strip() or p.section_path.strip() or p.summary.strip())
            status = "✅" if has_data else "❌"
            print(f"  数据状态: {status}")
        
        # 统计有数据的段落
        with_data_count = sum(1 for p in paragraphs_after if p.section_title.strip() or p.section_path.strip() or p.summary.strip())
        print(f"\n📊 统计结果:")
        print(f"  总段落数: {len(paragraphs_after)}")
        print(f"  有数据的段落: {with_data_count}")
        print(f"  无数据的段落: {len(paragraphs_after) - with_data_count}")
        
        if with_data_count > 0:
            print("✅ 测试通过：智能分段成功生成了章节信息")
        else:
            print("❌ 测试失败：智能分段没有生成章节信息")
    
    if __name__ == '__main__':
        test_page_index_integration()
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()