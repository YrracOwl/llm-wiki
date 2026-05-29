# Agent Memory Landscape (2026-05 Survey)

Research conducted for llm-wiki evolution planning. Covers five major approaches
to agent knowledge storage and memory, from lightweight to heavy.

> **Full analysis session:** 2026-05-25, archived in `concepts/ultra-long-context-paradox.md` (Chen Zhang) and the wiki evolution plan.

---

## Taxonomy: Lightweight → Heavy

```
文件系统       结构化图       向量记忆       全栈Agent OS
llm-wiki       Graphiti       Mem0           Letta
(Karpathy)     (Zep)          (Mem0 AI)      (MemGPT继任)
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

## 2. Graphiti (getzep/graphiti)

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

## 3. Mem0 (mem0ai/mem0, YC S24)

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

## 4. Letta (MemGPT successor, letta-ai/letta)

**Approach:** Full agent OS — memory blocks + tools + sub-agents + self-improvement.

**Memory model:**
- `human` block — user info
- `persona` block — agent personality
- Self-editing memory

**Relevance to us:** The memory-block separation is conceptually similar to our
entity/concept page split. Letta is too heavy to adopt directly, but the
multi-block retrieval pattern (fetch relevant blocks, not all) is worth emulating.

---

## 5. SkillOpt & "From Raw Experience to Skill Consumption" (2026-05, latest)

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

## 6. Cognitive Workspace (arxiv 2508.13171)

**Approach:** Emulates human working memory — metacognitive awareness + active planning
for what to keep in context. Goes beyond passive RAG.

**Three innovations:**
1. Dynamic memory allocation based on task demand
2. Metacognitive monitoring of what's been forgotten
3. Active retrieval planning before information is needed

**Relevance to us:** Our stale_check.py is a primitive form of metacognitive monitoring
("is this still true?"). Full Cognitive Workspace is aspirational.

---

## 7. Other Notable Systems

| System | Key Feature | Source |
|--------|------------|--------|
| **Supermemory** | 3 parallel search agents replace vector DB, 99% accuracy | LongMemEval SOTA |
| **Distilling Feedback → Memory-as-Tool** | Converts transient critiques into retrievable file-based guidelines | arxiv 2601.05960 |
| **Conditional Memory (Engram)** | O(1) lookup, separates knowledge from neural computation, 27B params | arxiv 2601.07372 |
| **Context Engineering** | Karpathy + Shopify CEO: shift from Prompt Eng to Context Eng | Weibo/industry |

---

## Adoption Priority for llm-wiki

| Priority | Feature | Borrowed From | Status |
|:---:|---------|--------------|:---:|
| ✅ | Time dimension (valid_from/until/status) | Graphiti | Done |
| ✅ | ADD-only + version snapshots | Mem0 | Done |
| ✅ | Entity linking + alias index | Mem0 | Done |
| ✅ | Skill-Wiki bridge | SkillOpt | Done |
| 🔜 | Provenance tracking (fact → session) | Graphiti | Planned |
| 🔜 | Multi-signal retrieval (grep + semantic) | Mem0 | Planned |
| 🔮 | Skill quality feedback loop | SkillOpt | Backlog |
| 🔮 | Metacognitive staleness monitoring | Cognitive Workspace | Backlog |
