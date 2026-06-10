#!/usr/bin/env python3
"""Scan text for known entity aliases and suggest wikilinks.

Subcommand: entities
  wiki_op.py entities "some text with entity names"
  echo "some text" | wiki_op.py entities -

Absorbed from ~/wiki/.hermes/scripts/entity_link.py
"""

import os
import sys
import json
import re

from wiki_path import resolve_wiki_path


def load_entities(wiki_path: str) -> dict:
    """Load entity definitions from _aliases/entities.json."""
    path = os.path.join(wiki_path, "_aliases", "entities.json")
    if not os.path.exists(path):
        sys.stderr.write(f"⚠️  entities.json not found at {path}\n")
        return {}
    with open(path) as f:
        return json.load(f).get("entities", {})


def suggest_links(text: str, entities: dict) -> list[dict]:
    """Scan text for known entity aliases and return link suggestions.

    Returns list of dicts: matched, entity, wikilink, position.
    Already-wikilinked phrases (preceded by [[) are skipped.
    """
    suggestions = []
    for slug, info in entities.items():
        page = info["page"]
        primary = info["primary"]
        all_names = [primary] + info.get("aliases", [])
        for name in all_names:
            if len(name) < 2:
                continue
            for m in re.finditer(re.escape(name), text, re.IGNORECASE):
                # Avoid suggesting if already wikilinked
                start = max(0, m.start() - 2)
                if text[start : m.start()] == "[[":
                    continue
                suggestions.append(
                    {
                        "matched": m.group(),
                        "entity": primary,
                        "wikilink": f"[[{os.path.splitext(os.path.basename(page))[0]}]]",
                        "position": m.start(),
                    }
                )
    # Deduplicate by position, keep longest match
    by_pos: dict[int, dict] = {}
    for s in suggestions:
        pos = s["position"]
        if pos not in by_pos or len(s["matched"]) > len(by_pos[pos]["matched"]):
            by_pos[pos] = s
    return sorted(by_pos.values(), key=lambda x: x["position"])


def run(args):
    """Main entry point for 'entities' subcommand."""
    wiki_path = resolve_wiki_path(args.wiki_path)
    entities = load_entities(wiki_path)

    if not entities:
        print("⚠️  No entities loaded — is _aliases/entities.json present?")
        return 1

    # Support both: positional "text" and "-" for stdin
    if args.text == "-" or args.text is None:
        text = sys.stdin.read()
    else:
        text = args.text

    suggestions = suggest_links(text, entities)

    if suggestions:
        print(f"\n🔗 {len(suggestions)} entity link suggestions:\n")
        for s in suggestions:
            print(f'  "{s["matched"]}" → {s["wikilink"]}  ({s["entity"]})')
    else:
        print("✅ No entity linking opportunities found.")

    return 0


def add_subparser(subparsers):
    """Register 'entities' subcommand."""
    parser = subparsers.add_parser(
        "entities",
        help="Scan text for known entity aliases and suggest wikilinks",
        description=(
            "Reads _aliases/entities.json from the wiki and scans input text "
            'for known entity names. Use "-" to read from stdin.'
        ),
    )
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Text to scan, or '-' to read from stdin",
    )
    # --wiki-path is added by the parent wiki_op.py; no need to duplicate here
    parser.set_defaults(func=run)
