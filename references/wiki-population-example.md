# Wiki Population from Past Sessions (Bulk Initialization)

When initializing a new wiki, **session_search** is the most efficient way to mine existing knowledge from past agent conversations.

## Workflow

### Phase 1: Reconnaissance (parallel searches)
Run 3-5 `session_search` calls in parallel with broad OR queries covering the domain's key topics:

```
session_search("keyword1 OR keyword2 OR keyword3", limit=5)
session_search("topic_A OR topic_B", limit=5)
session_search("pitfall OR 坑 OR 经验 OR workflow", limit=5)
```

Each returns session summaries with accurate technical details, timestamps, and outcomes.

### Phase 2: Categorization
From the search results, extract:
- **Entities**: tools, services, platforms, data sources, APIs
- **Concepts**: workflows, methodologies, theories, strategies
- **Comparisons**: side-by-side analyses of alternatives
- **Pitfalls**: lessons learned, gotchas, workarounds

Also check `persistent memory` for stable facts that span sessions.

### Phase 3: Batch creation
1. Create **SCHEMA.md** first — define the domain and tag taxonomy
2. Create all **entity pages** in one pass (use parallel write_file calls)
3. Create all **concept pages** in one pass
4. Create **comparison pages** if any
5. Write **index.md** with all entries, alphabetically sorted by section
6. Write **log.md** with a single creation entry listing all pages

### Phase 4: Cross-reference
Ensure every page has ≥2 `[[wikilinks]]` to other pages. Key pages (like the server environment or main workflow) should be linked from most other pages.

## Example: Hermes Agent Practice Wiki

A 30-page wiki was initialized from:
- 5 `session_search` calls across topics (skills, browser, news, cron, stock)
- Persistent memory extraction
- ~3 session summaries analyzed per search

Result: 12 entities + 12 concepts + 1 comparison + schema/index/log = 28 pages, ~156KB.

## Key tips
- **Search broadly**: Use OR between keywords; AND (FTS5 default) misses relevant sessions
- **Cross-reference memory**: Memory has stable facts; session_search has detailed procedures
- **Don't duplicate**: Check if the skill's own SKILL.md already covers a topic before creating a page
- **Tag first, write later**: Define the full tag taxonomy in SCHEMA.md before writing any page
