# Phase 05 Research

## Findings

- Wiki benchmark flow is split into:
  1) `wikimultihop_ingest.py` for episodic ingest
  2) `wikimultihop_search.py` for retrieval + QA evaluation
- Dataset source exists locally at `evaluation/data/wikimultihop.json`.
- Result JSON includes per-question retrieval metrics and aggregate final matrix
  (`wiki_final_matrix`) suitable for gate report extraction.
