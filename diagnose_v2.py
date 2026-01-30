# coding=utf-8
"""深入诊断 search_vector 生成问题 - 重新向量化后"""
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
    print("=" * 70)
    print("深入诊断：重新向量化后 search_vector 分析")
    print("=" * 70)
    
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
    if paragraphs:
        p_id = str(paragraphs[0][0])
        p_content = paragraphs[0][2]
        print(f"段落ID: {p_id}")
        print(f"标题: {paragraphs[0][1]}")
        print(f"内容前200字: {p_content[:200]}...")
    else:
        print("未找到包含'注册地址'的段落！")
        return
    
    # 2. 查看这个段落的所有 embedding 记录
    print("\n【2】该段落的 embedding 记录 (重新向量化后)")
    cursor.execute("""
        SELECT 
            e.id,
            e.source_type,
            e.is_active,
            CASE WHEN e.embedding IS NULL THEN 'NULL' ELSE 'OK' END as vec,
            e.search_vector::text as sv
        FROM embedding e
        WHERE e.paragraph_id::text = %s
        ORDER BY e.source_type
    """, (p_id,))
    embeddings = cursor.fetchall()
    print(f"找到 {len(embeddings)} 条 embedding 记录\n")
    
    for e_id, source_type, is_active, vec, sv in embeddings:
        print(f"--- source_type={source_type} (0=问题,1=段落,2=标题,3=摘要) ---")
        print(f"  ID: {e_id}")
        print(f"  is_active: {is_active}, vector: {vec}")
        
        # 检查关键词
        has_zhuce = '注册' in sv
        has_dizhi = '地址' in sv
        has_beijing = '北京' in sv
        has_2025 = '2025' in sv
        
        print(f"  关键词检查: 注册={has_zhuce}, 地址={has_dizhi}, 北京={has_beijing}, 2025={has_2025}")
        print(f"  search_vector (前300字): {sv[:300]}...")
        print()
    
    # 3. 直接用 jieba 分词测试段落内容
    print("\n【3】本地 jieba 分词测试段落内容")
    import jieba
    # 只取前500字
    test_content = p_content[:500]
    result = jieba.lcut(test_content, cut_all=True)
    result_lower = [token.lower() for token in result if token.strip()]
    
    has_zhuce = '注册' in result_lower
    has_dizhi = '地址' in result_lower
    print(f"jieba 分词结果包含 '注册': {has_zhuce}")
    print(f"jieba 分词结果包含 '地址': {has_dizhi}")
    print(f"分词结果前50个: {result_lower[:50]}")
    
    # 4. 对比 to_ts_vector 函数输出
    print("\n【4】模拟 to_ts_vector 函数输出")
    ts_vector_output = " ".join(result_lower)
    print(f"to_ts_vector 模拟输出 (前300字): {ts_vector_output[:300]}...")
    
    # 5. 测试全文检索能否匹配
    print("\n【5】全文检索测试 (使用 OR 逻辑)")
    test_queries = [
        "注册",
        "地址", 
        "注册 | 地址",
        "爱才神 | 注册 | 地址",
        "北京 | 大兴"
    ]
    
    for query in test_queries:
        cursor.execute("""
            SELECT COUNT(*)
            FROM embedding e
            WHERE e.is_active = true
              AND e.search_vector @@ to_tsquery('simple', %s)
        """, (query,))
        count = cursor.fetchone()[0]
        print(f"  查询 '{query}': 匹配 {count} 条")
    
    # 6. 直接查看 source_type=1 的完整 search_vector
    print("\n【6】source_type=1 (PARAGRAPH) 完整 search_vector")
    cursor.execute("""
        SELECT e.search_vector::text
        FROM embedding e
        WHERE e.paragraph_id::text = %s AND e.source_type = 1
    """, (p_id,))
    result = cursor.fetchone()
    if result:
        sv_full = result[0]
        print(f"完整 search_vector:\n{sv_full}")
        print(f"\n总字符数: {len(sv_full)}")
    
    conn.close()
    print("\n" + "=" * 70)
    print("诊断完成")

if __name__ == "__main__":
    main()
