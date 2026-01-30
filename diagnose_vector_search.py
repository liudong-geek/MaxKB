# coding=utf-8
"""向量检索诊断脚本v2"""
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
    print("向量检索诊断 v2")
    print("=" * 60)
    
    # 1. 检查 embedding 表结构
    print("\n【诊断1】embedding 表结构")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'embedding'
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # 2. 统计 embedding 状态
    print("\n【诊断2】embedding 统计")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_vector,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active
        FROM embedding
    """)
    row = cursor.fetchone()
    print(f"  总数: {row[0]}, 有向量: {row[1]}, 活跃: {row[2]}")
    
    # 3. 检查"爱才神"相关段落的 embedding
    print("\n【诊断3】'爱才神'段落的 embedding 状态")
    cursor.execute("""
        SELECT 
            e.id,
            e.paragraph_id,
            e.is_active,
            CASE WHEN e.embedding IS NULL THEN 'NULL' ELSE 'OK' END as vec,
            LEFT(e.search_vector::text, 80) as sv
        FROM embedding e
        JOIN paragraph p ON e.paragraph_id::text = p.id::text
        WHERE p.content LIKE '%注册地址%'
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  ID: {row[0]}, Active: {row[2]}, Vec: {row[3]}")
        print(f"  SearchVector: {row[4]}...")
    
    # 4. 测试全文检索 (OR逻辑)
    print("\n【诊断4】全文检索测试")
    test_query = "爱才神 | 注册 | 地址"
    cursor.execute("""
        SELECT 
            e.id,
            e.paragraph_id,
            ts_rank_cd(e.search_vector, to_tsquery('simple', %s), 32) as rank
        FROM embedding e
        WHERE e.is_active = true
          AND e.search_vector @@ to_tsquery('simple', %s)
        ORDER BY rank DESC
        LIMIT 10
    """, (test_query, test_query))
    results = cursor.fetchall()
    print(f"  查询: {test_query}")
    print(f"  匹配数: {len(results)}")
    for row in results:
        print(f"    ID:{row[0]}, Para:{row[1]}, Rank:{row[2]:.4f}")
    
    # 5. 测试向量相似度 (需要先获取查询向量)
    print("\n【诊断5】向量相似度分析")
    print("  (需要查询向量，此处仅检查向量是否存在)")
    
    cursor.execute("""
        SELECT 
            e.id,
            e.paragraph_id,
            vector_dims(e.embedding::vector) as dims
        FROM embedding e
        JOIN paragraph p ON e.paragraph_id::text = p.id::text
        WHERE p.content LIKE '%注册地址%'
          AND e.embedding IS NOT NULL
        LIMIT 3
    """)
    for row in cursor.fetchall():
        print(f"  ID: {row[0]}, Dims: {row[2]}")
    
    # 6. 检查 search_vector 是否包含关键词
    print("\n【诊断6】search_vector 中是否有'注册地址'关键词")
    cursor.execute("""
        SELECT 
            e.id,
            e.search_vector::text as sv
        FROM embedding e
        JOIN paragraph p ON e.paragraph_id::text = p.id::text
        WHERE p.content LIKE '%注册地址%'
        LIMIT 2
    """)
    for row in cursor.fetchall():
        sv = str(row[1])
        has_zhuce = '注册' in sv
        has_dizhi = '地址' in sv
        print(f"  ID: {row[0]}, 含'注册': {has_zhuce}, 含'地址': {has_dizhi}")
        print(f"  完整SV: {sv[:200]}...")
    
    conn.close()
    print("\n诊断完成")

if __name__ == "__main__":
    main()
