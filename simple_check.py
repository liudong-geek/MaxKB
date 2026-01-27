import os
import sys
import django

# 设置路径（与main.py相同）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'apps')

os.chdir(BASE_DIR)
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maxkb.settings')

try:
    django.setup()
    print("✅ Django setup successful")
    
    from knowledge.models import Paragraph, Document, Knowledge
    
    # 检查数据
    paragraph_count = Paragraph.objects.count()
    doc_count = Document.objects.count()
    knowledge_count = Knowledge.objects.count()
    
    print(f"📊 知识库数量: {knowledge_count}")
    print(f"📄 文档数量: {doc_count}")
    print(f"📝 段落数量: {paragraph_count}")
    
    if paragraph_count > 0:
        # 检查前几个段落的字段
        paragraphs = Paragraph.objects.all()[:5]
        
        print("\n=== 段落字段检查 ===")
        for i, p in enumerate(paragraphs, 1):
            print(f"\n段落 {i}:")
            print(f"  ID: {p.id}")
            print(f"  标题: '{p.title}'")
            print(f"  章节标题: '{p.section_title}'")
            print(f"  章节路径: '{p.section_path}'")
            print(f"  摘要: '{p.summary[:50] if p.summary else ''}{'...' if p.summary and len(p.summary) > 50 else ''}'")
            
            # 检查是否为空
            has_data = bool(p.section_title.strip() or p.section_path.strip() or p.summary.strip())
            status = "✅" if has_data else "❌"
            print(f"  数据状态: {status}")
    
    print("\n✅ 检查完成")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()