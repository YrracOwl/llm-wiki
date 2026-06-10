---
name: llm-wiki
description: "Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Use when user asks to ingest sources, update the wiki, query compiled knowledge, lint for consistency, create a knowledge base, or add notes. All writes go through wiki_op.py unified CLI."
version: 2.3.1
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

> ⚠️ **Line count**: This skill exceeds the 300-line target (~720 lines). This is intentional as a **domain knowledge skill** — the Ingest/Query/Lint operation flows, command templates, sync checklist, and schema templates are all **operational dependencies** the Agent needs at decision time, not "reference material" to be looked up separately. Removing them would add 3-5 `read_file` calls per operation, making every wiki interaction slower and more error-prone. The BM25 gate and write gate markers (🚨) ensure critical rules aren't buried.

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

Adapt to the user's domain. The schema constrains agent behavior and ensures consistency:

```markdown
# Wiki Schema

## Domain
三层知识库 — 「你 (Agent)」「我 (User)」「世界 (World)」：

- **你 (Agent)**：本机 Hermes Agent 的环境配置、工具链、技能使用经验、踩过的坑
- **我 (User)**：用户的身份、偏好、兴趣、行事风格、已掌握的知识、个人项目
- **世界 (World)**：通过 Agent 研究获得的一切知识——技术调研、投资分析、学术文献、工程笔记、市场情报

原则：任何在对话中产生的、值得留存的知识都可以入 Wiki。不复述"Agent 做了什么"，而是提炼"我们知道了什么"。

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `wyckoff-analysis.md`) or for 世界层 technical topics: `adclk954-broadband-jitter.md`
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- 语言：中文为主，技术术语保留英文
- 页面归属标注：在正文开头用一句「归属：你/我/世界」标注该页面主要属于哪一层（跨层页面可并列）

## Frontmatter
  ```yaml
  ---
  title: Page Title
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | query | summary
  tags: [from taxonomy below]
  sources: [raw/articles/source-name.md]
  ---
  ```

## Tag Taxonomy
- **环境与配置**: server, config, network, proxy, mirror
- **工具与技能**: skill, tool, cli, automation
- **数据与API**: data-source, api, stock, news
- **方法论**: theory, workflow, strategy, analysis
- **经验与坑**: pitfall, workaround, lesson, memory
- **平台**: qqbot, telegram, discord, xiaohongshu, steam, weibo, github
- **投资**: wyckoff, sentiment, a-stock, technical-analysis
- **内容**: mao, poetry, literature, classic
- **工程**: electronics, datasheet, semiconductor, signal-processing, measurement

## Page Thresholds
- **你 (Agent) 层**：当工具/技能/配置在 2+ 会话中出现或是一个主要工作流的核心 → 建页面
- **我 (User) 层**：当用户的偏好/身份/项目被明确讨论并形成可复用知识 → 建页面
- **世界 (World) 层**：当 Agent 完成一次有深度的技术调研、投资分析或学术查询，且结果值得复用 → 建页面
- **Add to existing page** when new info relates to an already-covered topic
- **DON'T create a page** for passing mentions, trivia, or things outside the domain
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages
One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

## Concept Pages
One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

## Comparison Pages
Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report


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

### index.md Template

The index is sectioned by type. Each entry is one line: wikilink + summary.

```markdown
# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: YYYY-MM-DD | Total pages: N

## Entities
<!-- Alphabetical within section -->

## Concepts

## Comparisons

## Queries
```

**Scaling rule:** When any section exceeds 50 entries, split it into sub-sections
by first letter or sub-domain. When the index exceeds 200 entries total, create
a `_meta/topic-map.md` that groups pages by theme for faster navigation.

### log.md Template

```markdown
# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [YYYY-MM-DD] create | Wiki initialized
- Domain: [domain]
- Structure created with SCHEMA.md, index.md, log.md
```

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
4. Create/update pages in one pass (avoids redundant updates)
5. Update index.md once at the end
6. Write a single log entry covering the batch

### Archiving

When content is fully superseded or the domain scope changes:
1. Create `_archive/` directory if it doesn't exist
2. Move the page to `_archive/` with its original path (e.g., `_archive/entities/old-page.md`)
3. Remove from `index.md`
4. Update any pages that linked to it — replace wikilink with plain text + "(archived)"
5. Log the archive action

### Obsidian Integration

The wiki directory works as an Obsidian vault out of the box:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries
- The `raw/assets/` folder holds images referenced via `![[image.png]]`

For best results:
- Set Obsidian's attachment folder to `raw/assets/`
- Enable "Wikilinks" in Obsidian settings (usually on by default)
- Install Dataview plugin for queries like `TABLE tags FROM "entities" WHERE contains(tags, "company")`

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the
same directory as the wiki path.

### Obsidian Headless (servers and headless machines)

On machines without a display, use `obsidian-headless` instead of the desktop app.
It syncs vaults via Obsidian Sync without a GUI — perfect for agents running on
servers that write to the wiki while Obsidian desktop reads it on another device.

**Setup:**
```bash
# Requires Node.js 22+
npm install -g obsidian-headless

# Login (requires Obsidian account with Sync subscription)
ob login --email <email> --password '<password>'

# Create a remote vault for the wiki
ob sync-create-remote --name "LLM Wiki"

# Connect the wiki directory to the vault
cd ~/wiki
ob sync-setup --vault "<vault-id>"

# Initial sync
ob sync

# Continuous sync (foreground — use systemd for background)
ob sync --continuous
```

**Continuous background sync via systemd:**
```ini
# ~/.config/systemd/user/obsidian-wiki-sync.service
[Unit]
Description=Obsidian LLM Wiki Sync
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/path/to/ob sync --continuous
WorkingDirectory=/home/user/wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now obsidian-wiki-sync
# Enable linger so sync survives logout:
sudo loginctl enable-linger $USER
```

This lets the agent write to `~/wiki` on a server while you browse the same
vault in Obsidian on your laptop/phone — changes appear within seconds.

## Pitfalls

- **Never modify files in `raw/`** — sources are immutable. Corrections go in wiki pages.
- **Always orient first** — read SCHEMA + index + recent log before any operation in a new session.
  Skipping this causes duplicates and missed cross-references.
- **Always update index.md and log.md** — skipping this makes the wiki degrade. These are the
  navigational backbone.
- **Don't create pages for passing mentions** — follow the Page Thresholds in SCHEMA.md. A name
  appearing once in a footnote doesn't warrant an entity page.
- **Don't create pages without cross-references** — isolated pages are invisible. Every page must
  link to at least 2 other pages.
- **Frontmatter is required** — it enables search, filtering, and staleness detection.
- **Tags must come from the taxonomy** — freeform tags decay into noise. Add new tags to SCHEMA.md
  first, then use them.
- **Keep pages scannable** — a wiki page should be readable in 30 seconds. Split pages over
  200 lines. Move detailed analysis to dedicated deep-dive pages.
- **Index completeness check after every sync** — files created in entities/ or concepts/ that aren't in index.md become invisible orphans. After any write to the wiki, compare `search_files "*.md" target="files" path="~/wiki/entities"` against the index's Entities section, and same for concepts/. Found `tailscale-failed.md` orphaned in May 2026 — created during bulk init but never indexed.
- **Rotate the log** — when log.md exceeds 500 entries, rename it `log-YYYY.md` and start fresh.
  The agent should check log size during lint.
- **Script fragmentation — individual tools pre-date wiki_op.py.** Utility scripts were created before `wiki_op.py` became the unified CLI. All individual scripts have been consolidated into `wiki_op.py` subcommands (see Sync Checklist above). When adding new wiki tooling, add it as a `wiki_op.py` subcommand. ⚠️ **The `wiki_op.py` write gate exists for a reason**: it mechanically enforces ADD-only, tag whitelist, frontmatter completeness, and line-number corruption detection. Direct `write_file`/`patch` on wiki pages bypasses these guards. Prefer `wiki_op.py update/create` for all wiki writes unless there's a specific reason not to.
  mark in frontmatter, flag for user review.
- **Domain-level and model-generated skills** — see `references/agent-memory-landscape.md` for a 2026-06 survey of agent memory architectures (agentmemory, Graphiti, Mem0, Letta, SkillOpt, Cognitive Workspace, etc.) and their implications for wiki evolution. Updated 2026-06-06 with agentmemory comparison.
- **Don't gatekeep by narrow domain assumptions** — the wiki's scope is defined by SCHEMA.md's domain field, not by the agent's guess. Many wikis use a three-layer model (Agent/User/World). If SCHEMA.md says the domain covers \"everything learned through the agent,\" then technical research, datasheet analysis, investment notes, photography knowledge, and any other knowledge the user generates through conversation ALL belong. Never refuse to add content because \"it's not about Agent configuration\" — that's reading the domain too narrowly. The domain is what the schema says it is.
- **Grep retrieval fails much earlier than index.md limit — 83 pages is already broken for thematic queries.** On 2026-06-06, a grep for \"威科夫\" across an 83-page wiki returned 50 matches, but the first actual wyckoff analysis page was at rank **#46** (precision 2.2%). The top 45 results were noise: excalidraw, diandian-ai, hermes-skills — pages that mention \"威科夫\" once in passing. Grep ranks by match count/file-path, not relevance. Mitigations: (a) prefer specific terms over broad keywords, (b) use `index.md` for discovery before grep, (c) for wikis above ~50 pages, implement multi-signal retrieval (BM25 + embedding + RRF fusion) — see `references/wiki-retrieval-baseline.md`.
- **`session_search` scroll requires real message IDs — `around_message_id=1` is a trap.** Message IDs are auto-incremented globally, not reset per session. The first message in a session might be ID 26309, not 1. Always use discovery mode (`session_search(query=...)`) first to find the actual `match_message_id`, then use that for scrolling. If discovery with a query returns nothing, fall back to `session_search()` browse mode and scroll via the last message ID from `bookend_end`. See also: `references/cron-sync-pitfalls.md` and `references/cron-session-scanning.md`.
- **🚨 `patch` on `index.md` needs 5+ context lines — wikilinks look alike.** Index entries are identical in structure (`- [[page-name]] — description`). Using only 2-3 lines of context causes `patch` to match the wrong location, silently dropping entries (e.g. `gmid-flow` disappeared during a blogwatcher update on 2026-06-10). Always include at least 5 lines of surrounding context to disambiguate. After patching index.md, ALWAYS verify by reading the section — duplicate entries and accidental removals are silent bugs that require manual repair.

- **🚨 wiki_op.py 是 7 个 Python 文件，不是一个文件。** `wiki_op.py` 是 dispatch 层，依赖 `wiki_path.py` + 5 个模块文件（`wiki_op_stale/entities/bridge/visits/search.py`）。部署到 `~/wiki/.hermes/scripts/` 时必须复制全部 `scripts/*.py`——用 `init-wiki.sh` 或 `cp scripts/*.py ~/wiki/.hermes/scripts/`。从 CLI 角度看是"一个命令"，从文件系统角度看是"7 个文件"。

- **🚨 修改 skill 后必须部署脚本到生产 wiki。** 同步清单（sync checklist）里的 `wiki_op.py snapshot/stale/visits` 等子命令只在新版 `wiki_op.py` 中可用。如果生产 `~/wiki/.hermes/scripts/wiki_op.py` 还是旧版（只有 create/update/delete/lint），这些命令会报 `invalid choice` 错误。修改 skill 的 `scripts/` 后，立即 `cp` 到生产 wiki 再执行同步。**不要绕过 wiki_op.py 裸写文件**——`patch()` 直接改 wiki 页面违背 [[wiki-op-gate]] 三道防线架构（2026-06-10 实际发生过：先手动 cp 快照、patch 页面、旧脚本查 stale，再被用户指出后补部署）。

- **`init-wiki.sh` 不创建 `_aliases/entities.json` 模板。** 新 wiki 上运行 `wiki_op.py entities "text"` 会输出 `⚠️ entities.json not found`。这是预期的——实体链接需要手动填充 `_aliases/entities.json` 才有用。如果需要空模板，手动创建 `{"entities": {}}`。
