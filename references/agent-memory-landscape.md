# Agent Memory Landscape (2026-06 Survey)

Research conducted for llm-wiki evolution planning. Covers eight major approaches
to agent knowledge storage and memory, from lightweight to heavy.

> **Full analysis session:** 2026-05-25, archived in `concepts/ultra-long-context-paradox.md` (Chen Zhang) and the wiki evolution plan.
> **2026-06-06 update:** Added agentmemory (Karpathy LLM Wiki v2 工程实现) — detailed comparison with llm-wiki in session 2026-06-06.

---

## Taxonomy: Lightweight → Heavy

```
文件系统               运行时引擎          结构化图       向量记忆       全栈Agent OS
llm-wiki               agentmemory         Graphiti       Mem0           Letta
(Karpathy)             (Karpathy v2)       (Zep)          (Mem0 AI)      (MemGPT继任)
```

---

## 1. Karpathy LLM Wiki (Baseline — we use this)

**Approach:** Markdown files + LLM as compiler. 5K+ GitHub stars, 15+ independent
implementations. Called "a potential vector-DB replacement" by the Chinese AI community.

**Strengths:**
- Zero dependencies, human-readable
- `[[wikilinks]]` for cross-referencing
- Obsidian compatible (Graph View, Dataview)
- LLM semantic compilation > keyword matching

**Limitations (addressed by our upgrades):**
- No time dimension (→ added `valid_from/valid_until/status`)
- No entity linking (→ added `entities.json` + `entity_link.py`)
- No version history (→ added `version_history.py` + ADD-only)
- No skill bridge (→ added `skill_wiki_bridge.py` + `_mapping.md`)

---

## 2. agentmemory (rohitg00/agentmemory, Karpathy LLM Wiki v2 工程实现)

**Stars:** 5,000-9,000+ (2026年4-6月快速增长) | **npm:** `@agentmemory/agentmemory`
**Self-claimed:** "#1 Persistent memory for AI coding agents"

**Core innovation:** 把 Karpathy 的 LLM Wiki pattern 做成**运行时守护进程 + MCP 服务器**，
而非文件约定。设计和我们的 llm-wiki 同根（同一篇 gist），但走了完全不同的架构路径。

| Feature | Detail |
|---------|--------|
| Runtime | Node.js + iii-engine (Rust actor runtime, ~38K LOC) |
| Memory tiers | 4-tier consolidation: Working → Episodic → Semantic → Procedural |
| Auto-capture | 12 lifecycle hooks (PostToolUse, SessionStart, PreCompact, etc.) |
| Search | BM25 + vector + knowledge graph, RRF fusion (k=60) |
| Retrieval | **LongMemEval-S R@5 = 95.2%** (ICLR 2025 基准) |
| Knowledge graph | Typed edges (uses/depends/contradicts/caused/fixed) |
| Lifecycle | Confidence scoring + Ebbinghaus decay + auto-forget + contradiction resolution |
| Multi-agent | Lease (exclusive action lock) + signal (inter-agent messaging) + team namespacing |
| Token cost | ~1,900 tokens/session (~$10/yr with local embeddings) |
| MCP surface | 53 tools, 6 resources, 3 prompts, 8 skills |
| Dependencies | Node.js + iii-engine binary (no external DB — SQLite + iii KV State) |
| Hermes integration | 已有官方 plugin (`integrations/hermes/`) — 6-hook memory provider + `memory.provider: agentmemory` |

**与 llm-wiki 的对比 (session 2026-06-06 详细分析):**

| 维度 | llm-wiki (我们) | agentmemory |
|------|----------------|-------------|
| 范式 | 文件约定 + shell 脚本 | 守护进程 + MCP 服务器 |
| 人类可读性 | ⭐ Obsidian 开箱即用 | Web viewer (port 3113) |
| 搜索 | grep + index + wikilinks | BM25 + vector + graph (RRF) |
| 捕获 | 手动 (Agent 主动调 ingest) | 自动 (12 hooks) |
| 记忆固化 | Source → wiki page (一次到位) | 4-tier 渐进管道 |
| 领域 | 通用 (投资/IC/摄影/文学) | 编码 Agent 会话记忆 |
| 部署 | 零依赖 | Node.js + iii-engine |
| 知识结构 | 无类型 wikilinks | 类型化知识图谱 |

**Relevance to us:** agentmemory 代表了同一基因的另一种演化方向——从文件约定走向运行时引擎。
它证明了三件事：① 混合搜索 (BM25+vector+graph) 对大规模 wiki 是刚需（index.md 超过 100 页就失效）；
② 置信度评分让 Agent 能区分「确定」和「猜测」；③ 4-tier 固化管道比一次性写入更接近人类记忆模型。
我们应该吸收这些设计理念（优先：混合搜索、置信度评分），但不一定需要 iii-engine 的运维复杂度。

---

## 3. Graphiti (getzep/graphiti)

**Paper:** [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
**Self-claimed:** "State of the Art in Agent Memory"

**Core innovation:** Temporal Context Graph — entities + relationships + time windows + provenance.

| Feature | Detail |
|---------|--------|
| Time windows | Every fact records when it became/was true |
| Provenance | Every fact traces back to raw data (Episode) |
| Hybrid retrieval | Semantic + keyword + graph traversal |
| Incremental | Append new facts, no full recompute |
| MCP support | MCP Server available for Claude/Cursor |

**Relevance to us:** The time-dimension addition (valid_from/valid_until) is directly inspired
by Graphiti's temporal tracking. Next step: add provenance tracking (link facts back to session dates).

---

## 4. Mem0 (mem0ai/mem0, YC S24)

**Core innovation:** Multi-level memory + ADD-only extraction + entity linking.

**Benchmarks (April 2026):**
| Benchmark | Score |
|-----------|------:|
| LoCoMo | 91.6 |
| LongMemEval | 94.8 |
| BEAM (1M tokens) | 64.1 |

**Key design choices:**
- **ADD-only**: One LLM call extracts memories, never overwrites. Memories accumulate.
- **Entity linking**: Entities extracted, embedded, linked across memories.
- **Multi-signal retrieval**: Semantic + BM25 keyword + entity matching, fused.
- **Temporal reasoning**: Distinguishes "current state" vs "past event" vs "future plan".

**Relevance to us:** Our ADD-only protocol and entity linking (`entities.json`) are directly
inspired by Mem0. Mem0 goes further with vector embeddings + multi-signal retrieval,
which we approximate with `search_files` (grep) + entity_link.py (regex).

---

## 5. Letta (MemGPT successor, letta-ai/letta)

**Approach:** Full agent OS — memory blocks + tools + sub-agents + self-improvement.

**Memory model:**
- `human` block — user info
- `persona` block — agent personality
- Self-editing memory

**Relevance to us:** The memory-block separation is conceptually similar to our
entity/concept page split. Letta is too heavy to adopt directly, but the
multi-block retrieval pattern (fetch relevant blocks, not all) is worth emulating.

---

## 6. SkillOpt & "From Raw Experience to Skill Consumption" (2026-05, latest)

**Papers:**
- SkillOpt (2605.23904): First systematic text-space optimizer for agent skills
- Raw Experience (2605.23899): Full skill lifecycle study across 5 domains

**Key findings:**
- Model-generated skills are beneficial on average but exhibit negative transfer
- Strong extractor ≠ strong consumer — skill utility independent of model size
- Skill should be trained like neural network weights — iterative optimization via validation feedback

**Relevance to us:** Our Skill-Wiki bridge is the first step toward skill evolution.
Next: implement a feedback loop where cron tasks evaluate skill quality and flag
degrading skills for regeneration.

---

## 7. Cognitive Workspace (arxiv 2508.13171)

**Approach:** Emulates human working memory — metacognitive awareness + active planning
for what to keep in context. Goes beyond passive RAG.

**Three innovations:**
1. Dynamic memory allocation based on task demand
2. Metacognitive monitoring of what's been forgotten
3. Active retrieval planning before information is needed

**Relevance to us:** Our stale_check.py is a primitive form of metacognitive monitoring
("is this still true?"). Full Cognitive Workspace is aspirational.

---

## 9. Other Notable Systems

| System | Key Feature | Source |
|--------|------------|--------|
| **Supermemory** | 3 parallel search agents replace vector DB, 99% accuracy | LongMemEval SOTA |
| **Distilling Feedback → Memory-as-Tool** | Converts transient critiques into retrievable file-based guidelines | arxiv 2601.05960 |
| **Conditional Memory (Engram)** | O(1) lookup, separates knowledge from neural computation, 27B params | arxiv 2601.07372 |
| **Context Engineering** | Karpathy + Shopify CEO: shift from Prompt Eng to Context Eng | Weibo/industry |

---

## 8. agentmemory (rohitg00/agentmemory, ~9K stars)

**Approach:** Persistent memory engine for AI coding agents — a runtime daemon + MCP server built on iii-engine.

**Core innovations:**
- 12 lifecycle hooks auto-capture every tool use, session start/stop, and compaction event
- 4-tier memory consolidation (Working → Episodic → Semantic → Procedural) with automatic promotion
- Hybrid search: BM25 + vector + knowledge graph with Reciprocal Rank Fusion (RRF, k=60)
- Confidence scoring + Ebbinghaus decay curve — frequently accessed memories strengthen, stale ones auto-evict
- Typed knowledge graph: entities + attributes + semantic edges (uses, depends on, contradicts, caused, fixed)
- 53 MCP tools + 6 resources + 8 skills — cross-agent shared memory (Claude Code, Codex, Copilot, Cursor, Hermes, etc.)
- Zero external DB deps (SQLite + in-memory KV via iii-state)

**Benchmarks:** LongMemEval-S R@5 = 95.2%, MRR = 88.2% (ICLR 2025)

**Relevance to us:** Extends Karpathy's LLM Wiki v2 — the same root as our llm-wiki. Key borrowable ideas:
1. Hybrid search (BM25 + vector + graph) — we currently use grep + index.md
2. Confidence scoring — we treat all wiki entries equally
3. 4-tier promotion pipeline — we do one-step source→page
4. Typed knowledge graph edges — our wikilinks are untyped
5. Ebbinghaus decay — our stale_check uses fixed expiry only

**Decision:** Runtime engine (daemon + Node.js + iii-engine) is too heavy to adopt directly. Absorb design ideas (hybrid search, confidence scoring) into llm-wiki rather than introducing the full stack. See [[llm-wiki-vs-agentmemory]] for full comparison.

---

## Adoption Priority for llm-wiki

| Priority | Feature | Borrowed From | Status |
|:---:|---------|--------------|:---:|
| ✅ | Time dimension (valid_from/until/status) | Graphiti | Done |
| ✅ | ADD-only + version snapshots | Mem0 | Done |
| ✅ | Entity linking + alias index | Mem0 | Done |
| ✅ | Skill-Wiki bridge | SkillOpt | Done |
| 🔜 | Hybrid search (BM25 + vector + graph) | agentmemory, Mem0 | Planned |
| 🔜 | Confidence scoring + Ebbinghaus decay | agentmemory | Planned |
| 🔜 | Hybrid search (BM25 + vector + graph RRF) | agentmemory | Planned |
| 🔜 | Confidence scoring + Ebbinghaus decay | agentmemory | Planned |
| 🔜 | 4-tier memory consolidation pipeline | agentmemory | Planned |
| 🔜 | Type-sysed knowledge graph edges | agentmemory | Planned |
| 🔜 | Provenance tracking (fact → session) | Graphiti | Planned |
| 🔜 | Multi-signal retrieval (grep + semantic) | Mem0 | Planned |
| 🔮 | Skill quality feedback loop | SkillOpt | Backlog |
| 🔮 | Metacognitive staleness monitoring | Cognitive Workspace | Backlog |
