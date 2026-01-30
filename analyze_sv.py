# coding=utf-8
"""深入分析 search_vector 来源"""
import psycopg2

DB_CONFIG = {
    "host": "10.80.17.190",
    "port": 5433,
    "user": "root",
    "password": "Password123@postgres",
    "database": "maxkb"
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("=" * 60)
    print("search_vector 来源分析")
    print("=" * 60)
    
    # 1. 查找包含"注册地址"的段落
    print("\n【1】找到包含'注册地址'的段落")
    cursor.execute("""
        SELECT 
            p.id,
            p.title,
            p.content
        FROM paragraph p
        WHERE p.content LIKE '%注册地址%'
        LIMIT 2
    """)
    paragraphs = cursor.fetchall()
    for p_id, title, content in paragraphs:
        print(f"\n段落ID: {p_id}")
        print(f"标题: {title}")
        print(f"内容(前300字): {content[:300]}...")
    
    # 2. 查找这个段落对应的 embedding 记录
    if paragraphs:
        p_id = paragraphs[0][0]
        print(f"\n【2】查找段落 {p_id} 的 embedding 记录")
        cursor.execute("""
            SELECT 
                e.id,
                e.source_type,
                e.source_id,
                e.meta,
                e.search_vector::text as sv
            FROM embedding e
            WHERE e.paragraph_id::text = %s
        """, (str(p_id),))
        embeddings = cursor.fetchall()
        print(f"找到 {len(embeddings)} 条 embedding 记录")
        for e_id, source_type, source_id, meta, sv in embeddings:
            print(f"\n  Embedding ID: {e_id}")
            print(f"  source_type: {source_type}")
            print(f"  source_id: {source_id}")
            print(f"  meta: {meta}")
            print(f"  search_vector: {sv[:300]}...")
        
        # 3. 检查 search_vector 是否包含 content 中的关键词
        print(f"\n【3】检查 search_vector 是否反映段落内容")
        content = paragraphs[0][2]
        # 检查一些应该存在的词
        check_words = ['注册', '地址', '北京', '大兴', '2025']
        if embeddings:
            sv = embeddings[0][4]
            for word in check_words:
                exists = word in sv
                in_content = word in content
                print(f"  '{word}': 在content={in_content}, 在search_vector={exists}")
    
    # 4. 检查 embedding 表的 meta 字段
    print(f"\n【4】检查 embedding 的 meta 字段结构")
    cursor.execute("""
        SELECT 
            e.id,
            e.meta
        FROM embedding e
        WHERE e.paragraph_id IS NOT NULL
        LIMIT 3
    """)
    for e_id, meta in cursor.fetchall():
        print(f"  ID: {e_id}")
        print(f"  Meta: {meta}")
        print("-" * 40)
    
    # 5. 查询直接看完整内容
    print(f"\n【5】查看段落ID为包含'注册地址'的段落完整 content (截取500字)")
    if paragraphs:
        print(f"\n原始 content:\n{paragraphs[0][2][:500]}")
    
    conn.close()

if __name__ == "__main__":
    main()
