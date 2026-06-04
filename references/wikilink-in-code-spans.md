# Wikilink in Backtick Code Spans — Zero-Width Space Trick

## Problem

`skill_wiki_bridge.py` uses a simple regex `\[\[([^\]]+)\]\]` to find wikilinks.
It does NOT skip backtick-quoted inline code spans. This means:

```markdown
- `[[hermes-systems]]`  ← bridge script treats this as a real wikilink!
```

gets reported as a false positive in the daily sync report.

## Solution: Zero-Width Space (U+200B)

Insert a zero-width space character between the brackets. Human eyes see `[[slug]]`; the regex sees `[​[slug]​]` and does NOT match.

### Python example

```python
zwsp = "\u200b"  # zero-width space

# Before: gets matched by skill_wiki_bridge.py regex
f"> 📚 Wiki: [[{slug}]]"

# After: visually identical, no regex match
f"> 📚 Wiki: [{zwsp}[{slug}]{zwsp}]"
```

### Manual insertion

Copy this character between brackets: `​` (between the arrows: →​← — you won't see it, but it's there). Paste it between `[` and `[` and between `]` and `]`.

### When to use

Only when you NEED to display `[[` `]]` wikilink syntax inside a backtick code span in SKILL.md. Prefer describing the format with plain text instead.

### Plain text alternative (preferred for wiki pages)

For wiki page content (as opposed to SKILL.md), the simplest fix for a broken-wikilink false positive is to **remove the wikilink brackets** and describe the link in plain text:

```markdown
# Before — broken link false positive
- ❌ `[[you/hermes-systems]]` → ✅ bare slug

# After — plain text, no false positive
- ❌ 子目录前缀写法（如 `you/hermes-systems`）→ ✅ bare slug
```

This works because `wiki_op.py`'s wikilink detector (unlike `skill_wiki_bridge.py`) strips inline code spans before scanning, and even if it didn't, plain text has no `[[` `]]` to match. Zero-width space is only needed when the content MUST display the wikilink brackets (e.g., in SKILL.md for skill_wiki_bridge.py scans).

### Caveats

- Works in terminals and most markdown renderers (ZWS is invisible)
- May not survive copy-paste between some applications
- Not needed outside SKILL.md — only matters for `skill_wiki_bridge.py` scans
