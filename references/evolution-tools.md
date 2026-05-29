# Wiki Evolution Tools — Complete Reference

Five utility scripts in `~/wiki/.hermes/scripts/` that power the time-dimension,
ADD-only, entity-linking, skill-wiki-bridge, and visit-tracking protocols.

> **All paths relative to `~/wiki/.hermes/scripts/`**. Symlink to `~/.hermes/scripts/` for convenience.

---

## 1. stale_check.py — Expired Fact Detection

**Purpose:** Scan all wiki pages for `status: current` + `valid_until < today`.

**Usage:**
```bash
python3 ~/wiki/.hermes/scripts/stale_check.py
```

**Exit codes:** 0 = no expired facts, 1 = expired facts found (lists them).

**Frontmatter fields checked:**
```yaml
status: current
valid_until: 2026-06-01  # If this date < today → alert
```

**Cron integration:** Runs nightly at 23:00 as part of `每日Wiki知识同步`. Expired
facts appear at the bottom of the sync report.

---

## 2. version_history.py — ADD-only Snapshot

**Purpose:** Before updating a wiki page, save the current version to `_versions/{page}/{timestamp}.md`.

**Usage:**
```bash
python3 ~/wiki/.hermes/scripts/version_history.py concepts/wyckoff-analysis.md
```

**Output:**
```
✅ Snapshot: wyckoff-analysis → _versions/wyckoff-analysis/2026-05-25_224535.md
```

**When to use:** Every time you modify an existing wiki page (ADD-only protocol step 4).
Run BEFORE making changes.

---

## 3. entity_link.py — Automatic Wikilink Suggestions

**Purpose:** Pipe text through it to find entity mentions that should be `[[wikilinked]]`.

**Usage:**
```bash
echo "宇树科技和CXMT都要IPO了" | python3 ~/wiki/.hermes/scripts/entity_link.py
```

**Output:**
```
🔗 2 entity link suggestions:
  "宇树科技" → [[unitree-robotics]] (宇树科技)
  "CXMT" → [[changxin-storage]] (长鑫存储)
```

**Data source:** `~/wiki/_aliases/entities.json` — 18 entities with primary names + aliases.

**Algorithm:** Case-insensitive regex match for every alias, skip already-wikilinked
occurrences, keep longest match at each position, return sorted by position.

**Cron integration:** After syncing new content, pipe the new page through this script
and auto-add any suggested wikilinks.

---

## 4. skill_wiki_bridge.py — Skill-Wiki Cross-Reference

**Purpose:** Analyze a Hermes SKILL.md for wiki references and extractable knowledge nuggets.

**Usage:**
```bash
python3 ~/wiki/.hermes/scripts/skill_wiki_bridge.py ~/.hermes/skills/investing/wyckoff-stock-analysis/SKILL.md
```

**What it finds:**
- `[[wikilinks]]` already in the SKILL.md (count + list)
- Knowledge nuggets in `## Pitfalls` and `## 核心/关键` sections
- Whether the skill is registered in `skills/_mapping.md`

**Format for bidirectional references:**
- **Skill → Wiki:** Add `> 📚 Wiki: [[page-name]]` to SKILL.md
- **Wiki → Skill:** Add `skill: skill-name` to page frontmatter

---

## Script Invocation Pattern (for cron / automated contexts)

```bash
# 1. Check for expired facts
python3 ~/wiki/.hermes/scripts/stale_check.py || echo "⚠️ Expired facts need attention"

# 2. Save version snapshot before updating
python3 ~/wiki/.hermes/scripts/version_history.py concepts/target-page.md

# 3. After new content, check for missing entity links
cat concepts/new-page.md | python3 ~/wiki/.hermes/scripts/entity_link.py

# 4. Cross-reference with skill system
python3 ~/wiki/.hermes/scripts/skill_wiki_bridge.py ~/.hermes/skills/path/to/SKILL.md

# 5. Check page visit heatmap
python3 ~/wiki/.hermes/scripts/visit_tracker.py top 10
python3 ~/wiki/.hermes/scripts/visit_tracker.py cold 30
```

---

## 5. visit_tracker.py — Side-Channel Visit Counter

**Purpose:** Record and query wiki page visit counts via lightweight SQLite side-channel.
Keeps visit data out of markdown frontmatter to avoid write amplification on every read.

**DB:** `~/wiki/.hermes/visits.db` (single table, WAL mode, auto-created on first write)

**Usage:**

```bash
# Record a visit (silent — zero output on success)
python3 ~/wiki/.hermes/scripts/visit_tracker.py record wyckoff-analysis

# Show one page's stats
python3 ~/wiki/.hermes/scripts/visit_tracker.py query hermes-agent-server

# Top-10 most visited
python3 ~/wiki/.hermes/scripts/visit_tracker.py top 10

# Pages untouched for 30+ days
python3 ~/wiki/.hermes/scripts/visit_tracker.py cold 30

# Global summary (total visits, unique pages, date range)
python3 ~/wiki/.hermes/scripts/visit_tracker.py stats
```

**Integration:** Call `record` for every page read during Query operations.
Run `top 10` + `cold 30` as part of the sync checklist (step 10) to surface
page utilization — which knowledge is actively consulted vs. gathering dust.

**Design rationale:** Placing counts in frontmatter would trigger the full write
chain (markdown write → checkpoint snapshot → Git commit) on every read. A
side-channel SQLite with WAL mode avoids this entirely while still providing
the same intelligence.
