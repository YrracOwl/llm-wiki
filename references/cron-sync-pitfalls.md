# Cron 兜底同步 — 踩坑记录

## session_search FTS5 与中文查询

**现象**: `session_search` 对纯中文/Unicode 查询词可能返回 0 结果，即使内容匹配。

**根因**: FTS5 的分词器对 CJK 字符的处理与英文不同。英文单词天然空格分隔，FTS5 的 `unicode61` tokenizer 对中文缺乏内在分词能力。

**对策（优先级降序）**:
1. **用英文关键词替代**: 技术术语保持英文 (`skill`, `wiki`, `cron`, `pip install`, `gateway`)
2. **用 OR 扩宽召回**: `skill OR 技能 OR workflow` — 多语言冗余
3. **降级到 browse 模式**: 无参数 `session_search()` → 手动浏览最近会话
4. **用 session_id 直接 scroll**: 已知 session_id 时直接滚入，不走 FTS5

**适用场景**: cron 兜底同步的 Step 1a（扫描过去24h 对话找遗漏）

## session_search scroll 模式：around_message_id=1 陷阱

**现象**: `session_search(session_id="...", around_message_id=1)` 连续返回 `"around_message_id 1 not in session_id"` 错误。

**根因**: Message ID 是全局自增的，不按 session 重置。一个 session 的第一条消息可能是 ID 26309，而不是 1。传入 `1` 永远匹配不到任何消息。

**正确做法（优先级降序）**:
1. **先用 discovery 拿到真实 ID**: `session_search(query="关键词", limit=N)` → 从结果中获取 `match_message_id`，再用它 scroll
2. **从 browse 的 bookend 获取 ID**: `session_search()` 无参数 → `bookend_end[-1].id` 就是最后一条消息的 ID
3. **不用 around_message_id，直接 browse**: `session_search(session_id="...")` 不传 around_message_id → 返回该 session 在 browse 列表中的位置附近的结果

**2026-06-05 实测**: cron 安全网 scan 中连续 3 次传入 `around_message_id=1` 全部失败。正确方法是用 discovery query 找到 session 后直接用返回的 `match_message_id`。

## 已确认的 session DB 路径

`~/.hermes/sessions/sessions.db` — **不存在**。session_search 使用内部存储，不通过 SQLite 文件暴露。
直接 SQL 查询不可用，只能通过 session_search 工具访问。
