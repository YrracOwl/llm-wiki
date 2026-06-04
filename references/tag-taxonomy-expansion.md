# Tag Taxonomy Expansion — Batch Workflow

When `wiki_op.py lint` reports many "Tags not in taxonomy" warnings, follow this workflow.

## Step 1: Collect all missing tags

```bash
python3 ~/wiki/.hermes/scripts/wiki_op.py lint 2>&1 \
  | grep 'Tags not in taxonomy' \
  | sed 's/.*Tags not in taxonomy: //' \
  | sed 's/\. Valid:.*//' \
  | tr ',' '\n' | sed 's/^ *//' | sort -u
```

This extracts every unique tag that exists on pages but not in SCHEMA.md's taxonomy.

## Step 2: Categorize

Group tags by which taxonomy section they belong to:
- **Agent 与 AI 系统** — AI/LLM/agent/programming tags
- **投资与市场** — investing/market tags
- **半导体与工程** — semiconductor/radiation/process tags
- **平台与数据** — platform/service tags
- **方法论与知识** — methodology tags
- **内容与兴趣** — content/hobby tags
- **工具与配置** — tool/config tags

## Step 3: Add to SCHEMA.md

Patch `~/wiki/SCHEMA.md` — add new tags to the appropriate category sections.
Keep the existing tag ordering; append new ones to each category line.

Example patch structure:
```
### 半导体与工程
semiconductor, 半导体, electronics, ..., SEE, ELDRS,
+SEGR, SEB, SEL, SEU, SET, SEFI, MBU, SHE,
```

## Step 4: Verify

```bash
python3 ~/wiki/.hermes/scripts/wiki_op.py lint
```

Expected: `✅ Wiki lint passed — no issues found.`

## When to skip

- One-off page tags that won't be reused — fix the PAGE instead (remove/rename the tag)
- Tags that duplicate existing ones (e.g., `a-share` vs existing `a-stock`) — decide: add or deduplicate
