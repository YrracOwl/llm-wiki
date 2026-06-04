# Pitfall: `wiki_op.py update --content-file` is full replacement

> Hit 2026-06-01 while updating `concepts/hermes-dreaming.md` with v1.1.0 content.

## The misunderstanding

The skill docs say:

```
# 大改：完整内容文件（有无 frontmatter 均可——脚本自动合并旧元数据）
wiki_op.py update --page concepts/X --content-file /tmp/draft.md
```

"完整内容文件" means **the file must contain ALL sections you want on the page** — old + new merged. It does NOT append to the existing page; it **replaces the entire body**.

## What happens if you only write new sections

1. `wiki_op.py` saves a snapshot of the current page to `_versions/{slug}/{timestamp}.md` ✅
2. It writes ONLY your new sections as the page body ❌
3. All original content (architecture, scoring, cron, etc.) is gone

## Recovery

```bash
# 1. Find the snapshot
ls ~/wiki/_versions/{slug}/

# 2. Read the snapshot, merge with your new content, write a complete file
# 3. Re-run update with the merged file
python3 ~/wiki/.hermes/scripts/wiki_op.py update \
  --page concepts/X --content-file /tmp/merged.md \
  --change-summary "v1.1.0: restore full content + new section"
```

## Correct usage

When using `--content-file`, always **merge old + new content first**, then write the complete file. The snapshot is your safety net but not your recovery — you must manually read the snapshot and reconstruct.

## Deadlier variant: `--content-file /dev/null`

> Hit 2026-05-31 (hermes-dreaming restore test) and again 2026-06-01 (skill-design-guide broken link fix).

Passing `/dev/null` as `--content-file` feeds an **empty body** to wiki_op.py. Since `--content-file` is full replacement (not append), the result is a page with only frontmatter + history — **all body content wiped to zero bytes**.

```bash
# 🚨 NEVER do this:
python3 ~/wiki/.hermes/scripts/wiki_op.py update \
  --page concepts/X --content-file /dev/null \
  --change-summary "minor fix"
# Result: page body = empty. Only frontmatter + history record survives.
```

This is trivially easy to do when the actual content change was already applied manually (outside wiki_op.py) and you just want wiki_op.py to record the snapshot + log. **wiki_op.py `update` always applies a change; it has no "record-only" mode.** If the change is already applied in the file, use a no-op patch:

```json
{"old": "an-existing-unique-line", "new": "an-existing-unique-line"}
```

Recovery is the same as the standard case — snapshot restore — but the zero-byte wipe can be more psychologically jarring.

### Root causes (2026-06-01 incident)

1. **No content-size guard**: wiki_op.py accepts any non-empty file, including `/dev/null` (0 bytes). Should reject files below a threshold (e.g. 50 bytes, since a valid page body is at minimum a heading + one sentence).
2. **Mode ambiguity**: `--content-file` and `--patch-file` have fundamentally different semantics (full-replace vs surgical-replace), but this is only documented in prose — the CLI doesn't enforce or warn. An agent under time pressure who just wants to "record a change that already happened" may reach for `--content-file /dev/null` as the shortest path, not realizing it's the nuclear option.
\n\n## `--patch-file` is safer for small changes

For adding a single section or fixing a typo, prefer `--patch-file`:

```json
{"old": "## 评分权重", "new": "## 评分权重 (v1.1 调整)\n\n新增 dedup 锚点扩展...\n\n## 评分权重"}
```

This replaces only the matched string, leaving everything else intact.
