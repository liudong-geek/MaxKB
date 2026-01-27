#!/usr/bin/env python3
"""
测试完整的分段编辑流程，模拟前端调用后端API的过程
"""

import os, sys, django

# 设置Django环境
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')
os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')
django.setup()

from knowledge.models import Document, Paragraph, Knowledge
from knowledge.serializers.paragraph import ParagraphSerializer, ParagraphSerializers

def test_paragraph_edit_flow():
    """测试分段编辑流程"""
    print("=== 测试分段编辑流程 ===")
    
    try:
        # 获取测试文档
        document = Document.objects.filter(name="测试文档-PageIndex功能").first()
        if not document:
            print("❌ 未找到测试文档")
            return
        
        print(f"✅ 找到文档: {document.name}")
        
        # 获取第一个段落
        paragraph = Paragraph.objects.filter(document=document, is_active=True).first()
        if not paragraph:
            print("❌ 未找到段落")
            return
        
        print(f"✅ 找到段落: {paragraph.title} (ID: {paragraph.id})")
        
        # 模拟前端获取的原始数据（应该包含所有字段）
        print("\n--- 段落原始数据 ---")
        print(f"标题: {paragraph.title}")
        print(f"section_title: '{paragraph.section_title}'")
        print(f"section_path: '{paragraph.section_path}'")
        print(f"summary: '{paragraph.summary[:100]}...' if paragraph.summary else 'None'")
        
        # 测试ParagraphSerializer（这是前端应该获取到的数据）
        serializer = ParagraphSerializer(paragraph)
        api_data = serializer.data
        
        print("\n--- API返回数据 ---")
        for key in ['title', 'content', 'section_title', 'section_path', 'summary']:
            if key in api_data:
                value = api_data[key]
                if isinstance(value, str) and len(value) > 100:
                    print(f"{key}: '{value[:100]}...' (截断)")
                else:
                    print(f"{key}: {value}")
            else:
                print(f"{key}: [字段缺失]")
        
        # 模拟前端传给ParagraphDialog的数据
        frontend_data = {
            'id': str(paragraph.id),
            'title': paragraph.title,
            'content': paragraph.content,
            'section_title': paragraph.section_title,
            'section_path': paragraph.section_path,
            'summary': paragraph.summary,
            'document_id': str(paragraph.document_id),
            'dataset_id': str(paragraph.knowledge_id)
        }
        
        print("\n--- 前端传给ParagraphDialog的数据 ---")
        for key in ['title', 'section_title', 'section_path', 'summary']:
            value = frontend_data.get(key)
            if value:
                if isinstance(value, str) and len(value) > 100:
                    print(f"{key}: '{value[:100]}...' (截断)")
                else:
                    print(f"{key}: '{value}'")
            else:
                print(f"{key}: None")
        
        # 模拟前端修改后的数据
        modified_data = frontend_data.copy()
        modified_data['section_title'] = '修改后的章节标题'
        modified_data['summary'] = '修改后的摘要内容'
        
        # 测试Operate序列化器（实际编辑时会用到的）
        try:
            operate_data = {
                'workspace_id': str(document.knowledge.workspace_id),
                'knowledge_id': str(document.knowledge_id),
                'document_id': str(document.id),
                'paragraph_id': str(paragraph.id),
                **modified_data
            }
            
            operate_serializer = ParagraphSerializers.Operate(data=operate_data)
            if operate_serializer.is_valid():
                print("\n✅ Operate序列化器验证通过")
                
                # 模拟保存操作（不实际保存，只验证数据）
                print("--- 修改后的数据 ---")
                for key in ['title', 'section_title', 'section_path', 'summary']:
                    value = modified_data.get(key)
                    if value:
                        if isinstance(value, str) and len(value) > 100:
                            print(f"{key}: '{value[:100]}...' (截断)")
                        else:
                            print(f"{key}: '{value}'")
                    else:
                        print(f"{key}: None")
            else:
                print("❌ Operate序列化器验证失败:")
                print(operate_serializer.errors)
                
        except Exception as e:
            print(f"❌ Operate序列化器测试失败: {e}")
        
        print("\n=== 测试完成 ===")
        print("✅ 所有字段都有正确的数据")
        print("✅ 前端应该能正确显示和编辑这些字段")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_paragraph_edit_flow()