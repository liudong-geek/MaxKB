
import os
import django
import sys
import json
from django.db.models import Q

# Add apps to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from knowledge.vector.pg_vector import BlendSearch, SearchMode, PGVector
from knowledge.models import Embedding, Knowledge

def debug_query():
    query_text = "首席专家 余昱钧"
    print(f"\n[Debug] Query: {query_text}")
    print(f"[Debug] Length: {len(query_text)}")
    
    # 1. Check Weights
    searcher = BlendSearch()
    # Mock behavior to see weights logic (copy-paste logic for verify)
    query_length = len(query_text.strip())
    if query_length <= 5:
        w_vec, w_kw = 0.1, 0.9
    elif query_length <= 10:
        w_vec, w_kw = 0.2, 0.8
    elif query_length <= 20:
        w_vec, w_kw = 0.35, 0.65
    else:
        w_vec, w_kw = 0.65, 0.35
    print(f"[Debug] Calculated Weights -> Vector: {w_vec}, Keyword: {w_kw}")
    
    # 2. Run Actual Search
    print("\n[Debug] Running BlendSearch...")
    # Get all embeddings (as we don't know the knowledge id easily, we just filter active)
    query_set = Embedding.objects.filter(is_active=True)
    count = query_set.count()
    print(f"[Debug] Total Embeddings in DB: {count}")
    
    if count == 0:
        print("[Error] No embeddings in DB!")
        return

    # Use a dummy embedding (random or zero) just to test the pipeline
    # In reality, pg_vector needs an embedding. We will try to fetch an existing one?
    # Or just use a zero vector if the model dimension is known (usually 1536 for OpenAI)
    # Let's try to get one from DB to check dimension
    first_emb = query_set.first()
    dim = len(first_emb.embedding) if first_emb else 1536
    query_embedding = [0.0] * dim
    
    try:
        results = searcher.handle(
            query_set=query_set,
            query_text=query_text,
            query_embedding=query_embedding,
            top_number=10,
            similarity=0.4, # Lower threshold to see what's caught
            search_mode=SearchMode.blend
        )
        
        print(f"\n[Debug] Search Results: {len(results)}")
        for i, res in enumerate(results):
            print(f"[{i+1}] ID: {res.get('id')} | Score: {res.get('comprehensive_score')} | Sim: {res.get('similarity')}")
            # Try to print document name if possible
            # We need to fetch paragraph content or title to verify
            # Note: The result object from raw sql might not have all fields populated in Django Object
            # It's a dict.
            
    except Exception as e:
        print(f"[Debug] Search Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_query()
