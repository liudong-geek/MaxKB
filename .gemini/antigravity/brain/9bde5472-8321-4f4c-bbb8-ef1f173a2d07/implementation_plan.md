# MaxKB RAG Optimization Implementation Plan

## Goal

Improve retrieval recall and hit rate by 30-40% through enhanced chunking, reranking integration, and optimized retrieval configurations.

## User Review Required
>
> [!IMPORTANT]
> **Data Re-indexing Required**: Implementing Overlap Chunking will require re-importing documents to take effect. Old chunks will remain until re-indexed.

## Proposed Changes

### 1. Chunking Optimization (Foundational)

#### [NEW] [overlap_chunk_handle.py](file:///d:/code/v21/MaxKB/apps/common/chunk/impl/overlap_chunk_handle.py)

- **Implement `OverlapChunkHandle`**:
  - Chunk Size: 800 characters (default)
  - Overlap: 400 characters (default)
  - Logic: Split by separators (sentences) while maintaining overlap.

#### [MODIFY] [**init**.py](file:///d:/code/v21/MaxKB/apps/common/chunk/__init__.py)

- **Register New Handler**: Add `OverlapChunkHandle` to the processing pipeline.

### 2. Reranker Integration (High Impact)

#### [MODIFY] [base_search_dataset_step.py](file:///d:/code/v21/MaxKB/apps/application/chat_pipeline/step/search_dataset_step/impl/base_search_dataset_step.py)

- **Integrate Cross-Encoder**:
  - Retrieve top 50 results (instead of top 3).
  - If Reranker enabled in settings, pass 50 results to Reranker.
  - Reranker filters and reorders to return top K (default 5).

### 3. Blend Search Configuration (User Control)

#### [MODIFY] [pg_vector.py](file:///d:/code/v21/MaxKB/apps/knowledge/vector/pg_vector.py)

- **Expose Weights**: Ensure `vector_weight` and `keyword_weight` from `Select Knowledge` settings are correctly prioritized over dynamic defaults.

## Verification Plan

### Automated Tests

- **Unit Test for Chunking**:
  - Create `tests/test_overlap_chunk.py`.
  - Content: Test text splitting with overlap, verifying boundary conditions and overlap length.
  - Command: `python tests/test_overlap_chunk.py` (Need to scaffold this simple runner).

- **Recall Regression Test**:
  - Use existing `test_retrieval_recall.py`.
  - Create `test_data/benchmark_queries.json` with 10-20 QA pairs.
  - Run before changes: `python test_retrieval_recall.py --knowledge-id <KID> --test-file test_data/benchmark_queries.json` (Record Baseline).
  - Run after changes: Re-run same command. Expected Recall@5 increase > 20%.

### Manual Verification

- **Log Verification**:
  - Trigger search in UI.
  - Check logs for `[Reranker] reranking 50 documents...` to confirm integration.
  - Check database `embedding` table for new chunks to verify size > 256.
