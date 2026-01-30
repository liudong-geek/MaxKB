
import os
import django
import sys
import json
from unittest.mock import MagicMock, patch

# Add apps to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from knowledge.vector.pg_vector import BlendSearch, SearchMode, PGVector
from common.utils.ts_vecto_util import to_query

def simulate_search_issue():
    print("=== Simulation: Diagnosing 'Chief Expert' Retrieval Failure ===")
    
    query_text = "首席专家 余昱钧"
    # Mock Embedding (1536 dim)
    query_embedding = [0.001] * 1536 
    
    # 1. Simulate Weights Logic
    print("\n[1] Dynamic Weights Calculation:")
    searcher = BlendSearch()
    # Copy logic for verification
    query_length = len(query_text.strip())
    # ... (Logic from Code)
    if query_length <= 5:
        w_vec, w_kw = 0.1, 0.9
    elif query_length <= 10:
        w_vec, w_kw = 0.2, 0.8
    elif query_length <= 20:
        w_vec, w_kw = 0.35, 0.65
    else:
        w_vec, w_kw = 0.65, 0.35
        
    print(f"Query Length: {query_length}")
    print(f"Weights -> Vector: {w_vec}, Keyword: {w_kw}")
    
    # 2. Simulate Candidate Scoring
    print("\n[2] Candidate Scoring Simulation:")
    # Scenario: 
    # Document exists. 
    # Keyword Search finds it (Score 0.84 normalized).
    # Vector Search fails to find it or has very low score (e.g., 0.1) due to missing context.
    
    # Let's say we retrieved this candidate via Keyword Index
    candidate_id = "doc_123"
    vector_score_raw = 0.25 # Distance (1 - 0.75) -> Low similarity
    keyword_score_raw = 0.84 # Normalized Rank -> High match
    
    # Old Logic Score
    old_score = vector_score_raw * 0.5 + keyword_score_raw * 0.5
    print(f"Old Logic Score: {vector_score_raw}*0.5 + {keyword_score_raw}*0.5 = {old_score:.4f}")
    print(f"Threshold 0.6 -> {'PASS' if old_score > 0.6 else 'FAIL'}")
    
    # New Logic Score
    new_score = vector_score_raw * w_vec + keyword_score_raw * w_kw
    print(f"New Logic Score: {vector_score_raw}*{w_vec} + {keyword_score_raw}*{w_kw} = {new_score:.4f}")
    print(f"Threshold 0.6 -> {'PASS' if new_score > 0.6 else 'FAIL'}")
    
    # 3. Simulate Context Impact
    print("\n[3] Context Injection Impact:")
    # If we re-index, Vector Score should improve.
    # Assume context raises vector similarity to 0.75
    improved_vector_score = 0.75
    
    improved_total_score = improved_vector_score * w_vec + keyword_score_raw * w_kw
    print(f"Improved Score: {improved_vector_score}*{w_vec} + {keyword_score_raw}*{w_kw} = {improved_total_score:.4f}")
    print(f"Threshold 0.6 -> {'PASS' if improved_total_score > 0.6 else 'FAIL'}")

    # 4. Verify Codebase Logic (Mocked Run)
    print("\n[4] Running BlendSearch.handle with Mock DB...")
    
    with patch('knowledge.vector.pg_vector.generate_sql_by_query_dict') as mock_gen_sql, \
         patch('knowledge.vector.pg_vector.select_list') as mock_select:
             
        # Mock Candidate Generation (Vector returns nothing, Keyword returns doc_123)
        # Vector SQL call
        mock_gen_sql.side_effect = [
            ("SELECT vector_cand", []),    # Vector SQL
            ("SELECT keyword_cand", []),   # Keyword SQL
            ("SELECT rerank_sql", [])      # Rerank SQL
        ]
        
        # Select List Returns
        mock_select.side_effect = [
            [], # Vector Candidates: Empty (Simulating vector search failure)
            [{'id': 'doc_123', 'search_vector': '...'}], # Keyword Candidates: Found it
            [{'id': 'doc_123', 'comprehensive_score': new_score, 'similarity': new_score}] # Final Result
        ]
        
        try:
            results = searcher.handle(
                query_set=MagicMock(),
                query_text=query_text,
                query_embedding=query_embedding,
                top_number=5,
                similarity=0.6,
                search_mode=SearchMode.blend
            )
            print(f"Results Found: {len(results)}")
            if results:
                print(f"Top Result Score: {results[0]['comprehensive_score']}")
            else:
                print("No results found (Filtered by threshold?)")
                
        except Exception as e:
            print(f"Execution Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    simulate_search_issue()
