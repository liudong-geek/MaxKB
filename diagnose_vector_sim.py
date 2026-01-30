# coding=utf-8
"""
Vector Search Diagnosis Script
1. Calculates cosine distance between query and target paragraph
2. Checks model consistency
3. Simulates vector search SQL
"""
import os
import sys
import django
import numpy as np
from django.conf import settings

# Setup Django environment
sys.path.append('d:\\code\\v21\\MaxKB\\apps')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "maxkb.settings")
django.setup()

from knowledge.models import Paragraph
from knowledge.vector.pg_vector import PGVector
from models_provider.models import Model
from langchain_core.embeddings import Embeddings
from common.config.embedding_config import ModelManage
from models_provider.tools import get_model, get_model_default_params

def get_embedding_model(model_id):
    model = Model.objects.get(id=model_id)
    default_params = get_model_default_params(model)
    return ModelManage.get_model(model_id, lambda _id: get_model(model, **default_params))

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def main():
    print("=" * 60)
    print("Vector Search Deep Diagnosis")
    print("=" * 60)

    query_text = "爱才神公司的注册地址是哪里"
    target_content_fragment = "北京市大兴区礼贤镇元平北路1号"
    
    # 1. Find target paragraph
    print(f"\n[1] Finding target paragraph containing '{target_content_fragment}'...")
    paragraphs = Paragraph.objects.filter(content__contains=target_content_fragment)
    if not paragraphs.exists():
        print("❌ Target paragraph not found!")
        return
        
    target_paragraph = paragraphs.first()
    print(f"✅ Found Paragraph ID: {target_paragraph.id}")
    print(f"   Knowledge ID: {target_paragraph.knowledge_id}")
    
    # 2. Get Knowledge Base Model
    from knowledge.models import Knowledge
    knowledge = Knowledge.objects.get(id=target_paragraph.knowledge_id)
    model_id = knowledge.embedding_model_id
    print(f"\n[2] Knowledge Base Model Info")
    print(f"   Knowledge Name: {knowledge.name}")
    print(f"   Model ID: {model_id}")
    
    try:
        model_obj = Model.objects.get(id=model_id)
        print(f"   Model Name: {model_obj.name}")
        print(f"   Model Provider: {model_obj.provider}")
    except Model.DoesNotExist:
        print("❌ Model not found in DB!")
        return

    # 3. Get Embedding from DB
    print(f"\n[3] Fetching Stored Embedding Vector")
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT embedding, source_type 
            FROM embedding 
            WHERE paragraph_id = %s 
            AND embedding IS NOT NULL
        """, [str(target_paragraph.id)])
        rows = cursor.fetchall()

    if not rows:
        print("❌ No embedding found for this paragraph!")
        return

    print(f"   Found {len(rows)} embeddings for this paragraph.")
    
    target_vector = None
    for row in rows:
        vec_str, source_type = row
        # Parse vector string format from PGVector (usually string or list)
        # Using a simple eval/json parse might be needed depending on driver return type
        # For psycopg2 it might return a string list representation
        try:
             # Assuming list or numpy array compatible
             vec = np.array(vec_str) if isinstance(vec_str, list) else np.array(eval(vec_str.replace('{', '[').replace('}', ']')))
             print(f"   - Source Type {source_type}: Dim={len(vec)}")
             if source_type == 1: # PARAGRAPH
                 target_vector = vec
        except Exception as e:
            print(f"   Error parsing vector: {e}")

    if target_vector is None:
        print("⚠️ Could not retrieve PARAGRAPH level embedding, using first available.")
        # Fallback parsing again
        vec_str = rows[0][0]
        target_vector = np.array(eval(vec_str.replace('{', '[').replace('}', ']')))

    # 4. Generate Query Vector
    print(f"\n[4] Generating Query Vector for '{query_text}'")
    try:
        embedding_model = get_embedding_model(model_id)
        query_vector = np.array(embedding_model.embed_query(query_text))
        print(f"   Query Vector Generated. Dim={len(query_vector)}")
    except Exception as e:
        print(f"❌ Failed to generate query vector: {e}")
        return

    # 5. Calculate Similarity
    print(f"\n[5] Calculating Similarity")
    if len(query_vector) != len(target_vector):
        print(f"❌ Dimension Mismatch! Query={len(query_vector)}, Target={len(target_vector)}")
    else:
        sim = cosine_similarity(query_vector, target_vector)
        distance = 1 - sim
        print(f"   Cosine Similarity: {sim:.4f}")
        print(f"   Cosine Distance:   {distance:.4f}")
        print(f"   Required Threshold for 0.1 similarity: Need sim >= 0.1")
        
        if sim < 0.1:
            print("🔴 Similarity IS extremely low (< 0.1). This explains why search fails.")
            print("   Possible reasons: Model mismatch, bad quality embedding, or query too different.")
        else:
            print("🟢 Similarity > 0.1. Search SHOULD work if logic is correct.")

if __name__ == "__main__":
    main()
