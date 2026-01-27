# Analyze and Optimize Retrieval Modes

- [x] Analyze Codebase for Retrieval Implementations
  - [x] `apps/knowledge/vector/pg_vector.py` (Vector & Blend Logic)
  - [x] `apps/knowledge/sql/blend_search.sql` (Blend SQL)
  - [x] Search for PageIndex implementation details
  - [x] `apps/knowledge/models/knowledge.py` (Data Models)
- [x] Evaluate Vector Search Optimization
  - [x] Check Chunking Logic (`apps/common/chunk/`)
  - [x] Check Indexing Strategy (HNSW vs IVFFlat)
  - [x] Check Query Parameters (top_k, distance)
- [x] Evaluate Blend Search Optimization
  - [x] Analyze Weighting Mechanism
  - [x] Analyze Keyword Extraction
- [x] Evaluate PageIndex Search Optimization
  - [x] Understand current implementation status
  - [x] Identify bottlenecks or missing features
- [x] Update Architecture Document
  - [x] Document Findings
  - [x] Propose Specific Code Changes
