#!/usr/bin/env python3
"""Record and query wiki page visit counts via side-channel SQLite.

Keeps visit data out of markdown frontmatter — no write amplification on every read.

Registered as the 'visits' subcommand of wiki_op with its own sub-subcommands:

    wiki_op visits record <slug>    # +1 visit
    wiki_op visits query <slug>     # show stats for one page
    wiki_op visits top <n>          # top-N most visited
    wiki_op visits cold <n>         # pages untouched for N+ days
    wiki_op visits stats            # global summary

DB: {wiki}/.hermes/visits.db  (single table, WAL mode, lightweight)

Absorbed from ~/wiki/.hermes/scripts/visit_tracker.py
"""

import os
import sqlite3
from datetime import date

from wiki_path import resolve_wiki_path


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS visits (
            page TEXT NOT NULL,
            visited_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (page, visited_at)
        ) WITHOUT ROWID"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_visits_date ON visits(visited_at)"
    )
    return conn


def record(db_path: str, page: str):
    """Insert one visit row. Lightweight, no locking issues under WAL."""
    conn = _connect(db_path)
    conn.execute(
        "INSERT INTO visits (page, visited_at) VALUES (?, datetime('now'))",
        (page,),
    )
    conn.commit()
    conn.close()
    # Silent success — print nothing on write to avoid noise


def query(db_path: str, page: str):
    """Show visit history for a single page."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT visited_at FROM visits WHERE page = ? ORDER BY visited_at DESC",
        (page,),
    ).fetchall()
    total = len(rows)
    first = rows[-1][0] if rows else None
    last = rows[0][0] if rows else None
    conn.close()

    if total == 0:
        print(f"{page}: never visited")
    else:
        print(f"{page}: {total} visits")
        print(f"  First: {first}")
        print(f"  Last:  {last}")


def top(db_path: str, n: int):
    """Print top-N most visited pages."""
    conn = _connect(db_path)
    rows = conn.execute(
        """SELECT page, COUNT(*) AS cnt,
                  MIN(visited_at) AS first, MAX(visited_at) AS last
           FROM visits
           GROUP BY page
           ORDER BY cnt DESC
           LIMIT ?""",
        (n,),
    ).fetchall()
    conn.close()

    if not rows:
        print("No visits recorded yet.")
        return

    print(f"{'Page':<40} {'Visits':>6}  {'First':<19}  {'Last':<19}")
    print("-" * 92)
    for page, cnt, first, last in rows:
        print(f"{page:<40} {cnt:>6}  {first:<19}  {last:<19}")


def cold(db_path: str, days: int):
    """List pages not visited for N+ days (or never visited)."""
    cutoff = date.today().isoformat()

    conn = _connect(db_path)
    # Pages that exist in visits and were last seen >= days ago
    stale = conn.execute(
        """SELECT page, MAX(visited_at) AS last_seen, COUNT(*) AS total
           FROM visits
           GROUP BY page
           HAVING date(?) >= date(last_seen, '+' || ? || ' days')""",
        (cutoff, days),
    ).fetchall()
    conn.close()

    if not stale:
        print(f"No pages cold for {days}+ days.")
        return

    print(f"Pages not visited in {days}+ days:")
    print(f"{'Page':<40} {'Total visits':>6}  {'Last seen'}")
    print("-" * 70)
    for page, last_seen, total in stale:
        print(f"{page:<40} {total:>11}  {last_seen}")


def stats(db_path: str):
    """Global summary: total visits, unique pages, date range."""
    conn = _connect(db_path)
    total = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    uniq = conn.execute("SELECT COUNT(DISTINCT page) FROM visits").fetchone()[0]
    range_row = conn.execute(
        "SELECT MIN(visited_at), MAX(visited_at) FROM visits"
    ).fetchone()
    conn.close()

    print(f"Total visits: {total}")
    print(f"Unique pages: {uniq}")
    print(f"Date range:   {range_row[0] or 'N/A'} → {range_row[1] or 'N/A'}")


def run(args):
    """Main entry point.  args is an argparse.Namespace with wiki_path + visits_cmd + sub-args.

    Returns nothing (prints to stdout).
    """
    wiki = resolve_wiki_path(args.wiki_path)
    db_path = os.path.join(wiki, ".hermes", "visits.db")

    cmd = args.visits_cmd

    if cmd == "record":
        record(db_path, args.slug)
    elif cmd == "query":
        query(db_path, args.slug)
    elif cmd == "top":
        top(db_path, args.n)
    elif cmd == "cold":
        cold(db_path, args.n)
    elif cmd == "stats":
        stats(db_path)
    else:
        print(__doc__)
        return 1


def add_subparser(subparsers):
    """Register the 'visits' subcommand with its own sub-subparsers."""
    p = subparsers.add_parser(
        "visits",
        help="Record and query wiki page visit counts (SQLite side-channel)",
        description=(
            "Record page visits and query visit statistics via a lightweight "
            "SQLite side-channel. Keeps visit data out of markdown frontmatter "
            "— no write amplification on every read.\n\n"
            "Subcommands: record, query, top, cold, stats"
        ),
    )
    p.add_argument(
        "--wiki-path", default=None,
        help="Path to wiki directory (default: $WIKI_PATH or ~/wiki)",
    )

    sub = p.add_subparsers(dest="visits_cmd", help="Visit subcommand")

    # record
    r = sub.add_parser("record", help="Log a visit (+1) for a wiki page")
    r.add_argument("slug", help="Page slug to record a visit for")

    # query
    q = sub.add_parser("query", help="Show visit history for a single page")
    q.add_argument("slug", help="Page slug to query")

    # top
    t = sub.add_parser("top", help="Show top-N most visited pages")
    t.add_argument("n", type=int, help="Number of pages to show")

    # cold
    c = sub.add_parser("cold", help="List pages untouched for N+ days")
    c.add_argument("n", type=int, help="Minimum days since last visit")

    # stats
    sub.add_parser("stats", help="Show global visit summary")

    p.set_defaults(func=run)


# Legacy CLI: direct execution without argparse (e.g. python wiki_op_visits.py record <slug>)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    wiki_path = sys.argv[2] if len(sys.argv) >= 3 and sys.argv[2].startswith("--wiki-path=") else None
    if wiki_path:
        wiki_path = wiki_path.split("=", 1)[1]

    wiki = resolve_wiki_path(wiki_path)
    db_path = os.path.join(wiki, ".hermes", "visits.db")

    if cmd == "record" and len(sys.argv) >= 3 and (wiki_path is None or len(sys.argv) >= 4):
        slug = [a for a in sys.argv[2:] if not a.startswith("--wiki-path=")][0]
        record(db_path, slug)
    elif cmd == "query" and len(sys.argv) >= 3 and (wiki_path is None or len(sys.argv) >= 4):
        slug = [a for a in sys.argv[2:] if not a.startswith("--wiki-path=")][0]
        query(db_path, slug)
    elif cmd == "top" and len(sys.argv) >= 3 and (wiki_path is None or len(sys.argv) >= 4):
        n = int([a for a in sys.argv[2:] if not a.startswith("--wiki-path=")][0])
        top(db_path, n)
    elif cmd == "cold" and len(sys.argv) >= 3 and (wiki_path is None or len(sys.argv) >= 4):
        n = int([a for a in sys.argv[2:] if not a.startswith("--wiki-path=")][0])
        cold(db_path, n)
    elif cmd == "stats":
        stats(db_path)
    else:
        print(__doc__)
        sys.exit(1)
