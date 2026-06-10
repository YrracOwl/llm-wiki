#!/usr/bin/env python3
"""
wiki_op.py — Single entry point for all LLM Wiki write operations.

Design: Agent never touches ~/wiki/*.md directly. All writes go through this gate.
The script enforces frontmatter completeness, index synchronization, log entries,
version snapshots, and content validation — mechanically, not via agent memory.

Usage:
  python3 wiki_op.py create  --page entities/foo --type entity --title "Foo" --tags "a,b" --content-file /tmp/draft.md
  python3 wiki_op.py update  --page entities/foo --content-file /tmp/new.md --change-summary "Added section"
  python3 wiki_op.py update  --page entities/foo --patch-file /tmp/patch.json --change-summary "Fix typo"
  python3 wiki_op.py delete  --page entities/foo [--force]
  python3 wiki_op.py lint    [--page entities/foo] [--fix]
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_path import resolve_wiki_path, add_wiki_path_argument

# ── Configuration ──────────────────────────────────────────────────

# WIKI_ROOT is set dynamically in main() via resolve_wiki_path()
# All other module-level config paths (SCHEMA_PATH, etc.) are also set in main()
WIKI_ROOT = None
SCHEMA_PATH = None
INDEX_PATH = None
LOG_PATH = None
VERSIONS_DIR = None
ARCHIVE_DIR = None

# Directories that contain wiki pages (searched for wikilink resolution)
PAGE_DIRS = ["entities", "concepts", "comparisons", "queries", "analyses", "you", "plans"]
# Directories the script manages index sections for
INDEXED_DIRS = {
    "entities": "Entities",
    "concepts": "Concepts",
    "comparisons": "Comparisons",
    "queries": "Queries",
    "analyses": "Analyses",
    "you": "You",
    "plans": "Plans",
}
# Directories that are off-limits for writes
RESERVED_DIRS = {"_versions", "_archive", ".hermes", "raw", "skills"}

REQUIRED_FM = ["title", "created", "updated", "type", "tags"]


def _init_paths(wiki_root: str):
    """Initialize all path globals from resolved wiki root. Called from main()."""
    global WIKI_ROOT, SCHEMA_PATH, INDEX_PATH, LOG_PATH, VERSIONS_DIR, ARCHIVE_DIR
    WIKI_ROOT = Path(wiki_root).resolve()
    SCHEMA_PATH = WIKI_ROOT / "SCHEMA.md"
    INDEX_PATH = WIKI_ROOT / "index.md"
    LOG_PATH = WIKI_ROOT / "log.md"
    VERSIONS_DIR = WIKI_ROOT / "_versions"
    ARCHIVE_DIR = WIKI_ROOT / "_archive"

REQUIRED_FM = ["title", "created", "updated", "type", "tags"]


# ── Helpers ────────────────────────────────────────────────────────

def die(msg: str, code: int = 1) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"⚠️  {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"✅ {msg}")


# ── Schema Parsing ─────────────────────────────────────────────────

def load_tag_taxonomy() -> set:
    """Parse SCHEMA.md Tag Taxonomy section. Supports two formats:
    Old: - **Category**: tag1, tag2, tag3
    New: ### Category (H3) followed by comma-separated tag lines."""
    if not SCHEMA_PATH.exists():
        return set()
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    in_section = False
    tags = set()
    for line in text.split("\n"):
        if line.startswith("## Tag Taxonomy"):
            in_section = True
            continue
        if not in_section:
            continue
        # End of taxonomy section
        if line.startswith("## ") and "Tag Taxonomy" not in line:
            break
        # New format: ### Category Name (H3 header, tags on subsequent lines)
        if line.startswith("### "):
            continue  # category header, tags follow on next lines
        # Old format: - **Category**: tag1, tag2
        m = re.match(r'-\s+\*\*[^*]+\*\*:\s*(.+)', line)
        if m:
            for t in re.split(r'[,;]', m.group(1)):
                t = t.strip().rstrip(".")
                if t:
                    tags.add(t)
            continue
        # New format: bare comma-separated tags (no bullet, no bold)
        stripped = line.strip()
        if stripped and not stripped.startswith("-") and not stripped.startswith("Rule"):
            for t in re.split(r'[,;]', stripped):
                t = t.strip().rstrip(".")
                if t and not t.startswith("#"):
                    tags.add(t)
    return tags


def load_valid_types() -> set:
    """Extract valid 'type' values from SCHEMA.md frontmatter template."""
    if not SCHEMA_PATH.exists():
        return {"entity", "concept", "comparison", "query"}
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    m = re.search(r'type:\s*(.+)', text)
    if m:
        return {t.strip() for t in re.split(r'\s*\|\s*', m.group(1)) if t.strip()}
    return {"entity", "concept", "comparison", "query"}


# ── Path Validation ────────────────────────────────────────────────

def resolve_page_path(page: str) -> Path:
    """Validate and resolve a page path argument. Returns absolute Path."""
    page = page.strip("/")
    if not page.endswith(".md"):
        page += ".md"
    full = (WIKI_ROOT / page).resolve()
    # Security: must be under wiki root
    if not str(full).startswith(str(WIKI_ROOT)):
        die(f"Path escapes wiki root: {page}")
    rel = full.relative_to(WIKI_ROOT)
    parts = rel.parts
    if len(parts) < 2:
        die(f"Page must be in a subdirectory (e.g., entities/foo): {page}")
    top_dir = parts[0]
    if top_dir in RESERVED_DIRS:
        die(f"Cannot write to reserved directory '{top_dir}/'. Use a content directory.")
    return full


def page_to_bare_slug(page_path: Path) -> str:
    """Extract the bare slug (filename without .md or directory)."""
    return page_path.stem


def page_dir(page_path: Path) -> str:
    """Get the content directory name (e.g., 'entities', 'concepts')."""
    return page_path.relative_to(WIKI_ROOT).parts[0]


def resolve_wikilink(slug: str) -> Optional[Path]:
    """Resolve a bare wikilink slug to an actual .md file in any content directory."""
    slug_clean = slug.strip().replace("/", "-")  # normalize
    for d in PAGE_DIRS:
        candidate = WIKI_ROOT / d / f"{slug_clean}.md"
        if candidate.exists():
            return candidate
    # Also try without normalization
    for d in PAGE_DIRS:
        candidate = WIKI_ROOT / d / f"{slug}.md"
        if candidate.exists():
            return candidate
    return None


# ── Content Validation ─────────────────────────────────────────────

def check_line_number_corruption(content: str) -> Optional[str]:
    """Detect if content starts with read_file line-number prefixes.
    Returns error message if corrupted, None if clean."""
    lines = content.split("\n")
    checked = 0
    for line in lines[:12]:
        stripped = line.strip()
        if stripped:
            if re.match(r'^\s*\d+\|', line):
                return f"Line-number prefix detected: {line[:80]!r} — content looks like read_file output"
            checked += 1
            if checked >= 5:
                break
    return None


def parse_frontmatter(content: str) -> Tuple[Dict, Optional[str], str]:
    """Parse YAML frontmatter from content.
    Returns (parsed_dict, error_or_None, content_with_possible_fixes)."""
    if not content.startswith("---"):
        return {}, "Missing opening '---' for frontmatter", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, "Frontmatter not closed (missing second '---')", content
    fm_text = parts[1]
    body = parts[2]
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1]
                fm[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
            else:
                fm[key] = value
    return fm, None, content


def validate_frontmatter(content: str, fix: bool = False) -> Tuple[Dict, Optional[str], str]:
    """Validate and optionally fix frontmatter.
    Returns (fm_dict, error_or_None, maybe_fixed_content)."""
    fm, err, content = parse_frontmatter(content)
    if err:
        return fm, err, content
    missing = [f for f in REQUIRED_FM if f not in fm]
    if not missing:
        return fm, None, content
    if not fix:
        return fm, f"Missing required fields: {', '.join(missing)}", content
    # Auto-fix: extract body (everything after the second '---')
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    today = now_str()
    defaults = {
        "title": "Untitled",
        "created": today,
        "updated": today,
        "type": "concept",
        "tags": [],
    }
    for f in missing:
        fm[f] = defaults.get(f, "")
    new_fm_block = build_frontmatter_block(fm)
    new_content = f"---\n{new_fm_block}---\n{body}"
    return fm, None, new_content


def build_frontmatter_block(fm: dict) -> str:
    """Serialize a frontmatter dict back to YAML-ish text."""
    lines = []
    for key in REQUIRED_FM:
        val = fm.get(key)
        if isinstance(val, list):
            lines.append(f"{key}: [{', '.join(val)}]")
        else:
            lines.append(f"{key}: {val}")
    for key in fm:
        if key not in REQUIRED_FM:
            val = fm[key]
            if isinstance(val, list):
                lines.append(f"{key}: [{', '.join(val)}]")
            else:
                lines.append(f"{key}: {val}")
    return "\n".join(lines) + "\n"


def validate_tags(tags, taxonomy: set) -> Optional[str]:
    """Check tags against SCHEMA taxonomy."""
    if not taxonomy:
        return None
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    invalid = [t for t in tags if t not in taxonomy]
    if invalid:
        sample = ", ".join(sorted(taxonomy)[:15])
        return f"Tags not in taxonomy: {', '.join(invalid)}. Valid: {sample}..."
    return None


def find_wikilinks(content: str) -> List[str]:
    """Extract all [[target]] slugs from content. Skips inline code and fenced code blocks."""
    # Strip fenced code blocks
    cleaned = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    # Strip inline code spans
    cleaned = re.sub(r'`[^`]+`', '', cleaned)
    return re.findall(r'\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]', cleaned)


def validate_wikilinks(content: str) -> List[str]:
    """Check [[wikilinks]] for broken targets. Returns list of broken slugs with suggestions."""
    broken = []
    for slug in find_wikilinks(content):
        slug = slug.strip()
        if not slug:
            continue
        if resolve_wikilink(slug) is None:
            similar = fuzzy_find_similar(slug)
            msg = slug
            if similar:
                msg += f" (did you mean: {', '.join(similar[:3])}?)"
            broken.append(msg)
    return broken


# ── Atomic & Snapshot ──────────────────────────────────────────────

def atomic_write(path: Path, content: str) -> None:
    """Write content to a temp file then atomically rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(path))


def create_snapshot(page_path: Path) -> Optional[Path]:
    """Save a timestamped copy to _versions/. Returns snapshot path or None."""
    if not page_path.exists():
        return None
    slug = page_path.stem
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snap_dir = VERSIONS_DIR / slug
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"{ts}.md"
    shutil.copy2(page_path, snap_path)
    return snap_path


# ── Index Management ───────────────────────────────────────────────

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _parse_index(text: str) -> dict:
    """
    Parse index.md into structured data.
    Returns: {"header": str, "sections": {"Entities": [(slug, summary, raw_line), ...]}}
    """
    sections: Dict[str, List[Tuple[str, str, str]]] = {}
    current_section = None
    header = []
    in_header = True

    for line in text.split("\n"):
        if in_header:
            if line.startswith("## "):
                in_header = False
            else:
                header.append(line)
                continue

        if line.startswith("## "):
            current_section = line[3:].strip()
            if current_section not in sections:
                sections[current_section] = []
        elif current_section and line.strip():
            m = re.match(r'-\s*\[\[([^\]]+)\]\]\s*[—–\-]\s*(.*)', line)
            if m:
                sections[current_section].append((m.group(1).strip(), m.group(2).strip(), line))

    return {"header": header, "sections": sections}


def _build_index(parsed: dict) -> str:
    """Rebuild index.md from parsed data."""
    total = sum(len(v) for v in parsed["sections"].values())
    today = now_str()
    lines = []
    for h in parsed["header"]:
        if "Last updated:" in h or "Total pages:" in h:
            lines.append(f"> Last updated: {today} | Total pages: {total}")
        elif h not in lines:
            lines.append(h)
    lines.append("")
    for sec_name in INDEXED_DIRS.values():
        entries = parsed["sections"].get(sec_name, [])
        if not entries:
            continue
        lines.append(f"## {sec_name}")
        lines.append("")
        for slug, summary, raw_line in entries:
            # Always output with bare slug
            lines.append(f"- [[{slug}]] — {summary}")
        lines.append("")
    # Also output sections not in INDEXED_DIRS (e.g., custom sections)
    for sec_name, entries in parsed["sections"].items():
        if sec_name in INDEXED_DIRS.values():
            continue
        if not entries:
            continue
        lines.append(f"## {sec_name}")
        lines.append("")
        for slug, summary, raw_line in entries:
            lines.append(f"- [[{slug}]] — {summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_index(page_path: Path, action: str, title: str = "") -> None:
    """
    action: 'add' | 'remove' | 'update-title'
    title: summary text for 'add', new title for 'update-title'
    """
    if not INDEX_PATH.exists():
        warn(f"index.md not found at {INDEX_PATH}")
        return

    slug = page_to_bare_slug(page_path)
    dir_name = page_dir(page_path)
    section_name = INDEXED_DIRS.get(dir_name)
    if not section_name:
        warn(f"No index section mapped for directory '{dir_name}/'")
        return

    content = INDEX_PATH.read_text(encoding="utf-8")
    parsed = _parse_index(content)

    if section_name not in parsed["sections"]:
        parsed["sections"][section_name] = []

    entries = parsed["sections"][section_name]

    if action == "remove":
        parsed["sections"][section_name] = [
            (s, sm, rl) for s, sm, rl in entries if s != slug
        ]
        total = sum(len(v) for v in parsed["sections"].values())
        ok(f"Removed from index: {slug} (now {total} pages)")

    elif action == "update-title":
        for i, (s, sm, rl) in enumerate(entries):
            if s == slug:
                entries[i] = (slug, title, f"- [[{slug}]] — {title}")
                break
        ok(f"Index title updated: {slug}")

    elif action == "add":
        summary = title
        # Check if already present
        existing = [s for s, sm, rl in entries if s == slug]
        if existing:
            # Update summary instead
            for i, (s, sm, rl) in enumerate(entries):
                if s == slug:
                    entries[i] = (slug, summary, f"- [[{slug}]] — {summary}")
            ok(f"Index entry updated: {slug}")
        else:
            # Insert alphabetically
            new_entry = (slug, summary, f"- [[{slug}]] — {summary}")
            inserted = False
            for i, (s, sm, rl) in enumerate(entries):
                if slug.lower() < s.lower():
                    entries.insert(i, new_entry)
                    inserted = True
                    break
            if not inserted:
                entries.append(new_entry)
            total = sum(len(v) for v in parsed["sections"].values())
            ok(f"Index: +{slug} ({total} pages)")

    new_index = _build_index(parsed)
    atomic_write(INDEX_PATH, new_index)


# ── Log Management ─────────────────────────────────────────────────

def append_log(action: str, page_path: Path, details: str) -> None:
    """Append a standardized entry to log.md."""
    if not LOG_PATH.exists():
        warn(f"log.md not found at {LOG_PATH}")
        return
    today = now_str()
    slug = page_to_bare_slug(page_path)
    entry = f"\n## {today} {action} | {slug}\n\n- {details}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)
    ok(f"Log: {today} {action} | {slug}")


# ── History Section ────────────────────────────────────────────────

def bump_updated_date(content: str) -> str:
    """Update the 'updated' field in frontmatter to today."""
    today = now_str()
    return re.sub(r'(updated:\s*)\S+', f'updated: {today}', content, count=1)


def append_history_section(content: str, change_summary: str) -> str:
    """Append a timestamped entry to the page's '历史记录' section."""
    today = now_str()
    entry = f"\n### [{today}] {change_summary}\n"
    marker = "## 历史记录"
    if marker in content:
        # Find the last ### entry in the section and append after it
        idx = content.index(marker)
        section_start = idx
        # Find next ## section or end of file
        rest = content[section_start:]
        next_section = re.search(r'\n## (?!历史记录)', rest)
        if next_section:
            insert_at = section_start + next_section.start()
        else:
            insert_at = len(content)
        return content[:insert_at].rstrip() + entry + "\n" + content[insert_at:].lstrip()
    else:
        return content.rstrip() + f"\n\n## 历史记录\n\n{entry}"


# ── Inbound Links ──────────────────────────────────────────────────

def find_inbound_links(page_path: Path) -> list:
    """Find all pages that link to the given page. Returns [(source_path, line_num), ...]."""
    slug = page_to_bare_slug(page_path)
    results = []
    for md_file in WIKI_ROOT.rglob("*.md"):
        if md_file == page_path:
            continue
        parts = md_file.relative_to(WIKI_ROOT).parts
        if parts[0] in RESERVED_DIRS or parts[0].startswith("."):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.split("\n"), 1):
            # Match exact slug: [[slug]], [[slug|..., or [[slug#...
            pattern = rf'\[\[{re.escape(slug)}(\]\]|[|#])'
            if re.search(pattern, line):
                results.append((md_file, i))
    return results


# ── Patch Application ──────────────────────────────────────────────

def fuzzy_find_similar(slug: str, max_distance: int = 3) -> List[str]:
    """Find existing pages with similar names to the given slug.
    Returns list of 'dir/basename' strings, sorted by similarity."""
    import difflib
    candidates = []
    for d in PAGE_DIRS:
        pd = WIKI_ROOT / d
        if not pd.exists():
            continue
        for fp in pd.rglob("*.md"):
            existing = fp.stem
            # Exact prefix match gets priority
            if existing.startswith(slug) or slug.startswith(existing):
                candidates.append((0, f"{d}/{fp.name}"))
            else:
                ratio = difflib.SequenceMatcher(None, slug.lower(), existing.lower()).ratio()
                if ratio > 0.6:
                    candidates.append((1 - ratio, f"{d}/{fp.name}"))
    candidates.sort()
    return [name for _, name in candidates[:5]]

def apply_json_patch(content: str, patch_data: dict) -> str:
    """Apply a {old: ..., new: ...} patch. old must be unique in the file."""
    old = patch_data.get("old", "")
    new = patch_data.get("new", "")
    if not old:
        die("Patch 'old' field is required and must not be empty")
    count = content.count(old)
    if count == 0:
        die(f"Patch 'old' text not found in file ({len(old)} chars)")
    if count > 1:
        die(f"Patch 'old' text found {count} times — must be unique. Use --content-file for complex changes.")
    return content.replace(old, new)


# ═══════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════

def cmd_create(args) -> None:
    taxonomy = load_tag_taxonomy()
    valid_types = load_valid_types()

    page_path = resolve_page_path(args.page)
    if page_path.exists():
        die(f"Page already exists: {args.page}")

    # Fuzzy duplicate check — warn if similar pages exist
    slug = page_to_bare_slug(page_path)
    similar = fuzzy_find_similar(slug)
    if similar:
        warn(f"Similar pages exist: {', '.join(similar)}")
        warn("Consider updating an existing page instead of creating a duplicate.")

    if args.type not in valid_types:
        die(f"Invalid type '{args.type}'. Must be: {', '.join(sorted(valid_types))}")

    # Read content
    if args.content_file:
        draft = Path(args.content_file)
        if not draft.exists():
            die(f"Content file not found: {args.content_file}")
        body = draft.read_text(encoding="utf-8")
    else:
        die("--content-file is required for 'create'")

    # Validate content
    err = check_line_number_corruption(body)
    if err:
        die(f"Content rejected: {err}")

    # Validate tags
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    err = validate_tags(tags, taxonomy)
    if err:
        die(err)

    # Build full page with frontmatter
    today = now_str()
    fm = {
        "title": args.title,
        "created": today,
        "updated": today,
        "type": args.type,
        "tags": tags,
    }
    if args.sources:
        fm["sources"] = [s.strip() for s in args.sources.split(",")]

    full = f"---\n{build_frontmatter_block(fm)}---\n\n{body.lstrip()}"

    # Validate wikilinks (warning only)
    broken = validate_wikilinks(full)

    # Write
    atomic_write(page_path, full)
    ok(f"Created {args.page} ({len(full.splitlines())} lines, {len(find_wikilinks(full))} wikilinks)")

    # Index
    update_index(page_path, "add", args.title)

    # Log
    details = f"create {args.type} | {args.title}"
    if broken:
        details += f"\n- ⚠️  {len(broken)} broken wikilinks: {', '.join(broken[:5])}"
    if args.sources:
        details += f"\n- sources: {args.sources}"
    append_log("create", page_path, details)

    if broken:
        warn(f"Broken wikilinks: {', '.join(broken)}")

    # Clean up temp file
    if args.content_file:
        try:
            Path(args.content_file).unlink(missing_ok=True)
        except OSError:
            pass


def cmd_update(args) -> None:
    taxonomy = load_tag_taxonomy()
    page_path = resolve_page_path(args.page)
    if not page_path.exists():
        die(f"Page not found: {args.page}")

    # ── ADD-only enforcement ──
    if not args.change_summary and not args.skip_history:
        die(
            "ADD-only protocol requires --change-summary for updates.\n"
            "  Provide --change-summary \"what changed and why\"\n"
            "  Or use --skip-history for typo/formatting fixes only."
        )

    current = page_path.read_text(encoding="utf-8")

    # Determine new content
    if args.content_file:
        draft = Path(args.content_file)
        if not draft.exists():
            die(f"Content file not found: {args.content_file}")
        raw = draft.read_text(encoding="utf-8")
        # Guard: refuse trivially-small content files (e.g. /dev/null → 0 bytes)
        raw_bytes = draft.stat().st_size
        if raw_bytes < 50 and not args.force:
            die(
                f"Content file is only {raw_bytes} bytes. "
                "--content-file does FULL REPLACEMENT, not append. "
                "If intentional (e.g. rewriting a page from scratch), use --force."
            )
        # If new content has no frontmatter (doesn't start with ---), merge:
        # keep old frontmatter + new body
        if not raw.lstrip().startswith("---"):
            old_fm_text = current.split("---", 2)[1] if current.startswith("---") else ""
            new_content = f"---\n{old_fm_text}---\n{raw.lstrip()}"
        else:
            new_content = raw
    elif args.patch_file:
        try:
            patch_data = json.loads(Path(args.patch_file).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            die(f"Patch file error: {e}")
        new_content = apply_json_patch(current, patch_data)
    else:
        die("Either --content-file or --patch-file is required for 'update'")

    # Guard: drastic body shrink (<10% of old size) for --content-file
    # --patch-file is surgical by design, skip the check
    if args.content_file and not args.force:
        old_body = current.split("---", 2)[2] if current.startswith("---") and current.count("---") >= 2 else current
        new_body = new_content.split("---", 2)[2] if new_content.startswith("---") and new_content.count("---") >= 2 else new_content
        old_sz = len(old_body.encode("utf-8"))
        new_sz = len(new_body.encode("utf-8"))
        if old_sz > 0 and new_sz / max(old_sz, 1) < 0.10:
            die(
                f"New body is {new_sz:,} bytes — only {new_sz / old_sz:.0%} of old ({old_sz:,} bytes). "
                "--content-file does FULL REPLACEMENT, not append. "
                "If you meant to make a small edit, use --patch-file instead. "
                "If you intentionally rewrote the page to be much shorter, use --force."
            )

    # Validate content
    err = check_line_number_corruption(new_content)
    if err:
        die(f"Content rejected: {err}")

    # Validate and fix frontmatter
    fm, fm_err, new_content = validate_frontmatter(new_content, fix=True)
    if fm_err and "Missing opening" in fm_err:
        die(f"Frontmatter: {fm_err}")

    # Validate tags
    if fm.get("tags"):
        tags = fm["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        err = validate_tags(tags, taxonomy)
        if err:
            die(err)

    # Bump updated date
    new_content = bump_updated_date(new_content)

    # Append history if change summary provided
    if args.change_summary:
        new_content = append_history_section(new_content, args.change_summary)

    # Snapshot current version
    snap = create_snapshot(page_path)
    if snap:
        ok(f"Snapshot: {snap.relative_to(WIKI_ROOT)}")

    # Validate wikilinks
    broken = validate_wikilinks(new_content)

    # Check title change
    old_fm, _, _ = parse_frontmatter(current)
    title_changed = old_fm.get("title") != fm.get("title")

    # Write
    atomic_write(page_path, new_content)

    # Index (if title changed)
    if title_changed and fm.get("title"):
        update_index(page_path, "update-title", fm["title"])

    # Log
    summary = args.change_summary or "(skip-history: no summary)"
    details = f"update | {summary}"
    if broken:
        details += f"\n- ⚠️  {len(broken)} broken wikilinks: {', '.join(broken[:5])}"
    if title_changed:
        details += f"\n- title changed: {old_fm.get('title')} → {fm.get('title')}"
    append_log("update", page_path, details)

    ok(f"Updated {args.page}")
    ok(f"Wikilinks: {len(find_wikilinks(new_content))} outbound, {len(broken)} broken")
    if broken:
        warn(f"Broken: {', '.join(broken)}")

    # Clean up temp files
    for fpath in [args.content_file, args.patch_file]:
        if fpath:
            try:
                Path(fpath).unlink(missing_ok=True)
            except OSError:
                pass


def cmd_delete(args) -> None:
    page_path = resolve_page_path(args.page)
    if not page_path.exists():
        die(f"Page not found: {args.page}")

    # Check inbound links
    inbound = find_inbound_links(page_path)
    if inbound and not args.force:
        print(f"⚠️  {len(inbound)} inbound link(s) from:")
        for src, lineno in inbound[:20]:
            print(f"    {src.relative_to(WIKI_ROOT)}:{lineno}")
        if len(inbound) > 20:
            print(f"    ... and {len(inbound) - 20} more")
        die("Use --force to archive anyway (remember to update referring pages).")

    # Move to archive
    rel = page_path.relative_to(WIKI_ROOT)
    archive_path = ARCHIVE_DIR / rel
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(page_path), str(archive_path))
    ok(f"Archived → _archive/{rel}")

    # Remove from index
    update_index(page_path, "remove")

    # Log
    inbound_slugs = [src.stem for src, _ in inbound[:5]]
    details = f"archived to _archive/{rel}"
    if inbound_slugs:
        details += f"\n- inbound links from: {', '.join(inbound_slugs)}"
    append_log("archive", page_path, details)

    if inbound:
        warn(f"Update {len(inbound)} referring pages that linked to [[{page_to_bare_slug(page_path)}]].")


def cmd_lint(args) -> None:
    taxonomy = load_tag_taxonomy()
    issues: List[str] = []

    # Determine scope
    if args.page:
        page_path = resolve_page_path(args.page)
        targets = [page_path] if page_path.exists() else []
        if not targets:
            die(f"Page not found: {args.page}")
    else:
        targets = []
        for d in PAGE_DIRS:
            pd = WIKI_ROOT / d
            if pd.exists():
                targets.extend(sorted(pd.rglob("*.md")))

    # Per-file checks
    for fp in targets:
        rel = fp.relative_to(WIKI_ROOT)
        try:
            content = fp.read_text(encoding="utf-8")
        except Exception as e:
            issues.append(f"🔴 {rel}: cannot read — {e}")
            continue

        # 1. Line-number corruption
        err = check_line_number_corruption(content)
        if err:
            issues.append(f"🔴 {rel}: LINE-NUMBER CORRUPTION")

        # 2. Frontmatter
        fm, fm_err, _ = validate_frontmatter(content)
        if fm_err:
            if args.fix:
                _, _, fixed = validate_frontmatter(content, fix=True)
                atomic_write(fp, fixed)
                ok(f"Fixed frontmatter: {rel}")
            else:
                issues.append(f"🟡 {rel}: {fm_err}")

        # 3. Tags
        if fm.get("tags"):
            tags = fm["tags"]
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            err = validate_tags(tags, taxonomy)
            if err:
                issues.append(f"🟡 {rel}: {err}")

        # 4. Broken wikilinks
        broken = validate_wikilinks(content)
        for b in broken:
            issues.append(f"🔴 {rel}: broken wikilink '{b}'")

    # 5. Index completeness (full scan only)
    if not args.page:
        index_text = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        indexed_slugs = set()
        for m in re.finditer(r'\[\[([^\]]+)\]\]', index_text):
            indexed_slugs.add(m.group(1).strip())

        for d in PAGE_DIRS:
            pd = WIKI_ROOT / d
            if not pd.exists():
                continue
            for fp in pd.rglob("*.md"):
                rel_path = str(fp.relative_to(WIKI_ROOT))
                slug = fp.stem
                # Index may contain bare slug or dir/slug — match both
                dir_slug = f"{d}/{slug}"
                if slug not in indexed_slugs and dir_slug not in indexed_slugs:
                    issues.append(f"🔴 {rel_path}: not in index.md")
                    if args.fix:
                        # Read title from frontmatter
                        try:
                            text = fp.read_text(encoding="utf-8")
                            fm, _, _ = parse_frontmatter(text)
                            title = fm.get("title", slug)
                        except Exception:
                            title = slug
                        update_index(fp, "add", title)

    # Report
    if not issues:
        ok("Wiki lint passed — no issues found.")
    else:
        print(f"\n📋 {len(issues)} issue(s):")
        for issue in issues:
            print(f"  {issue}")

    if args.fix:
        ok("Auto-fix applied where possible.")


# ── Built-in: snapshot ──────────────────────────────────────────────
def cmd_snapshot(args):
    """Expose create_snapshot as a standalone subcommand."""
    page_path = resolve_page_path(args.page)
    if not page_path.exists():
        die(f"Page not found: {args.page}")
    snap = create_snapshot(page_path)
    if snap:
        ok(f"Snapshot: {snap.relative_to(WIKI_ROOT)}")

# ── Built-in: path ──────────────────────────────────────────────────
def cmd_path(args):
    """Print resolved wiki path (debug helper)."""
    print(WIKI_ROOT)

# ── Module dispatch registry ─────────────────────────────────────────
MODULES = {
    "stale": "wiki_op_stale",
    "entities": "wiki_op_entities",
    "bridge": "wiki_op_bridge",
    "visits": "wiki_op_visits",
    "search": "wiki_op_search",
}

def _load_module(name):
    """Lazy-load a wiki_op module by name. Returns module or None on ImportError."""
    try:
        mod = __import__(name)
        return mod
    except ImportError as e:
        return None

# ── CLI Dispatch ────────────────────────────────────────────────────

def main() -> None:
    _init_paths(resolve_wiki_path())

    parser = argparse.ArgumentParser(
        description="wiki_op.py — LLM Wiki Write Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a page
  wiki_op.py create --page entities/my-tool --type entity \\
    --title \"My Tool\" --tags \"cli,automation\" --content-file /tmp/draft.md

  # Update with full new content
  wiki_op.py update --page entities/my-tool \\
    --content-file /tmp/updated.md --change-summary \"Added section\"

  # Lint
  wiki_op.py lint                # full scan
  wiki_op.py lint --fix          # auto-fix

  # Diagnostics
  wiki_op.py stale               # scan expired facts
  wiki_op.py snapshot concepts/p # manual snapshot
  wiki_op.py entities \"text\"    # entity link suggestions
  wiki_op.py bridge path/SKILL.md # skill-wiki bridge
  wiki_op.py visits top 10       # visit heatmap
  wiki_op.py search \"query\" --agent  # BM25 search
  wiki_op.py path                # print resolved wiki path
        """,
    )

    # --wiki-path is a top-level flag for the dispatch
    add_wiki_path_argument(parser)

    sub = parser.add_subparsers(dest="command", help="Operation")

    # ── Built-in subcommands ──
    p = sub.add_parser("create", help="Create a new wiki page")
    p.add_argument("--page", required=True, help="Page path, e.g. entities/my-page")
    p.add_argument("--type", required=True, help="entity | concept | comparison | query")
    p.add_argument("--title", required=True, help="Page title")
    p.add_argument("--tags", required=True, help="Comma-separated tags")
    p.add_argument("--content-file", help="Path to temp file with page body")
    p.add_argument("--sources", help="Comma-separated source references")

    p = sub.add_parser("update", help="Update an existing wiki page")
    p.add_argument("--page", required=True)
    p.add_argument("--content-file", help="Path to temp file with full updated content")
    p.add_argument("--patch-file", help='Path to JSON file: {"old":"...","new":"..."}')
    p.add_argument("--change-summary", help="Short description (appended to history + log)")
    p.add_argument("--skip-history", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("delete", help="Archive a wiki page")
    p.add_argument("--page", required=True)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("lint", help="Lint wiki for issues")
    p.add_argument("--page", help="Check a single page only")
    p.add_argument("--fix", action="store_true")

    p = sub.add_parser("snapshot", help="Create a version snapshot of a page")
    p.add_argument("--page", required=True, help="Page path, e.g. concepts/foo")

    p = sub.add_parser("path", help="Print resolved wiki path")

    # ── Register module subcommands (lazy load, graceful degradation) ──
    for cmd_name, mod_name in MODULES.items():
        mod = _load_module(mod_name)
        if mod is None:
            continue  # module unavailable, skip silently
        if hasattr(mod, 'add_subparser'):
            mod.add_subparser(sub)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Re-resolve wiki path with CLI flag
    if hasattr(args, 'wiki_path') and args.wiki_path:
        _init_paths(resolve_wiki_path(args.wiki_path))

    if not WIKI_ROOT.exists():
        die(f"Wiki root not found: {WIKI_ROOT}")

    # Built-in dispatch
    dispatch = {
        "create": cmd_create,
        "update": cmd_update,
        "delete": cmd_delete,
        "lint": cmd_lint,
        "snapshot": cmd_snapshot,
        "path": cmd_path,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    elif args.command in MODULES:
        # Module commands use func default from add_subparser
        mod = _load_module(MODULES[args.command])
        if mod is None:
            die(f"Module unavailable: {MODULES[args.command]}. Check dependencies.")
        mod.run(args)
    else:
        die(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
