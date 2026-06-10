# llm-wiki — Karpathy's LLM Wiki for Hermes

A persistent, compounding knowledge base as interlinked markdown files.
Based on Andrej Karpathy's LLM Wiki pattern.

## Quick Start

1. Copy to your Hermes skills:
   ```
   cp -r llm-wiki ~/.hermes/skills/research/
   ```

2. Initialize a wiki:
   ```
   bash ~/.hermes/skills/research/llm-wiki/scripts/init-wiki.sh
   ```

3. Ask your Hermes Agent:
   > "update the wiki" — it will load this skill and guide you.

## Requirements

- Python 3.8+
- `pip install rank-bm25` (for BM25 search, optional for wikis under 50 pages)

## All operations via unified CLI

```bash
python3 ~/wiki/.hermes/scripts/wiki_op.py create ...
python3 ~/wiki/.hermes/scripts/wiki_op.py update ...
python3 ~/wiki/.hermes/scripts/wiki_op.py lint
python3 ~/wiki/.hermes/scripts/wiki_op.py stale
python3 ~/wiki/.hermes/scripts/wiki_op.py search "query" --agent
python3 ~/wiki/.hermes/scripts/wiki_op.py visits top 10
python3 ~/wiki/.hermes/scripts/wiki_op.py entities "text"
python3 ~/wiki/.hermes/scripts/wiki_op.py bridge path/to/SKILL.md
python3 ~/wiki/.hermes/scripts/wiki_op.py snapshot concepts/page
python3 ~/wiki/.hermes/scripts/wiki_op.py path
```

## Architecture

```
wiki_op.py (dispatch)
├── create / update / delete / lint  (built-in)
├── snapshot / path                  (built-in)
├── stale       → wiki_op_stale.py
├── entities    → wiki_op_entities.py
├── bridge      → wiki_op_bridge.py
├── visits      → wiki_op_visits.py
└── search      → wiki_op_search.py
```

## Files

```
llm-wiki/
├── SKILL.md                    # Agent instruction file
├── README.md                   # This file
├── scripts/
│   ├── wiki_op.py              # Unified CLI
│   ├── wiki_path.py            # Path resolution
│   ├── wiki_op_stale.py        # Expired fact scanner
│   ├── wiki_op_entities.py     # Entity link suggester
│   ├── wiki_op_bridge.py       # Skill-wiki bridge
│   ├── wiki_op_visits.py       # Visit tracker
│   ├── wiki_op_search.py       # BM25 search
│   └── init-wiki.sh            # One-shot bootstrap
└── references/                 # Documentation
```

## License

MIT — same as Hermes Agent.
