## Graph Wiki
The general workflow for operating a personal knowledge graph using LLMs.

## Layers

There are three layers:
**Raw sources** — your curated collection of source documents. Articles, papers, images, data files. These are immutable — the LLM reads from them but never modifies them. This is your source of truth.
**The wiki** — a directory of LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this layer entirely. It creates pages, updates them when new sources arrive, maintains cross-references, and keeps everything consistent. You read it; the LLM writes it.
**The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured, what the conventions are, and what workflows to follow when ingesting sources, answering questions, or maintaining the wiki. This is the key configuration file — it's what makes the LLM a disciplined wiki maintainer rather than a generic chatbot. You and the LLM co-evolve this over time as you figure out what works for your domain.

## Operations
Main worfklow split by human or LLM or both

**Ingest:** A new source file is upload to raw source layer
*AI:* Contingent on human uploading raw source file -- AI will either create new node(s)/relationship(s) or update node(s)/relationship(s) properties.
*Human:* Will upload raw source file and will be able to manually reference it in node or relationship properties.

**Query:** Running questions/queries against the wiki
*AI:* The AI will intake NLQs and answer them via traversing the graph and inspecting each node/relationship properties. It can also look at index.md for a starting node.
*Human:* The human will run Cypher queries to look at sections of the KG.

**Lint:** Check the health of the wiki and look for contradictions between pages, stale claims, orphan nodes, etc.
*AI:* Periodically, the LLM will run health checks on the KG.
*Human:* The human will manually add, prune, and modify both nodes and relationships.

## Indexing and Logging

Two special files help the LLM (and you) navigate the wiki as it grows. They serve different purposes:

**index.md** is content-oriented. It's a catalog of everything in the wiki — each page listed with a link, a one-line summary, and optionally metadata like date or source count. Organized by category (entities, concepts, sources, etc.). The LLM updates it on every ingest. When answering a query, the LLM reads the index first to find relevant pages, then drills into them. This works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure.

**log.md** is chronological. It's an append-only record of what happened and when — ingests, queries, lint passes. A useful tip: if each entry starts with a consistent prefix (e.g. `## [2026-04-02] ingest | Article Title`), the log becomes parseable with simple unix tools — `grep "^## \[" log.md | tail -5` gives you the last 5 entries. The log gives you a timeline of the wiki's evolution and helps the LLM understand what's been done recently.
