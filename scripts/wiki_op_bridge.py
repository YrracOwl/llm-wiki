#!/usr/bin/env python3
"""Bridge subcommand: scan a skill for wiki references and knowledge extraction opportunities.

Invoked via: wiki_op bridge <skill_path> [--wiki-path PATH]
"""
import os
import re
import argparse

from wiki_path import resolve_wiki_path

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")


def find_wiki_refs(text):
    """Find [[wikilinks]] in text."""
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def find_knowledge_nuggets(text):
    """Find sections likely containing extractable knowledge."""
    nuggets = []
    pitfalls = re.findall(r"(?:## .*[Pp]itfalls?.*\n)((?:\s*- .+\n?)+)", text)
    for p in pitfalls:
        nuggets.append(("pitfall", p[:500]))
    key_sections = re.findall(
        r"(?:## .*(?:核心|关键|Key|核心理念).*\n)((?:\s*.+\n?){1,5})", text
    )
    for ks in key_sections:
        nuggets.append(("key_point", ks[:500]))
    return nuggets


def run(args):
    """Main entry point for the 'bridge' subcommand."""
    wiki_path = resolve_wiki_path(args.wiki_path)

    with open(args.skill_path) as f:
        content = f.read()

    rel = os.path.relpath(args.skill_path, SKILLS_DIR)
    skill_name = os.path.basename(os.path.dirname(args.skill_path))

    print(f"📋 Skill: {skill_name} ({rel})")

    refs = find_wiki_refs(content)
    if refs:
        print(f"\n🔗 引用的 Wiki 页面 ({len(set(refs))}):")
        for r in sorted(set(refs)):
            print(f"  • [[{r}]]")

    nuggets = find_knowledge_nuggets(content)
    if nuggets:
        print(f"\n💡 可提取知识点 ({len(nuggets)}):")
        for ntype, text in nuggets:
            preview = text.strip()[:100].replace("\n", " ")
            print(f"  [{ntype}] {preview}...")

    mapping_file = os.path.join(wiki_path, "skills/_mapping.md")
    if os.path.exists(mapping_file):
        with open(mapping_file) as f:
            mapping = f.read()
        if skill_name not in mapping:
            print(f"\n⚠️  {skill_name} 未在 _mapping.md 中注册")


def add_subparser(subparsers):
    """Register the 'bridge' subcommand with a positional skill_path argument."""
    parser = subparsers.add_parser(
        "bridge",
        help="Scan a skill's SKILL.md for wiki references and extractable knowledge",
    )
    parser.add_argument(
        "skill_path",
        help="Path to SKILL.md (or directory containing it)",
    )
    parser.set_defaults(func=run)
    return parser


# Legacy CLI: direct execution without argparse (e.g. python wiki_op_bridge.py <path>)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: wiki_op_bridge.py <path/to/SKILL.md> [--wiki-path PATH]")
        sys.exit(1)

    # Simple arg parsing for legacy direct-call compatibility
    skill_path = sys.argv[1]
    wiki_path_arg = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--wiki-path":
        wiki_path_arg = sys.argv[3]

    class Args:
        pass

    args = Args()
    args.skill_path = skill_path
    args.wiki_path = wiki_path_arg
    run(args)
