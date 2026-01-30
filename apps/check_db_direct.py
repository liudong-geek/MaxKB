
import psycopg2
import sys

# User provided credentials
DB_HOST = "10.80.17.190"
DB_PORT = 5433
DB_USER = "root"
DB_PASS = "Password123@postgres"

def get_connection(dbname="postgres"):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=dbname
        )
        return conn
    except Exception as e:
        print(f"[ERROR] Connection to {dbname} failed: {e}")
        return None

def main():
    print(f"=== Connecting to DB Server {DB_HOST}:{DB_PORT} ===", flush=True)
    
    # 1. Discover Databases
    conn = get_connection()
    if not conn:
        return
        
    target_db = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = [row[0] for row in cur.fetchall()]
        print(f"Available Databases: {dbs}", flush=True)
        
        # Heuristic to find MaxKB db
        for name in dbs:
            if 'maxkb' in name.lower():
                target_db = name
                break
        
        # Fallback
        if not target_db and 'maxkb' not in dbs:
            # Maybe it's named something else? Let's check 'postgres' or look for specific tables later?
            # User said "MaxKB", so likely maxkb.
            if 'postgres' in dbs:
                 # If no maxkb, maybe tables are in postgres db? (Unlikely but possible for docker)
                 target_db = 'postgres'
    finally:
        conn.close()
        
    if not target_db:
        print("[ERROR] Could not identify MaxKB database.", flush=True)
        return

    print(f"=== Analyzing Database: {target_db} ===", flush=True)
    
    # 2. Check Data
    conn = get_connection(dbname=target_db)
    if not conn:
        return
        
    try:
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("SELECT to_regclass('public.paragraph');")
        if not cur.fetchone()[0]:
             print(f"[ERROR] Table 'paragraph' not found in {target_db}. Wrong DB?", flush=True)
             return

        # A. Find '首席专家' Paragraph
        print("\n[Step 1] Finding Paragraph...", flush=True)
        cur.execute("SELECT id, content FROM paragraph WHERE content LIKE '%首席专家%' LIMIT 1;")
        row = cur.fetchone()
        
        if not row:
            print("[FAIL] Paragraph '首席专家' NOT FOUND in DB. Data might be missing.", flush=True)
            return
            
        para_id, content = row
        print(f"   Found Paragraph ID: {para_id}", flush=True)
        print(f"   Content Preview: {content[:50]}...", flush=True)
        
        # B. Find Embedding
        print("\n[Step 2] Finding Embedding...", flush=True)
        cur.execute(f"SELECT id, page_index_node_id, length(embedding) FROM embedding WHERE paragraph_id = '{para_id}';")
        emb_row = cur.fetchone()
        
        if not emb_row:
             print("[FAIL] No Embedding found for this paragraph! (Re-indexing pending?)", flush=True)
             return
             
        emb_id, node_id, vec_len = emb_row
        print(f"   Embedding ID: {emb_id}", flush=True)
        
        # C. Verify Logic
        print("\n[Step 3] Verifying Context Logic...", flush=True)
        if node_id:
            print(f"[PASS] page_index_node_id is SET to: {node_id}", flush=True)
            print("   Conclusion: The new code IS ACTIVE and context was injected.", flush=True)
        else:
            print(f"[FAIL] page_index_node_id is NULL.", flush=True)
            print("   Conclusion: The new code was NOT used. Service likely NOT restarted or task not re-run.", flush=True)
            
    except Exception as e:
        print(f"[ERROR] Query failed: {e}", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
