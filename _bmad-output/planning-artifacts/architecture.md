---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - d:\code\v21\MaxKB\RAG_优化方案_召回率提升.md
  - d:\code\v21\MaxKB\MaxKB_RAG优化可行性分析报告.md
  - d:\code\v21\MaxKB\MaxKB_RAG优化使用指南.md
workflowType: 'architecture'
project_name: 'MaxKB'
user_name: 'liudong'
date: '2026-01-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**(Kept from previous analysis)**

## Retrieval Mode Analysis & Optimization Plan

### 1. Comprehensive Retrieval Mode Analysis

#### A. Vector Search (`embedding`)

* **Mechanism**: Cosine Distance via PGVector (`<=>` operator).
* **Chunking**: Fixed 256 chars (MarkChunkHandle).
* **Issues**:
  * **Context Loss**: 256 chars is too short for semantic completeness.
  * **No Keyword Match**: Fails on specific entity names (e.g., "ND-405 specs").
* **Verdict**: Weak as standalone default.

#### B. Full-Text Search (`keywords`)

* **Mechanism**: PostgreSQL `ts_rank_cd` with `websearch_to_tsquery('simple', ...)`.
* **Formula**: `rank * quality_factor * weight_factor`.
* **Issues**:
  * **Semantic Blindness**: Misses synonyms/concepts.
  * **Query Rigidness**: `websearch_to_tsquery` is strict; minor typos fail.
* **Verdict**: Useful only as a component of Blend, not standalone.

#### C. Blend Search (`blend`)

* **Mechanism**: Weighted sum of Vector Distance and Keyword Rank.
* **Existing Logic**:
  * ALREADY implements **Dynamic Weighting** based on query length (Code: `pg_vector.py:829`).
  * `< 5 chars`: 10% Vector / 90% Keyword.
  * `> 40 chars`: 65% Vector / 35% Keyword.
  * **Supports Override**: Checks `knowledge_meta.get('vector_weight')`.
* **Optimization**:
  * **Expose Configuration**: The logic exists, but UI lacks controls to tune these weights manually (per requirement).
  * **Formula**: `(%s * (1 - distance) + %s * ts_similarity)`.

#### D. PageIndex Search (`_try_page_index_search`)

* **Mechanism**: Pre-retrieval check. Finds `PageIndexNode` (tree nodes) matching title/content.
* **Logic**:
  * "Try-First" Strategy: If PageIndex hits, return results and SKIP standard search.
  * Fallback: If no hits, proceed to standard Vector/Blend.
* **Issues**:
  * **Isolation**: Results are not blended with standard search; it's a hard switch.
  * **Maintenance**: Requires explicit "PageIndex" build process.

### 2. Optimization Strategy (Phase 1)

#### Step 1: Foundational Data Layer (CRITICAL)

* **Action**: Switch from `MarkChunkHandle` (256) to **`OverlapChunkHandle` (800 chars + 400 overlap)**.
* **Why**: Solves the "Context Loss" in Vector/Blend modes.
* **Impact**: Requires full re-indexing of documents.

#### Step 2: Reranker Integration (High Impact)

* **Action**: Integrate Cross-Encoder Reranking into `base_search_dataset_step.py`.
* **Why**: Neither Vector, Keyword, nor Blend can match the precision of a Cross-Encoder.
* **Logic**: Retrieve Top-50 (cheap) -> Rerank -> Return Top-5 (expensive but accurate).

#### Step 3: Global Configuration (User Control)

* **Action**: Expose `vector_weight` and `keyword_weight` in Application Settings UI/API.
* **Why**: Users need control to override the default dynamic weights for specific domains (e.g., technical docs need more keyword weight).
