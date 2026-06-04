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

## 已确认的 session DB 路径

`~/.hermes/sessions/sessions.db` — **不存在**。session_search 使用内部存储，不通过 SQLite 文件暴露。
直接 SQL 查询不可用，只能通过 session_search 工具访问。
