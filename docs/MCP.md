# The four-verb MCP server

`magnemo.mcp` is a Model Context Protocol server over stdio. It exposes
**four verbs, two tools that carry the person's answer, and `pending`**, each bound to code that already exists in the package.
Nothing is reimplemented; the server is a governed door, not a second brain.

```
retrieve(query, scope?, budget?, k?)   read   → search.Index.search
stage(note, provenance)                WRITE  → governance.agent_write   (the only write verb)
bootpack(scope?, class?)               read   → bootpack.generate
handoff(usage, trigger, cut?)          write* → handoff.record           (* telemetry + staged note)
keep(note)                             the person's yes → governance.promote  (chat-text, unverified)
drop(note, reason?)                    the person's no  → governance.reject   (chat-text, unverified)
pending(note?)                         read   → what waits for the person's keep; with an id, that note's body
```

**The agent cannot keep a note on its own authority; it carries your yes, and the record says so.** `keep` is for one
moment: the person has said yes to this note, in their own words, in this conversation. The ledger writes that yes
`chat-text:<client> · unverified`, because over MCP the engine cannot tell the person's keyboard from the model's
tool call. It counts half in the Trust Ledger, at most 50 a day are kept this way (`chat_keeps_per_day`; the day is the
local day of the computer the vault is on, reset at its midnight), and a note
Sentinel is holding is not kept by it: a hold needs a verified yes (a click the client draws, or `magnemo yes` at the
person's terminal). `approve` and `reject` are other names for `keep` and `drop`. There is no shell, eval, or file
tool — least privilege is the surface itself.

---

## Install & mount

```bash
pip install -e .                 # zero runtime deps; Python ≥ 3.11
magnemo init ./vault         # once
```

One-line `.mcp.json` (Claude Code reads it from the project root; any MCP client
takes the same shape):

```json
{"mcpServers":{"magnemo":{"command":"python3","args":["-m","magnemo.mcp"],"env":{"MAGNEMO_VAULT":"/abs/path/to/vault","MAGNEMO_AGENT":"my-agent","MAGNEMO_SCOPE":"dev,ops,shared","MAGNEMO_PARTITIONS":"dev,ops,shared"}}}}
```

| env | meaning | default |
|---|---|---|
| `MAGNEMO_VAULT` | vault root (created if missing) | **required** |
| `MAGNEMO_AGENT` | identity stamped on every stage/handoff/receipt | `agent` |
| `MAGNEMO_SCOPE` | partitions this agent may **read** (retrieve / bootpack) — the scope wall | all |
| `MAGNEMO_PARTITIONS` | partitions this agent may **stage into** | all |

Diagnostics go to stderr; stdout is pure JSON-RPC.

---

## The yes: never mid-work, asked at the pause

**`stage` never waits.** It asks nothing, on any transport: the note lands in the review queue and the result says one
line for the agent to repeat, `Staged. Say keep when you want it kept.` The agent keeps working. A person who steps
away from the desk comes back to a finished build and a queue, never to a question that stopped it.

The ask is at a pause, once, about everything that waits. `pending` lists the staged notes nobody has answered, and the
line to say: `N notes staged since you left. keep all / pick / later.` The agent says it at the end of its own turn.
The person says keep all (`keep` with `"all"`: each note its own ledger line), picks, or says later. Later and no
answer are the same thing: nothing blocks, nothing is lost, the notes wait for the next pause.

On `handoff`, a client that said at `initialize` that it can put a form to its user is sent one MCP elicitation
request for the whole batch:

```text
3 notes staged since you left. keep all / pick / later.

- <a note's title> (<the seat>)
- …

Keep them as Memory?    Keep all · Pick · Later
```

The client draws that in its own window and sends back what the person chose. **The model is not on that path.** It
does not see the request, and none of its tools answers it. Keep all promotes each note on its own ledger line with
`answered_by: elicitation:<client>`, a verified yes. Pick sends the agent back to the chat to ask which. Later, a
declined or dismissed question, or no answer in two minutes leaves every note staged; the question is withdrawn when
the wait ends, and the handoff completes. A note Sentinel is holding is never put to the person this way.

| Client | Seen | Says it can ask | What happened |
|---|---|---|---|
| Claude Code, a person at it | 2.1.296, Oct 12 2026 | yes (the dialog was drawn in the chat) | 0.6.8–0.6.9, when the question was asked inside `stage`: the agent staged one note; the person pressed Yes; the note was promoted 9 seconds after it was written. The ledger line: `approved`, actor `founder`, `ran_by: mcp:drill-seat`, `answered_by: elicitation:claude-code 2.1.296`. |
| Claude Code, run with nobody at it (`claude -p`) | 2.1.296, Oct 12 2026 | yes (form and url) | It let go of the question in 5 ms. Magnemo left the note staged. |
| Claude desktop app | untested | | |
| Cursor | untested | | |
| VS Code | untested | | |

A client that cannot draw a question (claude.ai today) gets the line in the `handoff` and `pending` results for the
agent to say. When the person says yes, `keep` carries it, and the ledger line says `chat-text`, unverified.
`magnemo yes <id>` at their own terminal is the verified yes: it clears a hold, and on a note kept in the chat it
re-ledgers the yes as verified, the first one kept on the record. It needs their own terminal and a name the vault
lists, and it refuses an agent's shell ([KNOWN_LIMITS.md](../KNOWN_LIMITS.md)).

For a harness with nobody at it:

- `MAGNEMO_ASK=off` on the server: the batch question is never drawn, and every note waits.
- Or leave it on and have the harness dismiss the request. In Claude Code that is an `Elicitation` hook that exits 2.
  A dismissed or declined request is never read as a no.
- An accepted answer that arrives in under 300 ms is refused and logged (`judgment.refused`, `answered_by:
  refused:too-fast`): it was not read by a person. A harness that waits longer and then accepts is not caught by
  this; `answered_by` on the ledger is what shows where a yes came from.

The server speaks the `initialize` handshake (protocol revisions up to 2025-11-25). A client on the 2026-07-28
revision probes first and falls back to it, as Claude Code 2.1.296 was seen to do. On that newer revision the same
question travels a different way (an input request inside the tool's result); the server does not speak it yet.

---

## The tools

### `retrieve(query, scope?, budget?, k?)`
Canonical memory only: `retrieve` does not search staged notes.
Returns a JSON payload, never a raw dump:

```json
{"rid":"…","scope":["dev"],"budget":4000,"rendition":"snippet","truncated":false,
 "candidates":3,"served":3,
 "results":[{"pointer":"mn://dev/knowledge/<id>","id":"…","title":"…","score":2.1,
             "yield":"+2/-0","snippet":"first 240 chars…"}],
 "payload_bytes":812}
```

- `scope` must lie inside `MAGNEMO_SCOPE`; otherwise `SCOPE WALL` and nothing is logged.
- `budget` (bytes, 200–32 000, default 4 000) is honoured deterministically:
  **snippet → fewer snippets → `mn://` pointers only**. `truncated` tells you it happened.
- `rid` is the retrieval receipt. Cite it with `magnemo outcome <rid> approved|denied`
  and every note that informed the action earns or loses yield.

### `stage(note, provenance)`
The only write verb. Lands in `_staging/` as a **memory candidate**; never touches canon.

```json
{"note":{"title":"…","body":"…","partition":"ops","store":"knowledge",
         "impact":"money","tags":"pattern","taint":"inbound-email"},
 "provenance":{"source":"run#1847","author":"ops-agent"}}
```

Refused before touching disk: missing provenance (**paperless**), blank `source`,
missing title/body/partition/store, unknown store, partition outside `MAGNEMO_PARTITIONS`.
Returns `{staged, salience, salience_components, duplicate_of, duplicate_similarity, taint, bytes}`.

### `bootpack(scope?, class?)`
The document a session reads first. `class` = `worker` (lean) | `partner`
(adds the relationship layer when a codex exists). Sections, in doctrine order:
Charter (verbatim, never fabricated) → **gates** (the Gate Map at ledger time) →
**your autonomy** (the mounting agent's own scorecard, `MAGNEMO_AGENT`) → canon digest → open threads & KAIROS-ranked queue → **last handoff** → ledger tail. Pure function of vault state: same state,
same bytes. The MCP path returns the pack; it never writes `_index/`.

### `handoff(usage, trigger, cut?)`
`trigger ∈ wall|planned|compaction|other`. Appends one entry to
`_ledger/handoffs.jsonl` (with the agent's autonomy `levels` at the boundary) and
stages a provenance-complete handoff note. The next `bootpack` serves it under
`LAST HANDOFF`. Doctrine: hand off at ~88–90%.

### `keep(note)` · `drop(note, reason?)`
Carry the person's yes or no from the chat. Call them only when the person has answered this note in their own words
in this conversation; never draw a panel, never on the agent's own judgment. `note` is the staged note's id (its last
eight characters are enough). `keep` returns one line to repeat: `Kept. Written by <writer>, your yes in the chat
(<client>). "<title>" is Memory now.` The refusals: no note waiting by that id; Sentinel is holding it (it stays held
with its alert); the day's cap is reached. `keep` with `"all"` keeps every note `pending` lists as waiting, one ledger
line each, when the person said keep all; it opens with the same count `pending` gives (`N waiting · M held: kept K of
the N waiting.`). A note carrying contact details keeps like any other; its `contact` line rides the ledger's yes.

### `pending(note?)`
Read-only. The staged notes nobody has answered (not Sentinel's alert notes, not handoff telemetry), which of them
Sentinel holds, and the one line to say at a pause: `N notes staged since you left. keep all / pick / later.` Its
`header` is the one count the boot pack and `keep all` also say: `N waiting · M held`. Times are local, with their
offset (`Oct 27, 10:12 PM −07:00`); the files and the ledger stay UTC.
With `note` (an id, or its last eight characters), one staged note whole: its body, its provenance (author, source,
written), labelled `staged · not yet Memory`. This is not `retrieve`, which serves Memory only; it is how a note left for
later stays within an agent's reach, on every transport. A note Sentinel holds returns its alert and no body.

### The first line
`magnemo mount` writes this block into the file the client reads first (`CLAUDE.md` for Claude Code,
`.cursor/rules/magnemo.mdc` for Cursor), between `<!-- MAGNEMO:BEGIN … -->` and `<!-- MAGNEMO:END -->`; `magnemo
unmount` removes it. Claude Desktop reads no project file first: put the same words where it reads instructions.

> This project's Memory is MAGNEMO. At the start of a session call `bootpack`. Before answering anything about this
> project, call `retrieve`. Each time you finish a step or make a decision, `stage` it right then, unasked — one note
> per step, after a restart too. Remembering means proposing; the person's keep makes it Memory. Never stop to ask; at
> the end of your turn say `pending`'s line.

The boot pack carries it in one sentence under its title. `mount` writes the absolute path of the server it found;
`doctor` checks that path, and checks only MAGNEMO's own entries; any other server is listed and left unchecked.

---

## Cascades — deterministic, zero model calls

```
stage(note, provenance)
  │
  ├─ validate ──── paperless / malformed ──▶ REFUSED (nothing on disk)
  ├─ write-partition wall ──────────────────▶ DENIED
  ├─ Sentinel: secret ─▶ held, body redacted · S14 contact ─▶ kept as written, `contact` line + ledger · injection ─▶ tainted, ALERT
  ├─ pattern separation: trigram-Jaccard vs in-partition canon + staged queue
  │        ≥ 0.6 → dup_of / dup_sim in frontmatter + `dup-candidate` tag
  ├─ governance.agent_write ─▶ KAIROS salience (consequence·novelty·operator·source) ─▶ _staging/<id>.md
  └─ foresight 'stage' event {id, salience, dup_of, taint}
```

```
retrieve(query, scope?, budget?)
  │
  ├─ scope gate ─── outside MAGNEMO_SCOPE ──▶ SCOPE WALL (no receipt, no cost event)
  ├─ Index.search walled to scope  (BM25 × strength × yield × taint-penalty)  ─▶ receipt rid
  ├─ rendition select to fit budget:  snippet ─▶ truncated snippet ─▶ mn:// pointers
  └─ foresight 'retrieval' event {rid, scope, budget, rendition, truncated, candidates, served}
```

```
bootpack(scope?, class?)
  │
  ├─ scope gate
  ├─ bootpack.generate:  CHARTER (verbatim) ─▶ GATES (ledger time) ─▶ CANON DIGEST ─▶ OPEN THREADS + queue
  │                      ─▶ LAST HANDOFF (from handoffs.jsonl) ─▶ LEDGER TAIL
  └─ foresight 'bootpack' event {class, scope, bytes}
```

```
handoff(usage, trigger, cut?)
  │
  ├─ handoff.record ─▶ _ledger/handoffs.jsonl  (append-only)
  │                 ─▶ governance.agent_write ─▶ _staging/<handoff-note>.md  (KAIROS-scored)
  ├─ foresight 'handoff' event
  └─ next bootpack() — any process, any session — renders it under LAST HANDOFF
```

---

## Invariants (each has a test in `tests/test_mcp.py`)

| invariant | how it holds |
|---|---|
| staging is the only agent write | the four verbs and `pending` leave the canon file set byte-identical; `keep` moves a note only on the person's yes; `stage` never waits; `promote` → `unknown tool` |
| provenance mandatory | 9 refusal shapes, none reach disk |
| scope walls | `MAGNEMO_SCOPE=dev` never returns ops-only canon; explicit `scope=ops` → `SCOPE WALL` |
| budgets cap payloads, truncation logged | served ≤ budget; `truncated` in both payload and cost event; clamp at 32 000 logged |
| free tier | `mcp.py` imports stdlib + package only; no network words anywhere in the chain |
| least privilege | exactly seven names; dispatch gated to *declared* tools; no eval/exec/shell |

---

## Three postures

**1. Native.** The agent runs with this server mounted and uses the four verbs
directly: `bootpack` on wake, `retrieve` before acting, `stage` what it learned,
`handoff` at ~88%. The vault is the agent's memory. (Claude Code via `.mcp.json`,
any MCP client.)

**2. Mount-and-govern.** The agent already has its own memory (a framework store,
a vector DB, a notes folder). Mount this server *alongside* it and route only the
*governed* moments through the four verbs: candidates worth your review go to
`stage`; decisions the agent must not make alone are `retrieve`d from canon. The
existing store keeps scratch; Magnemo keeps truth. Nothing in the agent's own
memory becomes canon without passing the staging gate.

**3. Gateway.** One server process, many agents, each with its own
`MAGNEMO_AGENT` / `MAGNEMO_SCOPE` / `MAGNEMO_PARTITIONS` — or one process per agent
behind a gateway that sets those per connection. Scope walls give a dev agent
dev, an ops agent ops, and the `shared/` bus to both; receipts, cost events, and
handoff telemetry stay attributable per agent. The yes is still the person's: said in
the chat (`keep`, unverified) or typed at the CLI (verified).

In every posture the same two things are true of this server: **agents can only stage**, and
**no tool keeps a note on the agent's own authority**.
