#!/usr/bin/env python3
"""wiki_op_search.py — BM25 hybrid search for llm-wiki.

Registered as the 'search' subcommand of wiki_op.

Builds a BM25Okapi index over all wiki markdown pages, caches to disk.
Tokenizer splits Chinese characters individually and English into words.

Index cache lives under {wiki_path}/.hermes/ (wiki-specific, not global).
"""

import os
import re
import sys
import json
import pickle
import hashlib
from datetime import datetime, timedelta

from wiki_path import resolve_wiki_path

# ── Config ──────────────────────────────────────────────────
CACHE_MAX_AGE_HOURS = 24
DEFAULT_LIMIT = 10

# Pages to exclude from index
EXCLUDE_FILES = {"index.md", "SCHEMA.md", "log-2026.md", "README.md"}
EXCLUDE_DIRS = {".hermes", "raw", "_versions", "_archive", "_aliases", "skills"}


# ── Tokenizer ───────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """Split Chinese char-by-char, English/numbers into word tokens.

    '威科夫分析 v2.3' → ['威','科','夫','分','析','v2','3']
    'agent memory 系统' → ['agent','memory','系','统']
    """
    tokens = []
    for word in re.findall(
        r'[\u4e00-\u9fff]|[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*|\d+', text.lower()
    ):
        tokens.append(word)
    return tokens


# ── Page loader ─────────────────────────────────────────────
def load_pages(wiki_path: str) -> list[dict]:
    """Walk wiki dir, return list of {path, slug, content, category}."""
    pages = []
    for root, dirs, files in os.walk(wiki_path):
        rel = os.path.relpath(root, wiki_path)
        # Skip excluded dirs and hidden dirs
        parts = rel.split(os.sep)
        if parts[0] in EXCLUDE_DIRS or any(p.startswith('.') for p in parts):
            continue
        for fname in files:
            if not fname.endswith('.md'):
                continue
            if fname in EXCLUDE_FILES:
                continue
            fpath = os.path.join(root, fname)
            slug = fname.replace('.md', '')
            category = parts[0] if len(parts) > 0 else ''
            try:
                with open(fpath) as f:
                    content = f.read()
            except Exception:
                continue
            pages.append({
                "path": fpath,
                "slug": slug,
                "category": category,
                "content": content,
            })
    return pages


# ── Checksum ────────────────────────────────────────────────
def compute_checksum(pages: list[dict]) -> str:
    """Fast hash over (path, mtime) pairs to detect changes."""
    h = hashlib.sha256()
    for p in sorted(pages, key=lambda x: x['path']):
        try:
            mtime = os.path.getmtime(p['path'])
        except OSError:
            mtime = 0
        h.update(f"{p['path']}:{mtime}".encode())
    return h.hexdigest()


# ── Index path helpers ──────────────────────────────────────
def _index_file(wiki_path: str) -> str:
    return os.path.join(wiki_path, ".hermes", "bm25_index.pkl")


def _meta_file(wiki_path: str) -> str:
    return os.path.join(wiki_path, ".hermes", "bm25_meta.json")


# ── Index builder ───────────────────────────────────────────
def build_index(pages, BM25Okapi):
    """Build BM25 index from pages. Returns (bm25, pages, checksum).

    BM25Okapi is passed in (not imported at module level) to support lazy import.
    """
    tokenized = [tokenize(p['content']) for p in pages]
    bm25 = BM25Okapi(tokenized)
    checksum = compute_checksum(pages)
    return bm25, pages, checksum


def save_index(bm25, pages, checksum, wiki_path):
    """Save index + metadata to {wiki_path}/.hermes/."""
    os.makedirs(os.path.join(wiki_path, ".hermes"), exist_ok=True)
    with open(_index_file(wiki_path), 'wb') as f:
        pickle.dump(bm25, f)
    meta = {
        "built_at": datetime.now().isoformat(),
        "checksum": checksum,
        "page_count": len(pages),
        "wiki_path": wiki_path,
    }
    with open(_meta_file(wiki_path), 'w') as f:
        json.dump(meta, f, indent=2)


def load_index(wiki_path):
    """Load cached index from {wiki_path}/.hermes/.

    Returns (bm25, pages, meta) or (None, None, None) on failure.
    Requires rank_bm25 to be importable at call time (for pickle).
    """
    if not os.path.exists(_index_file(wiki_path)):
        return None, None, None
    if not os.path.exists(_meta_file(wiki_path)):
        return None, None, None
    try:
        with open(_index_file(wiki_path), 'rb') as f:
            bm25 = pickle.load(f)
        with open(_meta_file(wiki_path)) as f:
            meta = json.load(f)
        pages = load_pages(wiki_path)
        return bm25, pages, meta
    except Exception:
        return None, None, None


def needs_rebuild(meta, pages):
    """Check if index is stale (age > CACHE_MAX_AGE_HOURS or checksum changed)."""
    if meta is None:
        return True
    # Age check
    built_at = datetime.fromisoformat(meta["built_at"])
    age = datetime.now() - built_at
    if age > timedelta(hours=CACHE_MAX_AGE_HOURS):
        return True
    # Checksum check
    current_checksum = compute_checksum(pages)
    if current_checksum != meta.get("checksum"):
        return True
    return False


# ── Search ──────────────────────────────────────────────────
def search(bm25, pages, query, limit=DEFAULT_LIMIT):
    """Search pages with BM25, return ranked results."""
    tokens = tokenize(query)
    scores = bm25.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in ranked[:limit]:
        if score <= 0:
            break
        p = pages[idx]
        results.append({
            "slug": p['slug'],
            "path": p['path'],
            "category": p['category'],
            "score": round(float(score), 4),
        })
    return results


# ── Output formatters ───────────────────────────────────────
def format_text(results, query):
    """Human-readable table."""
    lines = [f"Search: '{query}' → {len(results)} results\n"]
    lines.append(f"{'#':<3} {'Score':<8} {'Category':<12} Page")
    lines.append("-" * 60)
    for i, r in enumerate(results):
        lines.append(
            f"{i+1:<3} {r['score']:<8} {r['category']:<12} [[{r['slug']}]]"
        )
    return "\n".join(lines)


def format_json(results, query):
    """JSON for Agent consumption."""
    return json.dumps({
        "query": query,
        "count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2)


def format_for_agent(results, query):
    """Compact format for injection into Agent context.

    Returns page slugs + paths — Agent uses read_file for details.
    """
    lines = [f"Wiki BM25 search: '{query}' → {len(results)} results:"]
    for i, r in enumerate(results[:5]):  # top 5 for context injection
        lines.append(f"  #{i+1} [[{r['slug']}]] (score={r['score']:.3f})")
    return "\n".join(lines)


# ── Main entry point ────────────────────────────────────────
def run(args):
    """Main entry point for the 'search' subcommand.

    args is an argparse.Namespace with: query, wiki_path, agent, json,
    rebuild_only, rebuild, limit.

    The rank_bm25 import is LAZY — only imported here, not at module top level.
    This ensures other wiki_op subcommands (stale, entities, bridge) are not
    affected if rank-bm25 is missing.
    """
    # ── LAZY IMPORT: only triggered when search is actually executed ──
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("ERROR: pip install rank-bm25", file=sys.stderr)
        sys.exit(1)

    wiki_path = resolve_wiki_path(args.wiki_path)
    rebuild_only = getattr(args, 'rebuild_only', False)
    force_rebuild = getattr(args, 'rebuild', False) or rebuild_only
    json_out = getattr(args, 'json', False)
    agent_out = getattr(args, 'agent', False)
    limit = getattr(args, 'limit', DEFAULT_LIMIT)
    query = ' '.join(args.query) if args.query else None

    # Load pages
    pages = load_pages(wiki_path)

    # Load or build index
    if force_rebuild:
        bm25, cached_pages, meta = None, None, None
    else:
        bm25, cached_pages, meta = load_index(wiki_path)

    if bm25 is None or needs_rebuild(meta, pages):
        bm25, pages, checksum = build_index(pages, BM25Okapi)
        save_index(bm25, pages, checksum, wiki_path)
        if not rebuild_only:
            print(f"[index rebuilt: {len(pages)} pages]", file=sys.stderr)

    if rebuild_only:
        print(f"Index rebuilt: {len(pages)} pages")
        return

    if not query:
        print(
            "Usage: wiki_op search [--rebuild] [--json] [--agent] <query>",
            file=sys.stderr,
        )
        sys.exit(1)

    results = search(bm25, pages, query, limit)

    if agent_out:
        print(format_for_agent(results, query))
    elif json_out:
        print(format_json(results, query))
    else:
        print(format_text(results, query))


# ── Subcommand registration ─────────────────────────────────
def add_subparser(subparsers):
    """Register the 'search' subcommand on the given subparsers action."""
    p = subparsers.add_parser(
        "search",
        help="BM25 search over wiki markdown pages",
        description=(
            "Builds a BM25Okapi index over all wiki markdown pages, "
            "caches to {wiki}/.hermes/, and searches with a "
            "Chinese+English tokenizer."
        ),
    )
    p.add_argument(
        "query",
        nargs="*",
        help="Search query (multi-word supported)",
    )
    p.add_argument(
        "--agent",
        action="store_true",
        help="Compact output for Agent context injection",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="JSON output for programmatic consumption",
    )
    p.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Rebuild index and exit (no search)",
    )
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild index before searching",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum results to return (default: {DEFAULT_LIMIT})",
    )
    p.add_argument(
        "--wiki-path",
        default=None,
        help="Path to wiki directory (default: $WIKI_PATH or ~/wiki)",
    )
    p.set_defaults(func=run)
