# Wiki Templates & Setup

> Moved from SKILL.md (v2.3.2) to keep the main skill under attention budget.
> Loaded on-demand during wiki initialization or Obsidian setup.

---

## SCHEMA.md Template

Adapt to the user's domain. The schema constrains agent behavior and ensures consistency:

```markdown
# Wiki Schema

## Domain
三层知识库 — 「你 (Agent)」「我 (User)」「世界 (World)」：

- **你 (Agent)**：本机 Hermes Agent 的环境配置、工具链、技能使用经验、踩过的坑
- **我 (User)**：用户的身份、偏好、兴趣、行事风格、已掌握的知识、个人项目
- **世界 (World)**：通过 Agent 研究获得的一切知识——技术调研、投资分析、学术文献、工程笔记、市场情报

原则：任何在对话中产生的、值得留存的知识都可以入 Wiki。不复述"Agent 做了什么"，而是提炼"我们知道了什么"。

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `wyckoff-analysis.md`) or for 世界层 technical topics: `adclk954-broadband-jitter.md`
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- 语言：中文为主，技术术语保留英文
- 页面归属标注：在正文开头用一句「归属：你/我/世界」标注该页面主要属于哪一层（跨层页面可并列）

## Frontmatter
  ```yaml
  ---
  title: Page Title
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | query | summary
  tags: [from taxonomy below]
  sources: [raw/articles/source-name.md]
  ---
  ```

## Tag Taxonomy
- **环境与配置**: server, config, network, proxy, mirror
- **工具与技能**: skill, tool, cli, automation
- **数据与API**: data-source, api, stock, news
- **方法论**: theory, workflow, strategy, analysis
- **经验与坑**: pitfall, workaround, lesson, memory
- **平台**: qqbot, telegram, discord, xiaohongshu, steam, weibo, github
- **投资**: wyckoff, sentiment, a-stock, technical-analysis
- **内容**: mao, poetry, literature, classic
- **工程**: electronics, datasheet, semiconductor, signal-processing, measurement

## Page Thresholds
- **你 (Agent) 层**：当工具/技能/配置在 2+ 会话中出现或是一个主要工作流的核心 → 建页面
- **我 (User) 层**：当用户的偏好/身份/项目被明确讨论并形成可复用知识 → 建页面
- **世界 (World) 层**：当 Agent 完成一次有深度的技术调研、投资分析或学术查询，且结果值得复用 → 建页面
- **Add to existing page** when new info relates to an already-covered topic
- **DON'T create a page** for passing mentions, trivia, or things outside the domain
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages
One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

## Concept Pages
One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

## Comparison Pages
Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report
```

---

## index.md Template

The index is sectioned by type. Each entry is one line: wikilink + summary.

```markdown
# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: YYYY-MM-DD | Total pages: N

## Entities
<!-- Alphabetical within section -->

## Concepts

## Comparisons

## Queries
```

**Scaling rule:** When any section exceeds 50 entries, split it into sub-sections
by first letter or sub-domain. When the index exceeds 200 entries total, create
a `_meta/topic-map.md` that groups pages by theme for faster navigation.

---

## log.md Template

```markdown
# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [YYYY-MM-DD] create | Wiki initialized
- Domain: [domain]
- Structure created with SCHEMA.md, index.md, log.md
```

---

## Obsidian Integration

The wiki directory works as an Obsidian vault out of the box:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries
- The `raw/assets/` folder holds images referenced via `![[image.png]]`

For best results:
- Set Obsidian's attachment folder to `raw/assets/`
- Enable "Wikilinks" in Obsidian settings (usually on by default)
- Install Dataview plugin for queries like `TABLE tags FROM "entities" WHERE contains(tags, "company")`

If using the Obsidian skill alongside this one, set `OBSIDIAN_VAULT_PATH` to the
same directory as the wiki path.

## Obsidian Headless (servers and headless machines)

On machines without a display, use `obsidian-headless` instead of the desktop app.
It syncs vaults via Obsidian Sync without a GUI — perfect for agents running on
servers that write to the wiki while Obsidian desktop reads it on another device.

**Setup:**
```bash
# Requires Node.js 22+
npm install -g obsidian-headless

# Login (requires Obsidian account with Sync subscription)
ob login --email <email> --password '<password>'

# Create a remote vault for the wiki
ob sync-create-remote --name "LLM Wiki"

# Connect the wiki directory to the vault
cd ~/wiki
ob sync-setup --vault "<vault-id>"

# Initial sync
ob sync

# Continuous sync (foreground — use systemd for background)
ob sync --continuous
```

**Continuous background sync via systemd:**
```ini
# ~/.config/systemd/user/obsidian-wiki-sync.service
[Unit]
Description=Obsidian LLM Wiki Sync
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/path/to/ob sync --continuous
WorkingDirectory=/home/user/wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now obsidian-wiki-sync
# Enable linger so sync survives logout:
sudo loginctl enable-linger $USER
```

This lets the agent write to `~/wiki` on a server while you browse the same
vault in Obsidian on your laptop/phone — changes appear within seconds.
