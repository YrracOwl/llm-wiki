# wiki_op.py Architecture Decisions

## Why wiki_op.py exists

Before v3.0, all wiki maintenance relied on the agent remembering procedural rules from a 637-line SKILL.md. This caused:
- Broken wikilinks (10)
- Missing frontmatter (6 pages)
- Line-number prefix corruption (3 files)
- Index inconsistencies (2)

Root cause: procedural knowledge in prose prompts decays with LLM attention span.

## Three-layer architecture

| Layer | File | Role |
|-------|------|------|
| Operations | `SKILL.md` (160 lines) | What to call, why, what not to do |
| Enforcement | `wiki_op.py` (946 lines) | Mechanical gate — all writes go through it |
| Constitution | `SCHEMA.md` (168 lines) | Tag taxonomy, domain model, ADD-only protocol |

## Key design decisions

### 1. Script is the gate, not a helper
All wiki writes MUST go through `wiki_op.py`. Direct `write_file`/`patch` on `~/wiki/` is forbidden. This is enforced by convention (SKILL.md iron rule) not by filesystem permissions — but the lint command detects violations.

### 2. UPDATE has two modes
- `--patch-file` (surgical): JSON `{"old":"...","new":"..."}`, old must be unique
- `--content-file` (full): complete or body-only content, auto-merges old frontmatter

### 3. ADD-only is mechanically enforced
`update` without `--change-summary` is rejected. `--skip-history` allows opt-out for typo fixes only.

### 4. Content-file body-only merge
When `--content-file` content lacks frontmatter (doesn't start with `---`), wiki_op.py merges old frontmatter + new body. This lets the agent write just the body without worrying about metadata.

### 5. Tag taxonomy lives in SCHEMA.md
wiki_op.py parses SCHEMA.md's Tag Taxonomy section at runtime. Supports both old format (`- **Category**: tags`) and new format (`### Category` headers + comma-separated tags).

### 6. Fuzzy matching (not blocking)
- `create`: warns if similar pages exist (suggests updating instead)
- `validate_wikilinks`: appends "did you mean: X?" suggestions to broken link messages

### 7. Line-number prefix detection
First 12 non-empty lines of content are scanned for `^\s*\d+\|` pattern. If detected, the write is rejected. This prevents the most common corruption source.

## Pitfalls discovered

### execute_code write_file corrupts content
The `hermes_tools.write_file()` inside `execute_code` does NOT strip line-number prefixes from `read_file()` output. When the execute_code reads a file with read_file (which adds `N|` prefixes) and writes it back with write_file, the prefixes become literal content. Fixed in wiki-op-gate.md by using a looped regex cleanup, then wiki_op.py update.

### Inbound link substring match
`find_inbound_links()` originally used `f"[[{{slug}}" in line` which matched substrings (e.g., `hermes-agent` matched `hermes-agent-server`). Fixed with regex `\[\[{re.escape(slug)}(\]\]|[|#])`.

### Taxonomy parser format mismatch
When SCHEMA.md taxonomy was redesigned from `- **Category**: tags` to `### Category` format, `load_tag_taxonomy()` silently returned empty set — all tag validation passed vacuously. Fixed by adding new-format parsing to the parser.
