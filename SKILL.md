---
name: llm-wiki
description: "Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Use when user asks to ingest sources, update the wiki, query compiled knowledge, lint for consistency, create a knowledge base, or add notes. All writes go through wiki_op.py unified CLI."
version: 2.3.2
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative]
    category: research
    related_skills: [obsidian, arxiv, agentic-research-ideas]
    config:
      - key: wiki.path
        description: Path to the LLM Wiki knowledge base directory
        default: "~/wiki"
        prompt: Wiki directory path
---

# Karpathy's LLM Wiki

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.
Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike traditional RAG (which rediscovers knowledge from scratch per query), the wiki
compiles knowledge once and keeps it current. Cross-references are already there.
Contradictions have already been flagged. Synthesis reflects everything ingested.

**Division of labor:** The human curates sources and directs analysis. The agent
summarizes, cross-references, files, and maintains consistency.

> 📚 Wiki: [[agent-memory-systems]] — Agent 记忆系统调研，Wiki 互补方案对比
> 📚 Wiki: [[rag-vs-llm-wiki]] — RAG vs LLM Wiki 对比分析
> 📚 Wiki: [[ultra-long-context-paradox]] — 上下文腐烂与三层记忆轴

## When This Skill Activates

Use this skill when the user:
- Asks to create, build, or start a wiki or knowledge base
- Asks to ingest, add, or process a source into their wiki
- Asks a question and an existing wiki is present at the configured path
- Asks to lint, audit, or health-check their wiki
- References their wiki, knowledge base, or "notes" in a research context

> ⚠️ **Line count**: This skill is ~545 lines, over the 300-line target. This is intentional as a **domain knowledge skill** — the Core Operations (Ingest/Query/Lint with command templates), sync checklist, core protocols, and pitfall catalog are all **operational dependencies** the Agent needs at decision time. Init-time templates and Obsidian setup have been moved to `references/wiki-templates.md` (saving ~175 lines). The BM25 gate and write gate markers (🚨) ensure critical rules aren't buried.

## Wiki Location

Configured via `skills.config.wiki.path` in `~/.hermes/config.yaml` (prompted
during `hermes config migrate` or `hermes setup`):

```yaml
skills:
  config:
    wiki:
      path: ~/wiki
```

Falls back to `~/wiki` default. The resolved path is injected when this
skill loads — check the `[Skill config: ...]` block above for the active value.

The wiki is just a directory of markdown files — open it in Obsidian, VS Code, or
any editor. No database, no special tooling required.

## Architecture: Four Layers + Tools

```
wiki/
├── SCHEMA.md           # Conventions, structure rules, domain config (+time/ADD-only/Skill)
├── index.md            # Sectioned content catalog with one-line summaries
├── log.md              # Chronological action log (append-only, rotated yearly)
├── raw/                # Layer 1: Immutable source material
│   ├── articles/       # Web articles, clippings
│   ├── papers/         # PDFs, arxiv papers
│   ├── transcripts/    # Meeting notes, interviews
│   └── assets/         # Images, diagrams referenced by sources
├── entities/           # Layer 2: Entity pages (people, orgs, products, models)
├── concepts/           # Layer 2: Concept/topic pages
├── comparisons/        # Layer 2: Side-by-side analyses
├── queries/            # Layer 2: Filed query results worth keeping
├── .hermes/
│   ├── plans/          # Implementation plans for wiki evolution
│   ├── scripts/        # Tool scripts (consolidated into wiki_op.py subcommands)
│   └── visits.db       # SQLite side-channel visit counter (no write amplification)
├── _versions/          # ADD-only version snapshots (per-page, timestamped)
├── _aliases/           # Entity alias index (entities.json)
└── skills/             # Skill-Wiki bridge: knowledge distillation + mapping
```

**Layer 0 — Ecosystem Tools:** `$WIKI/.hermes/scripts/` contains the tool suite. **`wiki_op.py` is the unified CLI entry point** (create/update/delete/lint/search/stale/entities/bridge/visits/snapshot) — all write and query operations go through it. Individual scripts have been consolidated into `wiki_op.py` subcommands. See `references/evolution-tools.md` for the full tool reference.
**Layer 1 — Raw Sources:** Immutable. The agent reads but never modifies these.
**Layer 2 — The Wiki:** Agent-owned markdown files. Created, updated, and cross-referenced by the agent.
**Layer 3 — The Schema:** `SCHEMA.md` defines structure, conventions, tag taxonomy, and all protocols.
**Layer 4 — Skill Bridge:** `skills/_mapping.md` and `_aliases/entities.json` bridge wiki knowledge ↔ Hermes skills.

## Resuming an Existing Wiki (CRITICAL — do this every session) ⚡

When the user has an existing wiki, **always orient yourself before doing anything**:

① **Read `SCHEMA.md`** — understand the domain, conventions, and tag taxonomy.
② **Read `index.md`** — learn what pages exist and their summaries.
③ **Scan recent `log.md`** — read the last 20-30 entries to understand recent activity.

```bash
WIKI="${wiki_path:-$HOME/wiki}"
# Orientation reads at session start
read_file "$WIKI/SCHEMA.md"
read_file "$WIKI/index.md"
read_file "$WIKI/log.md" offset=<last 30 lines>
```

Only after orientation should you ingest, query, or lint. This prevents:
- Creating duplicate pages for entities that already exist
- Missing cross-references to existing content
- Contradicting the schema's conventions
- Repeating work already logged

For wikis with 50+ pages, BM25 search is mandatory before creating anything new:
```bash
python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py search "<topic>" --agent
```
This catches existing pages grep would miss — never skip this.

## Initializing a New Wiki

When the user asks to create or start a wiki:

**Preferred: Use `init-wiki.sh`** (one-shot bootstrap, copies all scripts + writes SCHEMA/index/log templates):

```bash
bash ${SKILL_DIR:-~/.hermes/skills/research/llm-wiki}/scripts/init-wiki.sh [wiki-path]
```

This is the only supported bootstrap path — it ensures `wiki_op.py` and all modules are present
at `${WIKI}/.hermes/scripts/`. The script handles idempotent re-runs (skip / update-scripts / full re-init).

**Manual fallback** (only if `init-wiki.sh` is unavailable):

1. Determine the wiki path (from config, env var, or ask the user; default `~/wiki`)
2. Create the directory structure above
3. Copy all `*.py` scripts from the skill's `scripts/` directory to `${WIKI}/.hermes/scripts/`
4. Ask the user what domain the wiki covers — be specific
5. Write `SCHEMA.md` customized to the domain (see template below)
6. Write initial `index.md` with sectioned header
7. Write initial `log.md` with creation entry
8. Confirm the wiki is ready and suggest first sources to ingest

### SCHEMA.md Template

> 📄 **See `references/wiki-templates.md`** for the full SCHEMA.md template including Domain, Conventions, Frontmatter, Tag Taxonomy, Page Thresholds, Entity/Concept/Comparison page structures, and Update Policy.
>
> Quick reference for initialization:
> ```bash
> # Run init-wiki.sh for one-shot bootstrap (writes SCHEMA + index + log + copies scripts)
> bash ${SKILL_DIR:-~/.hermes/skills/research/llm-wiki}/scripts/init-wiki.sh [wiki-path]
> ```
> For manual initialization, `read_file` the templates file and adapt.


## Four Core Protocols

The wiki has four upgrade protocols (implemented 2026-05). Full spec in the wiki's own `SCHEMA.md`.

### 1. Time Dimension (时间维度)

Every fact with a "current state" carries optional frontmatter fields:

```yaml
status: current | expired | superseded | uncertain
valid_from: 2026-05-25
valid_until: 2026-06-01  # known expiration date
```

**Script:** `wiki_op.py stale` — scans all pages for `status: current` + `valid_until < today` and alerts. Cron runs this nightly.

### 2. ADD-only Protocol (只增不改不删)

Facts are never overwritten or deleted. When updating:
1. Save a version snapshot: `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py snapshot concepts/page.md`
2. Append a timestamped entry to the page's `## 历史记录` section
3. Bump `updated` date in frontmatter
4. If contradictory info exists, mark `contradictions:` — let the reader judge

### 3. Entity Linking (实体链接)

**Index:** `~/wiki/_aliases/entities.json` — maps every entity slug to primary name + all aliases.

**Script:** `wiki_op.py entities` — pipe text through it to get `[[wikilink]]` suggestions:
```bash
echo "宇树科技和CXMT都要IPO了" | python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py entities -
# → "宇树科技" → [[unitree-robotics]]
# → "CXMT" → [[changxin-storage]]
```

### 4. Skill-Wiki Bridge (双向桥接)

**Mapping:** `~/wiki/skills/_mapping.md` — every Hermes skill ↔ wiki page pair.

**Script:** `wiki_op.py bridge` — analyze a SKILL.md for wiki references and extractable knowledge:
```bash
python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py bridge ~/.hermes/skills/investing/wyckoff-stock-analysis/SKILL.md
```

**Format:** Skill → Wiki uses `> 📚 Wiki: [[page-name]]` in SKILL.md. Wiki → Skill uses `skill: skill-name` in frontmatter.

### 5. Real-time Sync Convention (实时同步) ← PRIMARY MECHANISM

🚨 **This protocol has ONE rule:** After every `💾 Self-improvement review`, the agent MUST load llm-wiki (this skill) and execute the sync checklist. Do not rely on memory alone — load the skill, follow the steps, check every box.

**Why this rule exists:** The self-improvement review is Hermes' hardcoded agent loop — it's the only reliable hook. Without a skill loaded, the agent may skip wiki sync based on stale memory (as proven 2026-05-26 when 46 skill disables weren't synced).

**Trigger (mandatory):**
- After `Self-improvement review: Memory updated` → load llm-wiki → run checklist
- After `Self-improvement review: Skill patched` → load llm-wiki → run checklist
- When user says "update the wiki" → load llm-wiki → run checklist

**Full Sync Checklist:**

> ⚠️ **Pre-flight:** Before running any `wiki_op.py` commands below, verify the production wiki has the current scripts:
> ```bash
> # If wiki_op.py is old (missing subcommands like snapshot/stale/visits):
> cp ${SKILL_DIR:-~/.hermes/skills/research/llm-wiki}/scripts/*.py ${WIKI_PATH:-~/wiki}/.hermes/scripts/
> # Verify: wiki_op.py --help should show all 10 subcommands, not just create/update/delete/lint
> ```

| # | Step | Command / Action |
|---|------|-----------------|
| 1 | Snapshot | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py snapshot <page>` |
| 2 | Update pages | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py update --page <page> --change-summary "..." --patch-file /tmp/patch.json` |
| 3 | Update index | Manual (add to index.md if new page) |
| 4 | Update log | Manual (append to log.md) |
| 5 | Stale check | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py stale` |
| 6 | Entity links | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py entities "<text>"` |
| 7 | Skill bridge | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py bridge <SKILL.md>` |
| 8 | Mapping update | Manual (register in _mapping.md) |
| 9 | SKILL.md ref | Manual (add `> 📚 Wiki: [[page]]` to SKILL.md) |
| 10 | Visit heatmap | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py visits top 10` + `visits cold 30` |
| 11 | **Verify** ⚡ | `python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py lint` — catches broken links, missing index entries, tag violations. Exit 0 = clean sync. |

> ⚠️ Steps 3, 4, 8, 9 are manual — they depend on Agent discipline. Step 11 (`wiki_op.py lint`) is the mechanical backstop: if index.md wasn't updated (step 3) or a page was created without cross-references, lint will catch it.

**Change → Page map:**

| Change type | Pages to update |
|-------------|----------------|
| Skill created/disabled/deleted | `entities/hermes-agent-server.md` |
| Cron job changed | `entities/hermes-agent-server.md`, `concepts/market-monitoring-cron.md` |
| New tool/API configured | `entities/hermes-agent-server.md` or relevant entity page |
| New pitfall discovered | `concepts/cron-pitfalls.md` or create new concept page |
| Major workflow discovered | Create/update concept page |
| All of the above | `log.md` (append entry) |

**Anti-pattern — DO NOT:**
- Skip snapshot before editing
- Update pages without bumping `updated` date
- Create a page without adding to `index.md`
- Forget skill↔wiki bridge for new skills
- Rely on memory instead of loading this skill
- Modify skill scripts without deploying to production wiki before sync
- Bypass wiki_op.py with raw `patch()`/`write_file()` on wiki pages

### 6. Cron Safety Net (定时安全网)

The `每日Wiki知识同步` cron has been **downgraded from primary archiver to safety net**. It runs nightly at 03:00 Beijing time and only performs automated checks — no session scanning or page creation.

**Cron responsibilities (CHECK-ONLY):**
- `wiki_op.py stale` — scan for expired facts
- Orphan page detection — files not in index.md
- `wiki_op.py entities` — verify cross-references on recently changed pages
- `wiki_op.py bridge` — check skill↔wiki links

**Cron does NOT:** scan sessions, identify new knowledge, create pages, or update content. That's the real-time sync's job.

> ⚠️ **Cron prompt design**: All cron jobs now use a 🚨 anchor block in the middle of their prompt to force the final response to contain the actual report (not just "✅ Done"). See `[[cron-pitfalls]]`.
> 🔍 **Session scanning**: When `session_search(query=...)` returns 0 results for broad keyword queries, use browse-first-then-discover pattern. See `references/cron-session-scanning.md`.

---
> **See also:** `references/evolution-tools.md` — complete reference for the wiki_op.py tool suite and usage patterns.
> **Retrieval baseline:** `references/wiki-retrieval-baseline.md` — 2026-06-06 grep quality benchmark across 83-page wiki.
```

### index.md & log.md Templates

> 📄 **See `references/wiki-templates.md`** for the full index.md and log.md templates including scaling rules and log rotation policy. These are only needed during wiki initialization — `init-wiki.sh` creates them automatically.

## Core Operations

🚨 **WRITE GATE — wiki_op.py is the ONLY path to wiki files (🤖 机械强制)**

> All page creation, updates, and deletions MUST go through `wiki_op.py`.
> **NEVER use `write_file`, `patch`, or any other tool directly on wiki `.md` files.**
> `wiki_op.py` mechanically enforces: frontmatter completeness, index synchronization,
> log entries, version snapshots, tag whitelist, wikilink validation, and line-number
> corruption detection. Bypassing it = silent data corruption.
>
> Before any wiki write operation, verify the gate is available:
> ```bash
> python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py path
> ```
> If this fails → run `init-wiki.sh` first.

### 1. Ingest ⚡

When the user provides a source (URL, file, paste), integrate it into the wiki:

① **Capture the raw source:**
   - URL → use `web_extract` to get markdown, save to `raw/articles/`
   - PDF → use `web_extract` (handles PDFs), save to `raw/papers/`
   - Pasted text → save to appropriate `raw/` subdirectory
   - Name the file descriptively: `raw/articles/karpathy-llm-wiki-2026.md`

② **Discuss takeaways** with the user — what's interesting, what matters for
   the domain. (Skip this in automated/cron contexts — proceed directly.)

③ **Check what already exists** — search index.md and use `search_files` to find
   existing pages for mentioned entities/concepts. This is the difference between
   a growing wiki and a pile of duplicates.

④ **Write or update wiki pages via `wiki_op.py` (🤖 强制):**

   **Creating a new page:**
   ```bash
   # 1. Write body to temp file
   cat > /tmp/wiki-draft.md << 'EOF'
   # Page Title
   Content here...
   EOF
   # 2. Create via wiki_op.py
   python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py create \
     --page entities/my-page --type entity --title "Page Title" \
     --tags "tag1,tag2" --content-file /tmp/wiki-draft.md
   ```

   **Updating an existing page — surgical patch (preferred for small changes):**
   ```bash
   # Write patch as JSON
   echo '{"old":"old text to replace","new":"new replacement text"}' > /tmp/wiki-patch.json
   python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py update \
     --page entities/my-page --patch-file /tmp/wiki-patch.json \
     --change-summary "what changed and why"
   ```

   **Updating an existing page — full rewrite:**
   ```bash
   cat > /tmp/wiki-draft.md << 'EOF'
   (full new page content, including YAML frontmatter)
   EOF
   python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py update \
     --page entities/my-page --content-file /tmp/wiki-draft.md \
     --change-summary "what changed and why"
   ```

   - **New entities/concepts:** Create pages only if they meet the Page Thresholds
     in SCHEMA.md (2+ source mentions, or central to one source). Use `wiki_op.py create`.
   - **Existing pages:** Add new information, update facts, bump `updated` date.
     When new info contradicts existing content, follow the Update Policy.
     Use `wiki_op.py update --patch-file` for small changes, `--content-file` for rewrites.
   - **Cross-reference:** Every new or updated page must link to at least 2 other
     pages via `[[wikilinks]]`. Check that existing pages link back.
   - **Tags:** Only use tags from the taxonomy in SCHEMA.md. `wiki_op.py create` validates this.

⑤ **Update navigation:**
   - Add new pages to `index.md` under the correct section, alphabetically
   - Update the "Total pages" count and "Last updated" date in index header
   - Append to `log.md`: `## [YYYY-MM-DD] ingest | Source Title`
   - List every file created or updated in the log entry

⑥ **Report what changed** — list every file created or updated to the user.

A single source can trigger updates across 5-15 wiki pages. This is normal
and desired — it's the compounding effect.

### 2. Query ⚡

When the user asks a question about the wiki's domain:

🚨 **HARD GATE — BM25 before any page read for thematic queries:**

> Before you read a single wiki page to answer a thematic question, you MUST run:
> ```bash
> python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py search "<query>" --agent
> ```
> This is non-negotiable. `search_files` (grep) is REJECTED for wiki discovery.
> The ONLY exceptions are:
> - **Exact keyword lookup** — searching for a specific function name, API key,
>   error code, or ID string (not a concept/topic)
> - **Wiki under 50 pages** — `index.md` alone is sufficient for navigation
> - After BM25 has already been run in this session for the same topic

This gate exists because grep demonstrably fails at thematic queries:
- 2026-06-06 benchmark: "威科夫" query across 83 pages → first hit at rank #46 (2.2% precision)
- BM25: same query → #1 hit, Top-10 precision 60%
- See `references/wiki-retrieval-baseline.md` and `references/wiki-bm25-search.md`

① **Run BM25 search** (mandatory — the gate above):
   ```bash
   python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py search "<query>" --agent
   ```
   Returns a ranked top-5 list of `[[wikilinks]]` with relevance scores.

② **Read the top-ranked pages** using `read_file`. Start from #1 and read
   enough pages to answer the query (typically 2-5 pages). The BM25 scores
   tell you which pages are most relevant — trust the ranking.

③ **For wikis under 50 pages**, `index.md` alone is sufficient.
   For exact keyword lookups (function names, IDs, error codes), `search_files`
   (grep) is acceptable — this is the only grep use case for wiki queries.

④ **Synthesize an answer** from the compiled knowledge. Cite the wiki pages
   you drew from: "Based on [[page-a]] and [[page-b]]..."

⑤ **Record visits** for every page you read during the query:
   ```bash
   python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py visits record <page-slug>
   ```

⑥ **File valuable answers back** — if the answer is a substantial comparison,
   deep dive, or novel synthesis, create a page in `queries/` or `comparisons/`.
   Don't file trivial lookups — only answers that would be painful to re-derive.

⑦ **Update log.md** with the query and whether it was filed.

### 3. Lint ⚡

When the user asks to lint, health-check, or audit the wiki:

**Start with the four-point quick check** (`references/wiki-self-check.md`) — catches broken index links, dangling refs, expired facts, and broken wikilinks. This is a fast first pass. Then proceed with the full 12-step audit below for outbound links, orphans (no inbound), tags, frontmatter, page size, etc.

① **Orphan pages:** Find pages with no inbound `[[wikilinks]]` from other pages.
```python
# Use execute_code for this — programmatic scan across all wiki pages
import os, re
from collections import defaultdict
wiki = "<WIKI_PATH>"
# Scan all .md files in entities/, concepts/, comparisons/, queries/
# Extract all [[wikilinks]] — build inbound link map
# Pages with zero inbound links are orphans
```

② **Broken wikilinks:** Find `[[links]]` that point to pages that don't exist.

③ **Index completeness:** Every wiki page should appear in `index.md`. Compare
   the filesystem against index entries.

④ **Frontmatter validation:** Every wiki page must have all required fields
   (title, created, updated, type, tags, sources). Tags must be in the taxonomy.

⑤ **Stale content:** Pages whose `updated` date is >90 days older than the most
   recent source that mentions the same entities.

⑥ **Contradictions:** Pages on the same topic with conflicting claims. Look for
   pages that share tags/entities but state different facts.

⑦ **Page size:** Flag pages over 200 lines — candidates for splitting.

⑧ **Tag audit:** List all tags in use, flag any not in the SCHEMA.md taxonomy.

⑨ **Log rotation:** If log.md exceeds 500 entries, rotate it.

⑩ **Report findings** with specific file paths and suggested actions, grouped by
   severity (broken links > expired facts > orphans > stale content > style issues).

⑪ **Run evolution tools:** After lint, run `wiki_op.py stale` to catch expired facts,
   and `wiki_op.py entities` on any changed pages to verify cross-references are complete.

⑫ **Append to log.md:** `## [YYYY-MM-DD] lint | N issues found`

## Working with the Wiki

### Searching

```bash
# BM25 relevance-ranked search (PRIMARY — use this for all thematic queries)
python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py search "威科夫 吸筹" --agent
# Returns compact top-5 [[wikilinks]] with scores
# Rebuild index if stale (auto-detected):
python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py search --rebuild-only

# Find pages by content — grep for exact keywords (fast, no index needed)
search_files "transformer" path="$WIKI" file_glob="*.md"

# Find pages by filename
search_files "*.md" target="files" path="$WIKI"

# Find pages by tag
search_files "tags:.*alignment" path="$WIKI" file_glob="*.md"

# Recent activity
read_file "$WIKI/log.md" offset=<last 20 lines>
```

### Bulk Ingest

When ingesting multiple sources at once, batch the updates:
1. Read all sources first
2. Identify all entities and concepts across all sources
3. Check existing pages for all of them (one search pass, not N)
4. Create/update pages in one pass — **all via `wiki_op.py`** (avoids redundant updates and ensures frontmatter/index/log consistency)
5. Update index.md once at the end
6. Write a single log entry covering the batch

### Archiving

When content is fully superseded or the domain scope changes, **use `wiki_op.py delete`** (🤖 强制):
```bash
# Archive with confirmation (shows inbound links, requires --force to proceed)
python3 ${WIKI_PATH:-~/wiki}/.hermes/scripts/wiki_op.py delete --page entities/old-page --force
```
This mechanically: moves to `_archive/`, removes from `index.md`, logs the action, and warns about inbound links that need updating. Do NOT manually `mv` or `rm` wiki pages.

### Obsidian Integration & Headless Sync

> 📄 **See `references/wiki-templates.md`** for Obsidian desktop integration (vault setup, Dataview, plugins) and Obsidian Headless setup (CLI sync, systemd service). These are one-time setup operations — not needed for daily wiki use.

## Pitfalls

> Format: ❌ wrong behavior — why it breaks — ✅ correct approach. Each entry is a real bug that happened.

### Wiki Maintenance

1. ❌ **Direct `write_file`/`patch` on wiki `.md` files** → bypasses frontmatter validation, index sync, log, snapshots, tag whitelist, line-number corruption detection. → ✅ All writes go through `wiki_op.py create` / `wiki_op.py update --patch-file`.

2. ❌ **Skipping orientation** (not reading SCHEMA + index + log before operating) → duplicates, missed cross-references, contradicted conventions. → ✅ Always run the orientation three reads in a new session.

3. ❌ **Creating pages for passing mentions** (a name appears once in a footnote) → wiki bloat, noise in index, broken wikilinks. → ✅ Follow Page Thresholds from SCHEMA.md. Add to existing page when possible.

4. ❌ **No cross-references** (new page links to nothing) → invisible page, nobody discovers it. → ✅ Minimum 2 outbound wikilinks per page. Check existing pages link back.

5. ❌ **Tags outside taxonomy** → freeform tags decay into noise, lint fails. → ✅ Only use tags from SCHEMA.md tag taxonomy. Add new tags to SCHEMA.md first.

6. ❌ **Pages over 200 lines** → unreadable, hard to navigate. → ✅ Split into sub-topics, link between them.

7. ❌ **Skipping index.md / log.md updates** → navigational backbone degrades, pages become invisible. → ✅ After every write: add to index, append to log.

8. ❌ **Bypassing wiki_op.py with raw `patch()` on wiki pages** (e.g., manual cp snapshots, then patch pages, then old stale_check.py — all done 2026-06-10) → violates [[wiki-op-gate]] three-layer defense architecture. → ✅ After modifying skill scripts, cp them to production wiki, then use wiki_op.py for all sync operations.

### Search & Navigation

9. ❌ **grep/search_files for thematic wiki queries** (e.g., "威科夫") across 83+ pages → first real hit at rank #46, precision 2.2%. → ✅ BM25 `wiki_op.py search "query" --agent` for all thematic queries. grep only for exact keywords (function names, error codes, IDs).

10. ❌ **`session_search` with `around_message_id=1`** → message IDs are global, not per-session. ID 1 is the first message ever, not the first of this session. → ✅ Use discovery mode (`query=...`) first to find `match_message_id`, then scroll.

11. ❌ **`patch` on `index.md` with only 2-3 context lines** → wikilinks look alike, patch matches wrong location, silently drops entries. → ✅ At least 5 lines of surrounding context. Afterward: always `read_file` the section to verify.

### Deployment

12. ❌ **Only copying `wiki_op.py` to production** (not the 6 module files) → `wiki_op.py stale/entities/search` etc. fail with ImportError. → ✅ Copy all `scripts/*.py` with `init-wiki.sh` or `cp scripts/*.py ~/wiki/.hermes/scripts/`.

13. ❌ **Deploying script changes but not updating production** → sync checklist commands fail with "invalid choice" because old wiki_op.py is still in place. → ✅ After modifying skill `scripts/`, immediately `cp` to production wiki before running sync.
