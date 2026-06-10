#!/usr/bin/env python3
"""Scan wiki pages for expired facts (status=current but valid_until < today).

Registered as the 'stale' subcommand of wiki_op.
"""
import os
import sys
import re
from datetime import date

from wiki_path import resolve_wiki_path


def add_subparser(subparsers):
    """Register the 'stale' subcommand on the given subparsers action."""
    p = subparsers.add_parser(
        "stale",
        help="Scan wiki pages for expired facts (status=current, valid_until < today)",
        description="Walk the wiki directory, parse frontmatter from all .md pages, "
                    "and report any with status=current whose valid_until date has passed.",
    )
    p.add_argument(
        "--wiki-path", default=None,
        help="Path to wiki directory (default: $WIKI_PATH or ~/wiki)",
    )
    p.set_defaults(func=run)


def extract_frontmatter(text):
    """Parse YAML-like frontmatter block from markdown text."""
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def run(args):
    """Main entry point.  args is an argparse.Namespace.

    Returns exit code: 0 if no expired facts, 1 if expired facts found.
    """
    wiki = resolve_wiki_path(args.wiki_path)
    today = date.today()

    expired = []
    for root, dirs, files in os.walk(wiki):
        # Skip hidden directories (starting with . or _)
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_')]
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            fm = extract_frontmatter(content)
            status = fm.get('status', '')
            valid_until = fm.get('valid_until', '')
            if status == 'current' and valid_until:
                try:
                    until_date = date.fromisoformat(valid_until)
                    if until_date < today:
                        expired.append((path, fm.get('title', f), valid_until))
                except ValueError:
                    pass  # malformed date, skip

    if expired:
        print(f"\u26a0\ufe0f  {len(expired)} expired facts found:\n")
        for path, title, vu in expired:
            rel = os.path.relpath(path, wiki)
            print(f"  [{vu}] {title} \u2192 {rel}")
        sys.exit(1)
    else:
        print(f"\u2705 No expired facts ({today})")
