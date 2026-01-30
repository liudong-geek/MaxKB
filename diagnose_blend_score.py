# coding=utf-8
"""
Blend Search SQL Simulator
Executes the raw SQL used in blend_search.sql to see actual scores.
"""
import os
import sys
import django
import numpy as np
from django.db import connection

# Setup Django environment
sys.path.append('d:\\code\\v21\\MaxKB\\apps')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "maxkb.settings")
django.setup()

from knowledge.vector.pg_vector import PGVector
from models_provider.models import Model
from models_provider.tools import get_model, get_model_default_params
from common.config.embedding_config import ModelManage
from common.utils.ts_vecto_util import to_query

def get_embedding_model(model_id):
    model = Model.objects.get(id=model_id)
    default_params = get_model_default_params(model)
    return ModelManage.get_model(model_id, lambda _id: get_model(model, **default_params))

def main():
    print("=" * 60)
    print("Blend Search SQL Simulator")
    print("=" * 60)

    query_text = "爱才神公司的注册地址是哪里"
    # Target paragraph ID found in previous step
    target_paragraph_id = "019bfdf0-cc8d-77f0-b80b-9a2dfa39f0c3" 
    
    # 1. Get Model and Generate Vector
    print(f"\n[1] Generating Query Vector...")
    # Hardcoded model ID from previous run
    model_id = "019bd3ce-3669-7dd2-943b-3e8d236dcefb" 
    embedding_model = get_embedding_model(model_id)
    query_vector = embedding_model.embed_query(query_text)
    
    # 2. Prepare SQL Parameters
    print(f"\n[2] Preparing SQL Parameters...")
    # vector weight = 0.5, keyword weight = 0.5 for testing
    vector_weight = 0.5
    keyword_weight = 0.5
    embedding_query = str(query_vector) # format depends on driver, usually string works for pgvector wrapper
    ts_query_text = to_query(query_text)
    
    print(f"   Query: {query_text}")
    print(f"   TS Query: {ts_query_text}")
    print(f"   Weights: V={vector_weight}, K={keyword_weight}")

    # 3. Reading SQL Template
    print(f"\n[3] Reading SQL Template...")
    sql_path = 'd:\\code\\v21\\MaxKB\\apps\\knowledge\\sql\\blend_search.sql'
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # 4. Execute SQL
    print(f"\n[4] Executing SQL (Filtered for Target Paragraph)...")
    
    # Inject a WHERE clause to only look at our target (for debugging clarity)
    # The original SQL usually has WHERE clause for knowledge_id etc.
    # We will wrap the original SQL in a subquery or modify it?
    # Actually, the SQL is complex with CTEs.
    # Let's just execute the CORE selection part manually to debug the score.
    
    debug_sql = """
    WITH vector_score AS (
        SELECT 
            paragraph_id,
            (1 - (embedding <=> %s::vector)) as score
        FROM embedding 
        WHERE paragraph_id = %s
    ),
    keyword_score AS (
        SELECT 
            paragraph_id,
            ts_rank_cd(search_vector, to_tsquery('simple', %s), 32) as raw_rank,
            (ts_rank_cd(search_vector, to_tsquery('simple', %s), 32) / (ts_rank_cd(search_vector, to_tsquery('simple', %s), 32) + 0.1)) as normalized_score
        FROM embedding
        WHERE paragraph_id = %s AND source_type = '1'
    )
    SELECT 
        v.paragraph_id,
        v.score as vector_score,
        k.raw_rank as keyword_raw_rank,
        k.normalized_score as keyword_normalized_score,
        (v.score * %s + k.normalized_score * %s) as blend_score
    FROM vector_score v
    LEFT JOIN keyword_score k ON v.paragraph_id = k.paragraph_id
    """
    
    with connection.cursor() as cursor:
        cursor.execute(debug_sql, [
            embedding_query, 
            target_paragraph_id, 
            ts_query_text, ts_query_text, ts_query_text, target_paragraph_id,
            vector_weight, keyword_weight
        ])
        results = cursor.fetchall()

    if not results:
        print("❌ No results found for target paragraph!")
    else:
        print(f"\n[5] Analysis Results")
        for row in results:
            p_id, v_score, k_rank, k_score, final_score = row
            print(f"   Paragraph ID: {p_id}")
            print(f"   Vector Score: {v_score:.4f}")
            print(f"   Keyword Rank (Raw): {k_rank}")
            print(f"   Keyword Score (Norm): {k_score}")
            print(f"   Blend Score (50/50): {final_score:.4f}")
            
            k_rank_val = k_rank if k_rank is not None else 0.0
            
            # Scenario Analysis
            print(f"\n   --- Scenario Analysis ---")   
            # 100% Vector
            print(f"   100% Vector Score: {v_score:.4f}")
            # 100% Keyword
            print(f"   100% Keyword Score: {k_score if k_score else 0.0:.4f}")
            # 70% Vector / 30% Keyword
            s_73 = v_score * 0.7 + (k_score if k_score else 0.0) * 0.3
            print(f"   70/30 Score: {s_73:.4f}")
            
            if final_score < 0.4:
                print("\n🔴 RESULT: Final score is likely below common thresholds (0.4-0.6).")
                print("   The document is effectively filtered out.")

if __name__ == "__main__":
    main()
