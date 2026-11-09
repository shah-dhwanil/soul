# Architecture Design Document: Conversational Companion Agent (MVP)

Version 1.0 | November 8, 2026 | Status: Draft for review

## 1. Purpose and Scope

This document describes the architecture of an MVP AI agent that behaves like a close friend the user can talk things through with. It consolidates the original design notes with the bottlenecks and improvements identified during design review.

**Goals**

- Fast, warm replies that feel conversational rather than robotic.
- Durable memory of people, events, dates and preferences across threads.
- A consistent persona that adapts slowly over time.
- Safe handling of emotional distress and crisis messages.

**Non-goals for the MVP:** voice, shared multi-user graphs, proactive outbound messaging.

## 2. Technology Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Orchestration | LangGraph | Postgres checkpointer for thread state |
| Decision model | Jev (TypeSafe AI) | Returns typed decisions with probabilities; cannot generate text |
| LLM inference | Groq | Fast model for replies and query generation; larger model to be evaluated for ingestion |
| Graph memory | Graphiti on Neo4j 5.26+ | Temporal knowledge graph; one `group_id` per user |
| Relational store | PostgreSQL | Raw chats, threads, checkpoints, ingestion status, persona versions |
| Embeddings | Separate provider | Groq does not offer embeddings |
| Queue | Durable queue (Postgres-backed or Redis) | Feeds the ingestion worker |

## 3. System Overview

The system has two paths. The **request path** is synchronous and must feel instant. The **ingestion path** is asynchronous and builds long-term memory in the background.

### 3.1 Request path

1. User message arrives; the last few turns are loaded from Postgres.
2. In parallel: (a) Jev classifies the message, (b) a small Groq LLM writes memory queries, (c) NER and entity matching extract known names, (d) the raw message is kept as a fallback query.
3. Based on Jev's output, the thread is continued or a new one is created.
4. If memory is needed, queries run in parallel against Graphiti and results are merged and deduplicated.
5. The agent prompt is assembled: persona, core profile, retrieved memories, tone hint, thread summary and recent turns.
6. The agent generates the reply. A single `search_memory` tool is available as a fallback.
7. The reply is streamed to the user and stored in Postgres.

### 3.2 Ingestion path

1. A trigger fires (new thread created, inactivity timeout, or every N turns).
2. A signal builds a log of the relevant chat and adds it to the queue for Graphiti memory ingestion and persona updating.
3. A background worker ingests the episode into Graphiti, serialized per user.
4. The persona update job runs in batches and writes a new persona version.
5. Ingestion status is recorded in Postgres so failures can be retried or replayed.

## 4. Request Path in Detail

### 4.1 Decision layer (Jev)

Jev answers many questions about the same input in a single parallel pass, returning a probability for each option. One call covers all of the following:

- **Thread decision:** continue the current thread or start a new one. Continue when past chat matters; start new when it does not.
- **User intent:** for example venting, seeking advice, sharing news, casual chat.
- **User emotion:** for example sad, anxious, frustrated, happy, neutral.
- **needs\_memory:** whether memory retrieval is worthwhile (low for messages such as thanks or good morning).
- **Distress flag:** high-recall check for self-harm or acute distress.
- **Target tone:** the tone the reply should take, passed to the agent as a hint before generation.

**Using the probabilities**

- Apply thresholds rather than hard labels. Default to continuing the thread unless the new-thread probability is clearly high (for example above 0.8). Wrongly splitting a thread loses context; wrongly continuing costs little.
- Log every decision and its confidence to tune thresholds with real data.
- Escalate borderline cases (for example uncertain emotion or distress) to a Groq LLM for a second opinion.

**Known limits.** Jev is fast and cheap but cannot write text or reason over multiple steps, and its accuracy varies by task. Fuzzy judgments such as whether past chat matters must be validated on real messy conversations before launch.

### 4.2 Memory query generation

Raw user messages make poor search queries because they contain filler, pronouns and unrelated detail. Queries are therefore generated from several sources and merged:

| Source | Strength | Weakness |
| --- | --- | --- |
| Small Groq LLM (1 to 3 short, entity-focused queries) | Handles context and pronouns | Can invent names |
| NER (spaCy or GLiNER) matched against Neo4j Person and Event nodes, including aliases | Fast and deterministic | Weak on vague messages with no named entity |
| Raw message | Cheap safety net | Noisy |

The query LLM receives the last 2 to 3 turns so it can resolve references such as she to Riya. It runs in parallel with Jev, and its output is discarded if Jev reports that memory is not needed. Because Jev cannot generate text, this separate call is required.

### 4.3 Memory retrieval and injection

- **Always inject a core profile:** user name, key people, ongoing situations and strong preferences, so the agent never forgets the basics.
- **Pre-fetch on every message** rather than relying on the agent to decide to search. This removes extra LLM round trips from the reply path.
- **Internal typed lookups** such as person, event and preference lookups are retained as internal functions. The pre-fetch step calls them directly and in parallel, avoiding any tool-selection errors by the agent.
- Retrieved facts are formatted compactly, for example: Sister Riya, strained lately. Exam on Friday. Likes chai.

### 4.4 Agent and tools

The agent receives the persona, core profile, retrieved memories, tone hint, thread summary and recent turns. Its tool list is intentionally small:

- `search_memory(query, entity_type?, as_of?)`: fallback deep search over Graphiti. The model can call it several times in parallel in one turn. Date questions such as last March use `as_of` or a time filter, so a separate date-detail tool is not needed.
- `get_previous_chat(thread_id, chat_id_end, no_of_chat)`: returns a window of earlier chat from Postgres when exact wording is needed.

Tool-selection errors should be measured early. If testing shows the model reliably handles separate typed tools, they can be exposed individually.

### 4.5 Thread and context management

- Context memory uses a sliding window of the last N raw turns plus a rolling summary of content that has moved out of the window.
- Thread state is stored with the LangGraph Postgres checkpointer.
- The summary is updated asynchronously, never inside the request path.

## 5. Memory Model

### 5.1 Graph ontology (Graphiti)

Specialized node types are used for structured knowledge. Everything else is stored as normal memory (episodes and extracted facts).

| Type | Kind | Purpose |
| --- | --- | --- |
| Person | Node | People in the user's life, with aliases (Mom, Mama, Sunita resolve to one node) |
| Event | Node | Things that happened or will happen (exam, trip, argument) |
| Date | Node | Temporal anchors, supported by Graphiti's temporal edges |
| Preference | Node | Likes, dislikes, habits, with as-of history |
| Relationship | Edge (added) | User to person, with quality and recent state, for example sister, strained lately |
| Goal / Topic | Node (optional, added) | Ongoing concerns and aspirations |

**Guidelines**

- Give every custom type a clear docstring and field descriptions. Extraction quality depends heavily on these, especially with smaller models.
- Set `group_id` to the user ID so each user's graph is isolated.
- Entity resolution is a top risk. Maintain an alias list and test that variants of a name map to a single node.

### 5.2 PostgreSQL

Postgres is the source of truth for raw data:

- Raw chats and threads, each with an ingestion status or `ingested_at` field.
- LangGraph checkpoints.
- Rolling thread summaries.
- Versioned persona records.
- Jev decision logs with confidence scores.

Because raw chats are retained, the graph can be rebuilt from scratch after a failure or an ontology change.

## 6. Ingestion Pipeline

**Triggers.** The original design triggers ingestion when a new thread is created. This leaves a gap: if a user never starts a new thread, nothing is remembered. Ingestion also fires on an inactivity timeout (for example 30 minutes) and every N turns.

**Signal.** On each trigger a signal builds a log of the chat and adds it to the queue for Graphiti memory ingestion and persona updating.

**Worker rules**

- Run in the background, never in the request path. Each episode makes several LLM calls (entity extraction, deduplication, edge extraction, summaries).
- Serialize ingestion per user, using one queue partition or lock per user. Concurrent episodes for one user can create duplicate entities.
- Use a durable queue so a crash does not drop episodes.
- Record status per chat and retry safely; replay from Postgres when needed.
- Test the chosen Groq model early for reliable structured output. Graphiti needs valid JSON schemas, and smaller models sometimes break them. Consider a larger model for ingestion and a faster one for chat.

**Operations.** Graphiti requires Neo4j 5.26 or later and creates its own indices. Monitor memory if self-hosting; AuraDB's free tier suits the MVP but is small.

## 7. Persona System

- **Fixed core persona:** voice, values and boundaries that never change automatically.
- **Adaptive layer:** slowly changing traits such as humor level and favorite topics, learned from conversations.
- Updates run in batches from the ingestion signal and are versioned, so drift can be reviewed and rolled back.
- Guard against sycophancy: a friend should be supportive without simply agreeing with everything.

## 8. Safety

- A dedicated high-recall distress check runs on every message and bypasses the cheap decision path. Its threshold is low, and borderline scores escalate to an LLM.
- When distress is detected, the agent shifts to a calm, supportive response and encourages reaching out to trusted people or appropriate crisis services.
- Sycophancy and over-validation of harmful beliefs are tested for explicitly.
- Plan for privacy: users can request deletion, which removes their `group_id` graph and Postgres records.

## 9. Latency Budget (estimates, to be measured)

| Stage | Approx. time | Notes |
| --- | --- | --- |
| Jev + query LLM + NER | 250 to 300 ms | Run in parallel |
| Graphiti hybrid search | 100 to 300 ms | Parallel queries |
| Agent first token | 300 to 600 ms | Groq streaming |
| Total to first token | roughly 0.7 to 1.2 s | One LLM call in the reply path |

The original design chained decision, emotion classification, agent and tool calls serially, adding 3 to 5 round trips. Parallelization and pre-fetching remove most of these.

## 10. Bottlenecks and Mitigations

| Bottleneck | Risk | Mitigation |
| --- | --- | --- |
| Serial model calls | Robotic, slow replies | Merge classifications into one Jev call; run alongside retrieval |
| Agent-called graph tools | Extra LLM hops per turn | Pre-fetch; keep one fallback tool |
| Ingestion only on new thread | Memory never forms | Add inactivity and every-N-turn triggers |
| Graphiti ingestion cost | Slow, failing jobs | Background worker; test model reliability; durable queue |
| Concurrent ingestion | Duplicate entities | Per-user serialization |
| Entity resolution | Fragmented memories | Alias handling and tests |
| Weak raw-message queries | Poor retrieval | Multi-source query generation |
| Jev accuracy on fuzzy tasks | Wrong thread or emotion | Thresholds, escalation, logging |

## 11. Changes from the Original Draft

| Original | Revised |
| --- | --- |
| Agent calls five typed graph tools | One `search_memory` tool; typed lookups used internally by pre-fetch |
| Separate date-detail tool | Removed; handled by `as_of` and temporal edges |
| Classify the agent's response tone after generation | Classify target tone before generation as a hint |
| Ingest on new thread only | Also on inactivity and every N turns |
| Decision model treated as a single step | Jev for scores; separate LLM and NER for query text |
| Ontology: Event, Person, Date, Preference | Adds Relationship edge and optional Goal/Topic |
| Persona updated directly | Fixed core plus versioned adaptive layer, batch updates |
| No safety layer | Dedicated high-recall distress check |

## 12. Testing and Validation Plan

1. Build a set of about 20 to 50 real, messy chat messages with expected thread decisions, emotions and retrieval targets.
2. Compare retrieval quality across the LLM queries, NER queries and raw-message query; drop any source that adds nothing.
3. Measure Jev accuracy and calibration on thread and emotion decisions, then set thresholds.
4. Run Graphiti ingestion on sample conversations with the chosen Groq model and check schema validity and entity resolution.
5. Measure tool-selection errors and end-to-end latency.
6. Red-team the distress check and sycophancy behavior.

## 13. Open Questions

- Which Groq models to use for chat, query generation and ingestion.
- Which embedding provider to use for Graphiti.
- Final thresholds for thread splitting, needs\_memory and distress escalation.
- The window size N and the summary refresh schedule.

## 14. MVP Milestones

1. **Foundation:** Postgres schema, LangGraph thread flow with checkpointer, basic agent with persona.
2. **Decision layer:** Jev integration, thresholds, logging, parallel query generation.
3. **Memory:** Graphiti on Neo4j, ontology, ingestion worker, queue, pre-fetch and fallback tool.
4. **Persona and safety:** adaptive persona versions, distress check, red-team tests.
5. **Tuning:** latency measurement, threshold tuning, entity-resolution fixes.
