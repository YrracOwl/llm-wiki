# Cron Session Scanning Pattern

Reliable pattern for discovery when `session_search(query=...)` returns 0 results
for a broad topic search.

## The Problem

`session_search(query=...)` with broad keyword sets (e.g., "wiki skill config knowledge")
sometimes returns 0 results even when relevant sessions exist. This happens because
FTS5 requires exact token matches and the query may be too broad or not match the
specific language used in the session.

## The Reliable Pattern

```
Step 1: BROWSE — session_search() with NO query
  → Returns most recent 10 sessions chronologically
  → Review titles and previews to identify candidates

Step 2: DISCOVER — session_search(query="specific terms from candidate")
  → Use distinctive terms from the session title
  → E.g., "specs-as-code" not "skill wiki config"
  → This gets you the match_message_id for scrolling

Step 3: SCROLL — session_search(session_id=..., around_message_id=match_message_id)
  → Read the actual content around the match
  → Scroll forward/backward as needed

Step 4: If DISCOVER still returns nothing:
  → session_search(limit=0)  [browse mode]
  → Scroll via bookend_end message IDs directly
```

## Anti-patterns

- ❌ Starting with `session_search(query="broad keyword soup")` — FTS5 penalizes broad queries
- ❌ Using `around_message_id=1` — message IDs are globally auto-incremented, not reset per session
- ❌ Trying `session_search(limit=5, query=...)` before trying browse mode

## 2026-06-08 Example

Browse returned 10 sessions. Candidate "Engineering Specs-as-Code and Code-as-Specs" (97 msgs) was identified.
Discovery with `query="specs-as-code code-as-specs engineering"` returned 1 match.
Scroll with the returned `match_message_id` revealed a full Design Grill worth archiving.
