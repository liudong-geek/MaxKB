
import os
import django
import sys
import json

# Add apps to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from knowledge.models import Paragraph, Embedding, PageIndexNode

def check_reindex():
    print("=== Checking Re-Index Status for '首席专家' ===", flush=True)
    
    # 1. Find the Paragraph
    keywords = "首席专家"
    paras = Paragraph.objects.filter(content__icontains=keywords)
    print(f"Found {paras.count()} paragraphs containing '{keywords}'", flush=True)
    
    if paras.count() == 0:
        print("[ERROR] No paragraph found! Is data loaded?", flush=True)
        return

    target_para = paras.first()
    print(f"Target Paragraph ID: {target_para.id}", flush=True)
    print(f"Target Content Preview: {target_para.content[:50]}...", flush=True)
    
    # 2. Find the Embedding
    emb = Embedding.objects.filter(paragraph_id=target_para.id).first()
    if not emb:
        print("[ERROR] No embedding found for this paragraph! Re-vectorization failed or pending.", flush=True)
        return
        
    print(f"Embedding ID: {emb.id}", flush=True)
    
    # 3. Check PageIndex Linkage (The Logic Change)
    print("\n[Check 1] Linkage to PageIndex Node", flush=True)
    if emb.page_index_node_id:
        print(f"PASS: Linked to Node ID: {emb.page_index_node_id}", flush=True)
        # Fetch Node Content
        node = PageIndexNode.objects.get(id=emb.page_index_node_id)
        summary = (node.content or "").strip()
        print(f"   Node Content (Summary): {summary[:100]}...", flush=True)
        if not summary:
            print("   [WARN] Node content is empty! Vector might still be weak.", flush=True)
    else:
        print("FAIL: page_index_node_id is NULL. The code change did NOT take effect during re-indexing.", flush=True)
        print("Possible reasons: Service not restarted, or data not re-parsed (just re-embedded without resolving logic?).", flush=True)

    # 4. Check Vector Dimensions
    try:
        vec_len = len(emb.embedding)
        print(f"\n[Check 2] Vector Dimension: {vec_len}", flush=True)
        if vec_len == 1536: # Assuming OpenAI
            print("PASS: Vector dimension looks correct.", flush=True)
        elif vec_len == 0:
             print("FAIL: Vector is empty.", flush=True)
    except:
        print("WARN: Could not read vector length directly.", flush=True)

if __name__ == "__main__":
    check_reindex()
