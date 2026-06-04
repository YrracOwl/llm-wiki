# Wiki Self-Check — Four-Point Diagnostic

> Standard health check for the wiki knowledge base. Run when the user says "自查 wiki", after bulk edits, or before closing a session that touched wiki pages.

## The four checks

| Check | What | Severity |
|-------|------|----------|
| Orphan pages | `.md` files on disk but not in `index.md` | 🔴 page invisible to navigation |
| Dangling index refs | `[[slug]]` in index.md but no `.md` on disk | 🔴 broken navigation |
| Expired facts | `valid_until < today` but `status != expired` | 🟡 stale info served as current |
| Broken wikilinks | `[[slug]]` in any page body but no `.md` on disk | 🔴 dead links |

Also report these context metrics:
- **Version snapshots**: count of `_versions/**/*.md` — growing unbounded means cleanup needed
- **Archive count**: count of `_archive/**/*.md` — track accumulation over time

## Run it

Use `execute_code` with this script (or paste the logic into a Python block):

```python
import os, re
from pathlib import Path
from datetime import date

WIKI = Path.home() / "wiki"
INDEX = WIKI / "index.md"

# Collect all non-meta pages — dual-indexed by stem AND full slug
# because index.md may use subdirectory-prefixed slugs (e.g. [[plans/hermes-dreaming]])
# to disambiguate pages with the same stem in different directories.
all_pages_flat = {}   # full_slug → rel_path   (e.g. "plans/hermes-dreaming" → "plans/hermes-dreaming.md")
all_pages_by_stem = {}  # stem → [full_slug, ...]  (e.g. "hermes-dreaming" → ["concepts/hermes-dreaming", "plans/hermes-dreaming"])

for md in WIKI.rglob("*.md"):
    rel = md.relative_to(WIKI)
    if rel.parts[0] in ("_archive", "_versions", ".hermes"):
        continue
    if rel.parts[0] in ("entities", "concepts", "comparisons", "queries", "analyses", "plans", "you"):
        stem = md.stem
        full_slug = str(rel.with_suffix(''))
        all_pages_flat[full_slug] = str(rel)
        all_pages_by_stem.setdefault(stem, []).append(full_slug)

index_text = INDEX.read_text() if INDEX.exists() else ""
index_slugs = set(re.findall(r'\[\[([^\]]+)\]\]', index_text))

# 1. Orphans: page on disk whose full_slug AND stem are both absent from index
orphans = []
for stem, full_slugs in all_pages_by_stem.items():
    if not any(fs in index_slugs or stem in index_slugs for fs in full_slugs):
        orphans.append((stem, full_slugs))

# 2. Dangling: index entry with no matching disk page (try full slug, then bare stem)
dangling = []
for s in index_slugs:
    if s in all_pages_flat:
        continue
    if s.split("/")[-1] in all_pages_by_stem:
        continue
    dangling.append(s)

# 3. Expired: valid_until < today but status != expired
#    Restrict search to frontmatter block to avoid false matches in body text.
today = date.today()
expired = []
for full_slug, rel_path in all_pages_flat.items():
    content = (WIKI / rel_path).read_text(errors='replace')
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    fm = fm_match.group(1) if fm_match else ""
    m = re.search(r'valid_until:\s*(\d{4}-\d{2}-\d{2})', fm)
    if m:
        exp_date = date.fromisoformat(m.group(1))
        m_status = re.search(r'status:\s*(\S+)', fm)
        status_val = m_status.group(1) if m_status else ""
        if exp_date < today and status_val != "expired":
            expired.append((full_slug, str(exp_date), status_val))

# 4. Broken wikilinks: [[link]] in any page body where link is not a valid target
#    Try literal full-slug match first, then bare-stem fallback.
broken = []
for full_slug, rel_path in all_pages_flat.items():
    content = (WIKI / rel_path).read_text(errors='replace')
    for link in re.findall(r'\[\[([^\]]+)\]\]', content):
        if link in all_pages_flat:
            continue
        if link.split("/")[-1] in all_pages_by_stem:
            continue
        broken.append((full_slug, link))

# Summary
page_count = len(all_pages_flat)
print(f"Pages: {page_count} | Index entries: {len(index_slugs)}")
print(f"Orphans: {len(orphans)} | Dangling: {len(dangling)} | Expired: {len(expired)} | Broken: {len(broken)}")

# Context metrics
versions_dir = WIKI / "_versions"
vcount = sum(1 for _ in versions_dir.rglob("*.md")) if versions_dir.exists() else 0
archive_dir = WIKI / "_archive"
acount = sum(1 for _ in archive_dir.rglob("*.md")) if archive_dir.exists() else 0
print(f"Versions: {vcount} | Archive: {acount}")
```

Also run `wiki_op.py lint` for frontmatter/format issues.

## Interpretation

- **Orphans**: A page on disk that appears in neither the index by its full slug (e.g. `plans/hermes-dreaming`) nor by its bare stem (`hermes-dreaming`). Add to `index.md` if it's a legitimate content page. Archive if it's test/transient.
- **Dangling refs**: An `[[slug]]` in index.md with no matching disk file. Either create the page or remove the link from index.
- **Subdirectory-prefixed slugs** (e.g. `[[plans/hermes-dreaming]]`): The script handles these correctly — it tries the literal full slug first, then falls back to bare stem. This supports disambiguation when two pages share the same stem in different directories (e.g. `concepts/hermes-dreaming` and `plans/hermes-dreaming`). No false positives.
- **Expired facts**: `valid_until` date has passed but `status` is not `expired`. Run `wiki_op.py update` with a JSON patch to flip `status: expired` and a change-summary. The script now restricts `valid_until` and `status` regex searches to the YAML frontmatter block only, avoiding false matches in body text.
- **Broken wikilinks**: `[[link]]` in any page body that resolves to no disk page (tried as literal full slug, then bare stem). Fix with correct bare slug or remove if the target doesn't exist.
- **Version count growing fast** (>100): Check if pages are being updated too frequently (each update creates a snapshot). Consider batching edits or rotating old snapshots.
- **Archive count growing**: Normal — but if suddenly spikes, check for accidental bulk-archive.
- **`skills/` directory**: The script intentionally excludes `skills/` from page collection (it's a mapping infrastructure directory, not a content directory). `skills/_mapping.md` will never appear as an orphan or dangling.
