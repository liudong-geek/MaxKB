SELECT paragraph_id,
	comprehensive_score,
	comprehensive_score AS similarity
FROM (
		SELECT DISTINCT ON ("paragraph_id") (
				(
					%s * vector_similarity + %s * normalized_ts_similarity
				) * (
					1 + COALESCE((meta->>'quality_score')::float, 0) * 0.05
				) * (
					1 + COALESCE((meta->>'source_weight')::float, 0) * 0.1
				)
			) as similarity,
			*,
			(
				(
					%s * vector_similarity + %s * normalized_ts_similarity
				) * (
					1 + COALESCE((meta->>'quality_score')::float, 0) * 0.05
				) * (
					1 + COALESCE((meta->>'source_weight')::float, 0) * 0.1
				)
			) AS comprehensive_score
		FROM (
				SELECT *,
					-- 向量相似度：1 - distance，范围 [0, 1]
					(1 - (embedding.embedding::vector(%s) <=> %s)) as vector_similarity,
					-- 全文相似度：ts_rank_cd 归一化到 [0, 1]
					-- ts_rank_cd 典型范围是 0-0.5，乘以 2 后映射到 0-1
					-- 使用 LEAST 确保不超过 1
					-- 使用非线性归一化：x / (x + 0.1)
					-- 0.1 -> 0.5, 0.5 -> 0.83, 1.0 -> 0.91
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
					) AS normalized_ts_similarity
				FROM embedding $ { embedding_query }
			) TEMP
		ORDER BY paragraph_id,
			similarity DESC
	) DISTINCT_TEMP
WHERE comprehensive_score > %s
ORDER BY comprehensive_score DESC
LIMIT %s