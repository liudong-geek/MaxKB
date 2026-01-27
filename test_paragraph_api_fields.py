#!/usr/bin/env python3
"""
测试段落API是否正确返回section_title、section_path和summary字段
"""

import os
import sys
import json
import django

# 设置Django环境（与main.py相同）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')

os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import Document, Paragraph
from knowledge.serializers.paragraph import ParagraphSerializer, ParagraphSerializers

def test_paragraph_api_fields():
    """测试段落API字段返回"""
    print("=== 测试段落API字段返回 ===")
    
    try:
        # 获取测试文档
        documents = Document.objects.filter(name="测试文档-PageIndex功能")
        if not documents.exists():
            print("❌ 未找到测试文档，请先运行 create_test_document.py")
            return
        
        document = documents.first()
        print(f"✅ 找到测试文档: {document.name} (ID: {document.id})")
        
        # 获取该文档的所有段落
        paragraphs = Paragraph.objects.filter(document=document, is_active=True)
        if not paragraphs.exists():
            print("❌ 该文档没有段落")
            return
        
        print(f"✅ 找到 {paragraphs.count()} 个段落")
        
        # 测试ParagraphSerializer
        for i, paragraph in enumerate(paragraphs[:3]):  # 只测试前3个段落
            print(f"\n--- 段落 {i+1} (ID: {paragraph.id}) ---")
            print(f"标题: {paragraph.title}")
            print(f"section_title: '{paragraph.section_title}'")
            print(f"section_path: '{paragraph.section_path}'")
            print(f"summary: '{paragraph.summary[:50]}...' if paragraph.summary else 'None'")
            
            # 测试序列化器
            serializer = ParagraphSerializer(paragraph)
            data = serializer.data
            
            print(f"\n序列化器返回:")
            for key in ['section_title', 'section_path', 'summary']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str):
                        print(f"  {key}: '{value[:50]}...' if len(value) > 50 else '{value}'")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: [字段缺失]")
        
        # 测试Operate序列化器的one方法
        print(f"\n=== 测试Operate序列化器 ===")
        if paragraphs.exists():
            first_paragraph = paragraphs.first()
            operate_serializer = ParagraphSerializers.Operate(data={'paragraph_id': str(first_paragraph.id)})
            operate_serializer.is_valid()
            result = operate_serializer.one()
            
            print("Operate.one() 返回的字段:")
            for key in ['section_title', 'section_path', 'summary']:
                if key in result:
                    value = result[key]
                    if isinstance(value, str):
                        print(f"  {key}: '{value[:50]}...' if len(value) > 50 else '{value}'")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: [字段缺失]")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_paragraph_api_fields()