SELECT paragraph_id,
	comprehensive_score,
	comprehensive_score as similarity
FROM (
		SELECT DISTINCT ON ("paragraph_id") (normalized_similarity),
			*,
			normalized_similarity * (
				1 + COALESCE((meta->>'quality_score')::float, 0) * 0.05
			) * (
				1 + COALESCE((meta->>'source_weight')::float, 0) * 0.1
			) AS comprehensive_score
		FROM (
				SELECT *,
					-- 全文相似度：ts_rank_cd 归一化到 [0, 1]
					-- ts_rank_cd 典型范围是 0-0.5，乘以 2 后映射到 0-1
					-- 使用非线性归一化：x / (x + 0.1)
					(
						ts_rank_cd(
							embedding.search_vector,
							to_tsquery('simple', %s),
							32
						) / (
							ts_rank_cd(
								embedding.search_vector,
								to_tsquery('simple', %s),
								32
							) + 0.1
						)
					) AS normalized_similarity
				FROM embedding $ { keywords_query }
			) TEMP
		ORDER BY paragraph_id,
			normalized_similarity DESC
	) DISTINCT_TEMP
WHERE comprehensive_score > %s
ORDER BY comprehensive_score DESC
LIMIT %s