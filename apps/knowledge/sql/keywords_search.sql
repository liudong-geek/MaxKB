SELECT paragraph_id,
	comprehensive_score,
	comprehensive_score as similarity
FROM (
		SELECT DISTINCT ON ("paragraph_id") (similarity),
			*,
			similarity * (
				1 + COALESCE((meta->>'quality_score')::float, 0) * 0.05
			) * (
				1 + COALESCE((meta->>'source_weight')::float, 0) * 0.1
			) AS comprehensive_score
		FROM (
				SELECT *,
					ts_rank_cd(
						embedding.search_vector,
						plainto_tsquery('simple', %s),
						32
					) AS similarity
				FROM embedding $ { keywords_query }
			) TEMP
		ORDER BY paragraph_id,
			similarity DESC
	) DISTINCT_TEMP
WHERE comprehensive_score > %s
ORDER BY comprehensive_score DESC
LIMIT %s