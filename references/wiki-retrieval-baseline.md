# Wiki Retrieval Baseline (2026-06-06)

Measured on an 83-page, 471KB wiki with 10,219 lines across 6 categories.

## Wiki Scale

| Category | Pages |
|---|---|
| concepts | 51 |
| entities | 24 |
| comparisons | 3 |
| plans | 3 |
| queries | 1 |
| analyses | 1 |
| **Total** | **83** |

## Growth Rate

| Metric | Value |
|---|---|
| Wiki age | 12 days (2026-05-25 → 2026-06-06) |
| Net new pages | ~53 |
| Organic daily rate | 4.4 pages/day |
| 150-page warning | 2026-06-21 (15 days) |
| 200-page break | 2026-07-02 (26 days) |

## Token Cost (per query)

| Component | Est. tokens |
|---|---|
| index.md (5,551 chars) | ~1,850–3,100 |
| Reading top-5 grep results | ~4,200 |
| **Total per query** | **~6,000** |

## Grep Retrieval Quality

### Test queries (7 total)

| Query | Target page | Result |
|---|---|---|
| `Ebbinghaus` | llm-wiki-vs-agentmemory | ✅ #1/5 |
| `gh.idayer` | github-access-cn | ✅ #1/4 |
| `Context Rot` | ultra-long-context-paradox | ✅ #2/3 |
| `SOW.*失效` (regex) | wyckoff-core-events | ✅ #4/7 |
| `Graphiti` | agent-memory-systems | ✅ #5/8 |
| `agentmemory` | agent-memory-systems | ❌ not in top 10 |
| `威科夫` | wyckoff-core-events | ❌ first wyckoff page at #46 |

### 🔴 Thematic query failure: "威科夫"

```
50 grep matches total
First wyckoff analysis page: rank #46
45 noise pages before first relevant result
Precision@46: 2.2%

Top noise (pages that mention "威科夫" once in passing):
  #1  excalidraw
  #2  diandian-ai
  #4  hermes-skills
  #5  hermes-agent-server
  #9  stock-data-api
  #10 index
```

**Root cause:** grep ranks by file path and match count, not by relevance. A page that mentions "威科夫" 50 times (actual analysis) is not ranked above a page that mentions it once (passing reference), because output ordering is not relevance-sorted.

### When grep works

- **Exact unique terms**: `Ebbinghaus`, `gh.idayer`, `CLIP` — terms that appear in few pages
- **Regex with specific context**: `SOW.*失效`
- **English technical terms** in a Chinese-majority wiki: less collision

### When grep fails

- **Broad topic keywords** with high fan-out: `威科夫`, `记忆`, `搜索`
- **Semantically related but textually different**: "agentmemory" vs "Agent 记忆系统"
- **Queries that need concept matching**, not string matching

## Implications

1. At 83 pages, thematic queries are already broken — not at the 200-page "index.md limit" previously assumed.
2. The `index.md` + `search_files` pattern needs augmentation with relevance-ranked retrieval for wikis above ~50 pages.
3. Hybrid search (BM25 + embedding + RRF fusion) is not a future nice-to-have — it's needed now.

## BM25: Quantified Improvement (2026-06-06)

Tested `rank-bm25` (8KB pip install, pure Python) against the same 83-page wiki with the same queries:

| Query | Grep (first relevant) | BM25 (first relevant) | Improvement |
|---|---|---|---|
| 威科夫 | #46 | #1 | **46×** |
| agent memory 记忆系统 | not found | #1 | rescued |
| 混合搜索 | — | #1 | — |
| GitHub 镜像 国内 | #1 | #1 | tied |
| 三层记忆 上下文 | #2 | #1 | 2× |

BM25-only (no embeddings, no vectors, no knowledge graph) already solves the grep crisis. Estimated implementation: ~255 lines of Python, ~50MB memory, <2s full index rebuild (83 pages).

Embedding stream (sentence-transformers + all-MiniLM-L6-v2) adds ~90MB model + ~90MB runtime memory for marginal gains at this wiki scale.
