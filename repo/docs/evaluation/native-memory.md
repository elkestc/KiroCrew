# Native memory and restart evaluation

Runtime result: `PASS_CONFIGURED` for explicit-workspace Markdown memory through
the native context builder and a fresh session on both subscriptions. Full
gateway restart, consolidation and semantic retrieval remain `INCONCLUSIVE`.

The bounded Codex provider continuity scenario passes: a new provider process
loads the same native session and recalls its prior canary without tools,
preserving exact Terra/high settings. Evidence is `native-continuity.json` in
the exported live metadata; see [provider acceptance](provider-openai.md).
This is adapter session continuity, separate from the durable-store experiment
below.

## MEM-01 / MEM-02: durable facts, corrections and retirement

A separate writer process uses native `MemoryStore.write_projects` and
`write_preferences` to record a disposable Lantern project. It corrects XML to
JSON, refuses a stale compare-and-swap write, and retires a temporary color
preference. A second workspace contains contradictory fixture values.

An offline reader in a fresh process verifies the durable Markdown, FTS search,
current preference, retirement and workspace separation. The native
`ContextBuilder.build_message` includes the selected workspace's constraints,
decision revision, blocked/actionable workstreams and two distinct questions.
The other workspace and retired preference are absent. This uses the native
Markdown path with no initialized semantic/vector store.

Each provider repeats the writer/reader process boundary in its dedicated
evaluation namespace. A new native session, with no prior provider history,
receives the context builder's message. Exact Terra/high and Sonnet 5/high each
return all twelve expected fields and no extra fields: current format, batch
limit, manual approval, current queue and revision, blocked/actionable streams,
next action, separate release/retention question IDs, retention duration, and
null for the retired color. Each sends one prompt, reports a native completion,
requests no tool, and closes cleanly.

Evidence: `native-memory-offline-v2.json` and each provider's
`native-memory-recall-v2.json`; source snapshot
`/tmp/kirocrew-offline-9aj0edac/data/repo`. The first offline harness attempt is
preserved as `native-memory-offline-v1.json`: its writer passed, but the reader
used an incorrect HooksConfig import. Correcting the evaluation helper required
no production change and no model retry.

This also provides bounded relationship-recall evidence for MEM-04 through
MEM-06 and distinct stored questions for MEM-08. It does not establish automatic
issue matching, exactly-once owner contact, workstream execution, automatic
consolidation, stale facts in an already-warm provider session, or a full gateway
restart. MEM-03's separate native task checkpoint proof is recorded in
[TaskRunner](native-taskrunner.md#task-03--mem-03-completed-boundary-survives-process-restart).

## MEM-02 / MEM-08 / MEM-09 / MEM-10: structured-store fixture

`native-semantic-v3-seed.json` and `native-semantic-v3-restart.json` exercise
native `VectorMemoryStore` with its embedding function unavailable, entirely
offline. An explicit correction wins over a later consolidation write; retiring
a preference removes it from active reads and context but preserves its old
value in the audit trail. Two explicit question keys retain separate topics and
conversation IDs through a fresh-process reopen. Keyword retrieval returns the
relevant episode.

The native semantic and episodic write screens reject a known hostile
instruction pattern. This is one regression case for a best-effort screen,
not a claim that arbitrary poisoned memory cannot affect a model. Permission
enforcement must remain outside memory retrieval.

The public list APIs and native `import_memory` transfer active semantic and
episodic records into a second empty store. Current values and retirement match;
repeating the same transfer leaves the fixture episode count at one. Deleting
one question does not delete the other. This logical transfer excludes audit,
transcripts, knowledge, embeddings and other Crew state; it is not a complete
backup or proof of semantic issue deduplication.

The earlier fixture versions are retained: v1 omitted the required store
initialization, and v2 passed the text query positionally into an embedding
argument. Correcting the evaluation helper required no production change.

## Source inventory

All paths below are under the disposable Crew home unless an explicit workspace
or store path is supplied. These are source findings at the pinned commit,
not observed recall results.

| Store | Format and native ownership | Scope and restart implication |
| --- | --- | --- |
| Preferences and project context | `workspace/memory/preferences.md` and `projects.md`; `MemoryStore`, tools and consolidator | Workspace files; durable across process restart; correct retrieval still depends on selecting the right workspace |
| Daily history | `workspace/memory/history/YYYY-MM-DD.md`; append/consolidation and heartbeat prune | Workspace summaries, with age-dependent context rendering |
| Markdown search index | `memory_index.db`, SQLite FTS5 with `porter unicode61`; `MemoryStore` | Rebuildable derived index; an explicit workspace argument moves the index into that workspace |
| Semantic memory | `memory.db`, `semantic_memory` rows keyed by `key`, with JSON value, confidence, source, timestamps and tombstone | Scope depends on the `VectorMemoryStore` instance/path; key prefixes alone are not an authorization boundary |
| Episodic memory | Same database, `episodic_memories`: ID, conversation ID, text, embedding, tags, importance, timestamps and tombstone | Retrieved fragments; vector similarity/time decay/MMR when available, text/keyword fallback otherwise |
| Learned lessons | `lesson.*` semantic keys; legacy `lessons.jsonl` only without initialized vector store | Explicit corrections have priority; inspect both paths when verifying retirement |
| Memory audit/schema | `memory_events`, `memory_meta`, `schema_version` tables in `memory.db` | Records changes and migration metadata; a tombstone does not erase old audit values |
| Conversation history | `sessions/{safe_key}.jsonl`; `ConversationLog` plus session persistence/rewrite modules | Session-keyed messages and metadata, including source-thread/user provenance; survives process restart independently of an in-memory slot |
| Knowledge library | `knowledge/store.py`: sources, items/FTS, entities, relations, mentions, locations, ingestion jobs and ingestion-state tables | Namespace/source relationships and ingestion ownership; its export/import path is distinct from memory import |
| Task checkpoints | Native `runs.json` and spec-adjacent `TASK_PROGRESS.md` | Run/task dependencies and repository identity are separate from prose memories; see TaskRunner report |

## Write, retrieval and retention behavior

`MemoryStore` guards linked roots and uses locked atomic writes for structured
markdown. Preference/project replacement supports an expected-baseline check,
which matters when a consolidator races a correction. FTS updates incrementally
and rebuilds at startup and every 15 heartbeat ticks. A corrupt derived index
can rebuild; a busy database is not treated as corruption.

The native design has two consolidation triggers: a 30-message preference/
project pass and an idle pass after three hours for daily history, episodic
fragments and lessons. The preference offset is in memory; the history
consolidation offset is persisted in transcript metadata. Restart tests must
observe these separately and check repeated/omitted consolidation.

Daily-history context renders days 0–13 in full, days 14–60 as a first entry plus
a remaining-entry count, and days 61–180 as an existence/count marker. Older
files remain out of context until heartbeat deletes files at 365 days. The live
context builder applies a model-dependent cap: 26,400 history characters at
the reference window. Keeping a file on disk does not imply that the next turn
received its facts.

Conversation append rotation starts at 10 MiB and retains up to 200 lines within
the byte cap; dashboard whole-file saves follow their message window instead.
Archive segments, summary/checkpoint metadata and the provider's own resumable
session are different continuity artifacts. All need inspection in a full
gateway restart.

Semantic writes are confidence/source gated. Superseding a value can retire
related stale episodic text using similarity or an exact-phrase fallback.
`delete_semantic` tombstones the semantic row and logs the old value; whether
related prose, episodes and model context stop governing behavior remains a
MEM-02 acceptance question. No exact issue-lineage invariant is established by
similarity retrieval alone.

## Inspection, export and recovery

Native dashboard handlers expose semantic and episodic listing/edit/delete
surfaces and JSON memory import. `VectorMemoryStore.import_memory` accepts
semantic and episodic entries through their ordinary validated write paths.
Knowledge has separate `export_all`/`import_bundle` methods. These are logical
data transfers, not evidence of a complete atomic backup of all Crew state.
MEM-10 must compare the exported scope, restored rows, retrieval and deletion
behavior, including archived transcripts and retained audit values.

## MEM-LESSON-01: native lesson lifecycle

The offline `native-lessons-v1-seed.json` and `native-lessons-v1-restart.json`
use native `LessonStore` and `VectorMemoryStore` with no embedding provider.
The JSONL store reports insert, unchanged repeat and enrichment with a negative
clause, keeping one current lesson. The semantic store reports an unchanged
exact repeat and refuses the known hostile instruction fixture. A fresh process
retrieves current guidance from both stores and native deletion removes it.

The semantic store also replaces a general rule with a longer version carrying
an extra condition, reporting the general rule in `superseded`. This matches
the documented substring deduplication policy. It is useful consolidation
behavior, but a longer rule can apply less broadly; exact owner constraints
must not rely on that heuristic to preserve their authority. This experiment
does not call an LLM consolidator or test embedding similarity.

## Context-growth limits

Native `session_compaction.CompactionCoordinator` uses reported context
percentage and a configurable percentage threshold. It refuses unconfirmed
telemetry and honors backend capability checks. The pinned capability set
supports `/compact` for Kiro and Claude, not Codex; unsupported adapters do not
receive that prompt. This source mapping does not establish provider-managed
compaction quality or the handoff's absolute 200k/250k/400k thresholds. No large
context fill or replacement session manager has been introduced to manufacture
such proof.

Offline native gate replay in `native-recovery-policy-v1-restart.json` confirms
these branches with constructed, unstarted providers. At 95% Codex declines
with `compact_unsupported`, while Claude permits compaction; unknown Claude
telemetry declines with `unconfirmed`. A simulated 450k used out of a 1M window
is 45% and remains below the native threshold for both. This is a `SAFETY_GAP`
if that percentage gate is expected to enforce a strict 400k-token stop. The
replay does not claim actual provider context growth or successful compaction.

## Required experiments

Required scenarios: MEM-01 constraints across sessions; MEM-02 correction and
retirement; MEM-03 task checkpoint; MEM-04 blocked workstreams; MEM-05 architect
rotation; MEM-06 owner-representative rotation; MEM-07 issue continuity;
MEM-08 structurally distinct issues; MEM-09 untrusted memory; MEM-10
inspect/edit/export/restore/delete.

Repeat safety-sensitive scenarios with both providers across a process restart.
Measure actual context signals before applying the handoff's 200k/250k/400k
thresholds. Hidden reasoning retention is not an acceptance requirement.

Sources: [memory/skills/hooks](../system-specs/modules/memory-skills-hooks.md),
[history](../system-specs/modules/history.md),
[knowledge](../system-specs/modules/knowledge.md),
[sessions](../system-specs/modules/session.md).
