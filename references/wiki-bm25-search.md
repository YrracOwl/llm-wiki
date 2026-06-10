# Wiki BM25 Search Integration

> Added 2026-06-06 | Replaces grep-based retrieval as primary search mechanism.

## Why BM25

grep fails catastrophically for thematic queries on our wiki at 83 pages:

| Query | grep first relevant | BM25 first relevant |
|---|---|---|
| 威科夫 | #46 (2.2% precision) | #1 |
| agent 记忆 | not found | #1 |
| 混合搜索 | N/A | #1 |
| GitHub 镜像 | #1 | #1 |
| 三层记忆 | #2 | #1 |

BM25 uses term frequency × inverse document frequency to rank pages by
relevance, not by file path or match count.

## Usage

### Search (Agent context injection)

```bash
python3 ~/.hermes/scripts/wiki_search.py --agent "<query>"
# Returns compact top-5 wikilinks for context injection
```

### Search (JSON for programmatic use)

```bash
python3 ~/.hermes/scripts/wiki_search.py --json "<query>"
```

### Rebuild index

```bash
python3 ~/.hermes/scripts/wiki_search.py --rebuild-only
# Rebuilds from scratch (~2s for 83 pages)
```

## Integration into llm-wiki Query flow

When the Agent loads `llm-wiki` skill and performs a Query:

1. **First**: run `wiki_search.py --agent "<query>"` — returns ranked top-5
2. **Then**: read the top 2-3 pages using `read_file`
3. **Fallback**: for wikis under 50 pages, `index.md` still works as a navigational aid

The old `search_files` (grep) should NOT be used as primary retrieval for
thematic queries. It remains useful for exact keyword lookups (e.g., finding
which pages mention a specific function name).

## Index maintenance

```bash
# Cron job (daily, after stale_check):
python3 ~/.hermes/scripts/wiki_search.py --rebuild-only
```

The index auto-rebuilds when:
- Older than 24 hours
- Wiki pages have changed (checksum mismatch)
- `--rebuild` flag is passed

## Dependencies

```
pip install rank-bm25  # 8KB, pure Python, no native deps
```

## Architecture

```
~/.hermes/scripts/wiki_search.py   (~250 lines)
~/.hermes/wiki_index/
  ├── bm25_index.pkl               (BM25Okapi, pickled)
  └── bm25_meta.json               (checksum, timestamp)
```
