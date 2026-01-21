SELECT
    paragraph_id,
	comprehensive_score,
	comprehensive_score as similarity
FROM
	(
	SELECT DISTINCT ON
		("paragraph_id")
		(1 - distance) * (1 + COALESCE((meta->>'quality_score')::float, 0) * 0.05) * (1 + COALESCE((meta->>'source_weight')::float, 0) * 0.1) AS comprehensive_score,

		*
	FROM
		( SELECT *, ( embedding.embedding::vector(%s) <=>  %s ) AS distance FROM embedding ${embedding_query} ORDER BY distance) TEMP
	ORDER BY
		paragraph_id,
		comprehensive_score DESC

	) DISTINCT_TEMP
WHERE comprehensive_score>%s
ORDER BY comprehensive_score DESC
LIMIT %s