#!/bin/bash
# init-wiki.sh — Bootstrap a new llm-wiki instance
# Usage: bash init-wiki.sh [wiki-path]
#   wiki-path defaults to $WIKI_PATH or ~/wiki

set -euo pipefail

WIKI="${1:-${WIKI_PATH:-$HOME/wiki}}"
WIKI=$(eval echo "$WIKI")

echo "🌐 Initializing llm-wiki at: $WIKI"

# Guard: existing wiki
choice="full"
if [ -f "$WIKI/SCHEMA.md" ]; then
    if [ -t 0 ]; then
        echo "⚠️  Wiki already exists at $WIKI"
        echo "  [1] Skip (exit)"
        echo "  [2] Update scripts only (cp all *.py)"
        echo "  [3] Full re-init (overwrites SCHEMA/index/log)"
        read -p "Choice [1]: " choice_raw
        choice="${choice_raw:-1}"
    else
        choice="1"
    fi
    case "$choice" in
        2) ;;
        3) ;;
        *) echo "→ Skipping."; exit 0 ;;
    esac
fi

# Create directory structure (idempotent)
mkdir -p "$WIKI"/{raw/{articles,papers,transcripts,assets},entities,concepts,comparisons,queries}
mkdir -p "$WIKI"/{.hermes/scripts,_versions,_aliases,skills}

# Copy ALL scripts from skill's scripts/ directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR"/*.py "$WIKI/.hermes/scripts/"
echo "  ✅ Copied scripts: $(ls "$SCRIPT_DIR"/*.py 2>/dev/null | wc -l) files"

# Full init: write SCHEMA + index + log (only if choice is full or 3)
if [ "$choice" = "full" ] || [ "$choice" = "3" ]; then
    TODAY=$(date +%Y-%m-%d)

    # SCHEMA.md
    cat > "$WIKI/SCHEMA.md" << 'SCHEMA_EOF'
# Wiki Schema

## Domain
三层知识库 — 「你 (Agent)」「我 (User)」「世界 (World)」：

- **你 (Agent)**：本机 Hermes Agent 的环境配置、工具链、技能使用经验、踩过的坑
- **我 (User)**：用户的身份、偏好、兴趣、行事风格、已掌握的知识、个人项目
- **世界 (World)**：通过 Agent 研究获得的一切知识——技术调研、投资分析、学术文献、工程笔记、市场情报

原则：任何在对话中产生的、值得留存的知识都可以入 Wiki。不复述"Agent 做了什么"，而是提炼"我们知道了什么"。

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `wyckoff-analysis.md`)
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- 语言：中文为主，技术术语保留英文

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

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

## Time Dimension
Every fact with a "current state" carries optional frontmatter fields:
```yaml
status: current | expired | superseded | uncertain
valid_from: YYYY-MM-DD
valid_until: YYYY-MM-DD  # known expiration date
```
Run `wiki_op.py stale` to scan for expired facts.

## ADD-only Protocol
Facts are never overwritten or deleted. When updating:
1. Save a version snapshot: `wiki_op.py snapshot concepts/page`
2. Append a timestamped entry to the page's `## 历史记录` section
3. Bump `updated` date in frontmatter
4. If contradictory info exists, mark `contradictions:` — let the reader judge

## Entity Linking
Index: `_aliases/entities.json` — maps every entity slug to primary name + all aliases.
Run `wiki_op.py entities "text"` to get wikilink suggestions.

## Skill-Wiki Bridge
Mapping: `skills/_mapping.md` — every Hermes skill ↔ wiki page pair.
Run `wiki_op.py bridge path/to/SKILL.md` for bridge analysis.
Format: Skill → Wiki uses `> 📚 Wiki: [[page-name]]` in SKILL.md. Wiki → Skill uses `skill: skill-name` in frontmatter.
SCHEMA_EOF

    # index.md
    cat > "$WIKI/index.md" << 'INDEX_EOF'
# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: INDEX_DATE | Total pages: 0

## Entities
<!-- Alphabetical within section -->

## Concepts

## Comparisons

## Queries
INDEX_EOF
    sed -i "s/INDEX_DATE/$TODAY/" "$WIKI/index.md"

    # log.md
    cat > "$WIKI/log.md" << LOG_EOF
# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [LOG_DATE] create | Wiki initialized
- Domain: 三层知识库 (Agent/User/World)
- Structure created with SCHEMA.md, index.md, log.md
- Unified CLI: wiki_op.py
LOG_EOF
    sed -i "s/LOG_DATE/$TODAY/" "$WIKI/log.md"

    echo "  ✅ Created SCHEMA.md, index.md, log.md"
fi

# Check rank-bm25
if ! python3 -c "import rank_bm25" 2>/dev/null; then
    echo "⚠️  pip install rank-bm25 (required for wiki_op.py search)"
fi

echo ""
echo "✅ Wiki ready. Try: python3 $WIKI/.hermes/scripts/wiki_op.py path"
