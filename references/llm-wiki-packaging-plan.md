# llm-wiki Skill Packaging Plan

> Architecture analysis and consolidation roadmap. Created 2026-06-10 during a grill session.

## Motivation

The llm-wiki skill evolved organically: `wiki_op.py` was created as a write gate (2026-05-31), then individual utility scripts were added ad-hoc. The result is fragmentation — 7 scripts with different path resolution methods, some functionality duplicated (version_history inside wiki_op.py update, broken_links inside wiki_op.py lint), and SKILL.md commands scattered across multiple CLI names.

## Architecture Discovery

Grill revealed that `wiki_op.py` was designed as the unified CLI entry point (three-layer architecture: SKILL.md → wiki_op.py → SCHEMA.md) but the integration was never completed. The correct end state:

```
SKILL.md → wiki_op.py <subcommand>  (one CLI for all operations)

wiki_op.py create/update/delete/lint   ← existing
wiki_op.py stale                       ← absorb stale_check.py
wiki_op.py snapshot                    ← expose internal snapshot function
wiki_op.py entities "text"             ← absorb entity_link.py
wiki_op.py bridge <skill.md>           ← absorb skill_wiki_bridge.py
wiki_op.py visits top 10               ← absorb visit_tracker.py
wiki_op.py search "query" --agent      ← absorb wiki_search.py (lazy import)
wiki_op.py path                        ← debug helper
```

## Script Absorption Map

| Old | New | Status |
|-----|-----|--------|
| `wiki_op.py create/update/delete/lint` | `wiki_op.py create/update/delete/lint` | Unchanged |
| `stale_check.py` | `wiki_op.py stale` | Absorbed as module |
| `version_history.py` | `wiki_op.py snapshot` | Already internal, expose as subcommand |
| `entity_link.py` | `wiki_op.py entities` | Absorbed as module |
| `skill_wiki_bridge.py` | `wiki_op.py bridge` | Absorbed as module |
| `visit_tracker.py` | `wiki_op.py visits` | Absorbed as module |
| `wiki_search.py` | `wiki_op.py search` | Absorbed as module (lazy import rank-bm25) |
| `broken_links.py` | Already in `wiki_op.py lint` | Retire |

## Path Resolution Unification

8 scripts used 5 different path resolution methods. The fix: single `wiki_path.py` module with resolution order `--wiki-path` flag > `WIKI_PATH` env var > `~/wiki` default.

## Key Design Decisions

1. **Modular, not monolithic**: Each absorbed script becomes a `wiki_op_*.py` module file, not inline code in wiki_op.py
2. **Lazy import for rank-bm25**: Only `wiki_op.py search` triggers the import — other commands work without the pip package
3. **init-wiki.sh copies the entire `scripts/` directory**: No need to maintain a list of files
4. **Old scripts get DEPRECATED headers, not deleted**: Transition period safety

## Implementation: 5 Phases

| Phase | Content | Est. Time |
|-------|---------|:---:|
| 1 | Infrastructure: wiki_path.py + module skeletons + wiki_op.py dispatch | 30 min |
| 2 | Absorb 5 scripts into wiki_op_*.py modules | 30 min |
| 3 | SKILL.md rewrite: all commands → wiki_op.py subcommands | 20 min |
| 4 | init-wiki.sh: simplify to `cp scripts/*.py` | 15 min |
| 5 | Reference doc updates + e2e test + packaging | 25 min |

Full implementation plan at `~/wiki/.hermes/plans/llm-wiki-packaging.md`.
