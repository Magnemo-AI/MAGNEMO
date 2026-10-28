"""magnemo.mcp — the MCP server: four verbs, keep and drop to carry the person's yes or no, and pending to list what waits.

A Model Context Protocol server that exposes EXACTLY seven tools, each bound to existing magnemo code (nothing
reimplemented here):

  retrieve(query, scope?, budget?)   → search.Index        scored, budgeted, rendition-selected
  stage(note, provenance)            → governance.agent_write   the ONLY write verb; _staging only
  bootpack(scope?, class?)           → bootpack.generate   the v0.3 boot pack (worker | partner)
  handoff(usage, trigger, cut?)      → handoff.record      boundary telemetry + staged handoff note

  keep(note) / drop(note)            → governance.promote / reject, carrying the person's yes or no from the chat
  pending(note?)                     → the staged notes nobody has answered yet; with an id, that note's body (read-only)

P-106 v3: the agent cannot keep a note on its own authority; keep carries the person's yes, said in the chat, and the
record says so (`answered_by: chat-text:<client> · unverified`, weighed lower in the trust arithmetic, at most
`chat_keeps_per_day` a day). A note Sentinel holds needs a verified yes (a terminal, or a question the client draws).
There is no shell, no eval, no file tool — least privilege is the surface itself.

THE EMPTY DESK (P-106 addendum A). `stage` never waits: no question is drawn inside it, on any transport; it returns
one line ("Staged. Say keep when you want it kept.") and the agent keeps working. The ask moves to the pause, batched:
`pending` lists what waits, and the agent says once, at the end of its own turn, "N notes staged since you left. keep
all / pick / later." On `handoff`, a client that can put a form to its user (MCP elicitation) draws that one batch
question; the model is not on that path. Keep all promotes each note on its own ledger line (`elicitation:<client>`),
Pick sends the agent back to the chat, and Later, a dismissed question or no answer leaves every note staged: nothing
blocks, nothing is lost. An answer faster than a person can read (under 300 ms) is refused and logged.

THE FIRST LINE (P-106 addendum B). Remembering means proposing: `stage` proposes, the person's keep makes it Memory,
and the tools say so. `pending` with an id reads back one staged note's body, labelled `staged · not yet Memory`, so
"later" never puts a note out of reach (a held note gives its alert, never its body). The chat-keep cap is counted in
the local day of the computer the vault is on and resets at its midnight.

Configuration (env):
  MAGNEMO_VAULT       path to the vault root                         (required)
  MAGNEMO_AGENT       calling agent's identity, e.g. "ops-agent"     (default "agent")
  MAGNEMO_PARTITIONS  comma list this agent may WRITE to             (default: all)
  MAGNEMO_SCOPE       comma list this agent may READ from            (default: all)
                    retrieve/bootpack scope must fall inside it — the scope wall.
  MAGNEMO_ASK         "off": never draw the batch question at handoff (a harness with no person at it)   (default: ask where the client can)
  MAGNEMO_ASK_SECONDS how long the batch question at handoff waits before the notes are left for later   (default 120)

Run:  MAGNEMO_VAULT=./vault python -m magnemo.mcp
"""
from __future__ import annotations
import os, sys, json, re
from .transport import Server
from .config import env
from .vault import PARTITIONS, STORES
from .bootpack import CLASSES
from .handoff import TRIGGERS
from . import bootpack, handoff, foresight, kairos, desk
from .desk import local_day

TOOL_NAMES = ("retrieve", "stage", "bootpack", "handoff", "keep", "drop", "pending")   # P-106 v3 + addendum A: the yes carried from the chat; what waits
TOOL_ALIASES = {"approve": "keep", "reject": "drop"}                          # the other words for the same two tools
CHAT_KEEPS_PER_DAY = 50                                                       # P-106 v3: a chat-carried yes has a daily cap

DEFAULT_BUDGET = 4000      # bytes of served payload per retrieve, unless the caller says otherwise
MAX_BUDGET = 32000         # hard ceiling — a budget above this is clamped and the clamp is logged
SNIPPET_CHARS = 240        # "snippet" rendition: per-note body excerpt length
ASK_SECONDS = 120          # how long the batch question at handoff waits for the person before the notes are left for later
TOO_FAST_S = 0.3           # an answer inside 300 ms of the question was not read by a person: refused, logged
STAGED_LINE = "Staged. Say keep when you want it kept."                   # P-106 addendum A: what stage says, always
BATCH_ANSWERS = ("Keep all", "Pick", "Later")
BATCH_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string", "title": "Keep them as Memory?",
                                                             "enum": list(BATCH_ANSWERS), "default": "Later"}}}


def batch_line(n: int) -> str:
    """The one line said at a pause, in the person's grain."""
    return "%d note%s staged since you left. keep all / pick / later." % (n, "" if n == 1 else "s")


def tools_spec(vault=None) -> list:
    """The four verbs. With a vault, the schema enums reflect THAT vault's declared
    partitions and stores; without one, the defaults every vault is born with."""
    P = tuple(vault.partitions) if vault is not None else PARTITIONS
    S = dict(vault.stores) if vault is not None else STORES
    return [
        {
            "name": "retrieve",
            "title": "Look something up in memory",
            "annotations": {"title": "Look something up in memory", "readOnlyHint": True,
                            "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "description": (
                "Retrieve canonical (keyholder-approved) memory relevant to a query. Returns a "
                "scored, BUDGETED payload: mn:// pointers plus snippet renditions, never raw "
                "dumps. Scope is partition-walled; payload size is logged to the Foresight "
                "counters. Cite the returned rid when the action resolves."),
            "inputSchema": {"type": "object", "properties": {
                "query": {"type": "string", "description": "what you need to remember"},
                "scope": {"type": "string", "enum": list(P),
                          "description": "partition to search (must be inside this agent's MAGNEMO_SCOPE)"},
                "budget": {"type": "integer", "minimum": 200, "maximum": MAX_BUDGET,
                           "default": DEFAULT_BUDGET,
                           "description": "max payload bytes; results are truncated/downgraded to fit and the truncation is logged"},
                "k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            }, "required": ["query"]},
        },
        {
            "name": "stage",
            "title": "Draft an entry for a person to review",
            "annotations": {"title": "Draft an entry for a person to review", "readOnlyHint": False,
                            "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
            "description": (
                "Remembering means proposing: this stages a note; the person's keep makes it Memory. "
                "Contact details are kept as written and labelled; the label is checked once before anything leaves "
                "this computer. "
                "Stage a memory candidate for the person's review. This is the only write verb: "
                "the note lands in _staging/ with mandatory provenance and never touches "
                "canon. It never waits and asks nothing: keep working. Returns the staged id, its "
                "salience, a duplicate flag, and one line to say: 'Staged. Say keep when you want "
                "it kept.' Ask about what you staged only at a pause (see pending), never mid-work. "
                "Malformed or paperless (no provenance) notes are refused."),
            "inputSchema": {"type": "object", "properties": {
                "note": {"type": "object", "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "partition": {"type": "string", "enum": list(P)},
                    "store": {"type": "string",
                              "description": "store within the partition: " + "; ".join(
                                  f"{p}: {', '.join(S[p])}" for p in P)},
                    "tags": {"type": "string", "description": "comma-separated"},
                    "supersedes": {"type": "string", "description": "id of the note this replaces"},
                    "impact": {"type": "string",
                               "enum": ["security", "money", "correctness", "process", "info"],
                               "description": "declared impact class (consequence). Default: info"},
                    "taint": {"type": "string",
                              "description": "REQUIRED when content originates from an untrusted source — label it"},
                }, "required": ["title", "body", "partition", "store"]},
                "provenance": {"type": "object", "properties": {
                    "source": {"type": "string",
                               "description": "run id / gate id / audit id — where this knowledge came from"},
                    "author": {"type": "string",
                               "description": "defaults to this server's MAGNEMO_AGENT identity"},
                }, "required": ["source"]},
            }, "required": ["note", "provenance"]},
        },
        {
            "name": "bootpack",
            "title": "Read what this agent wakes up knowing",
            "annotations": {"title": "Read what this agent wakes up knowing", "readOnlyHint": True,
                            "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "description": (
                "The boot pack: Charter first (verbatim, never fabricated), then the Gate "
                "Map, YOUR AUTONOMY (this agent's own trust levels), canon digest, open "
                "threads, salience-ranked review queue, last handoff, ledger tail. Read it "
                "FIRST on every wake. Deterministic: same vault state, same bytes."),
            "inputSchema": {"type": "object", "properties": {
                "scope": {"type": "string", "enum": list(P),
                          "description": "partition to orient on (must be inside MAGNEMO_SCOPE)"},
                "class": {"type": "string", "enum": list(CLASSES), "default": "worker",
                          "description": "worker = lean; partner = adds the relationship layer when a codex exists"},
            }},
        },
        {
            "name": "handoff",
            "title": "Record where this session stopped",
            "annotations": {"title": "Record where this session stopped", "readOnlyHint": False,
                            "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
            "description": (
                "Record a session boundary: appends telemetry (usage %, trigger, what was "
                "cut) to the append-only handoffs ledger AND stages a provenance-complete "
                "handoff note. The next bootpack inherits it. Doctrine: hand off at ~88-90%, "
                "do not ride to the wall. A pause: where the client can draw a question, the "
                "person is asked once about every note still staged (keep all / pick / later); "
                "later or no answer leaves them staged and blocks nothing."),
            "inputSchema": {"type": "object", "properties": {
                "usage": {"type": "number", "minimum": 0, "maximum": 100,
                          "description": "context usage percent at the boundary"},
                "trigger": {"type": "string", "enum": list(TRIGGERS)},
                "cut": {"type": "string", "description": "what was cut / deferred at the boundary"},
            }, "required": ["usage", "trigger"]},
        },
        {
            "name": "keep",
            "title": "Keep a note the person said yes to",
            "annotations": {"title": "Keep a note the person said yes to", "readOnlyHint": False,
                            "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "description": (
                "Call keep only when the person has said yes to this note in their own words in this conversation; "
                "never draw a panel, and never keep on your own judgment. The note becomes Memory, and the record says "
                "the yes was given in the chat (unverified). A note Sentinel is holding is not kept this way. "
                "\"all\" keeps every note pending lists, when the person said keep all; each is its own ledger line. "
                "The cap: at most %d notes a day are kept by a yes in the chat, counted in the local day of the computer "
                "the vault is on and reset at its midnight. Two ways past it: the person's own terminal (magnemo yes "
                "<id>), or the one question their client draws at a pause (handoff)." % CHAT_KEEPS_PER_DAY),
            "inputSchema": {"type": "object", "properties": {
                "note": {"type": "string", "description": "the staged note's id, its last 8 characters, or \"all\""},
            }, "required": ["note"]},
        },
        {
            "name": "drop",
            "title": "Drop a note the person said no to",
            "annotations": {"title": "Drop a note the person said no to", "readOnlyHint": False,
                            "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "description": (
                "Call drop only when the person has said no to this note in their own words in this conversation. "
                "The note is set aside as rejected, with their reason, and never becomes Memory."),
            "inputSchema": {"type": "object", "properties": {
                "note": {"type": "string", "description": "the staged note's id, or its last 8 characters"},
                "reason": {"type": "string", "description": "the person's reason, in their words, if they gave one"},
            }, "required": ["note"]},
        },
        {
            "name": "pending",
            "title": "List what waits for the person's keep",
            "annotations": {"title": "List what waits for the person's keep", "readOnlyHint": True,
                            "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
            "description": (
                "The staged notes nobody has answered yet, and the one line to say about them. Call it at a "
                "pause, at the end of your own turn, never mid-work; say its line once ('N notes staged since you "
                "left. keep all / pick / later.'). Later, or no answer, is fine: nothing blocks and nothing is lost. "
                "With a note's id, it returns that staged note's full body and where it came from, labelled "
                "'staged · not yet Memory' (a note Sentinel holds gives its alert, not its body)."),
            "inputSchema": {"type": "object", "properties": {
                "note": {"type": "string", "description": "optional: a staged note's id, or its last 8 characters, to read its body"},
            }},
        },
    ]


class MemoryServer(Server):
    """Four verbs to work with, keep and drop to carry the person's yes or no from the chat (P-106 v3), and pending. Inherits
    the JSON-RPC/stdio plumbing from transport.Server; declares the one tool surface."""
    TOOL_ALIASES = TOOL_ALIASES

    def __init__(self):
        super().__init__()
        rs = env("SCOPE", ",".join(self.vault.partitions))
        self.read_scope = self.vault.resolve_scope(rs.split(","))
        if not self.read_scope:
            sys.stderr.write(f"MAGNEMO_SCOPE={rs!r} names no valid partition or scope — "
                             f"valid: {', '.join(self.vault.partitions)}"
                             f"{' · aliases: ' + ', '.join(self.vault.scopes()) if self.vault.scopes() else ''}"
                             " (unset MAGNEMO_SCOPE to allow all)\n")
            sys.exit(2)
        # P-54: the record tells the truth about itself — the queue depth at session start, as the docs say
        try:
            _w, _h = desk.counts(desk.waiting(self.vault))          # addendum C: the one count
            _qs = f" waiting={_w} held={_h}"
        except Exception:
            _qs = ""
        sys.stderr.write(f"[magnemo.mcp] agent={self.agent} read_scope={','.join(self.read_scope)} "
                         f"write_partitions={','.join(self.write_partitions)} tools={','.join(TOOL_NAMES)}{_qs}\n")

    def tools_spec(self) -> list:
        return tools_spec(self.vault)

    # ---------------- scope wall (read side) ----------------
    def _gate_scope(self, scope, verb: str):
        """Resolve the partition filter for a read verb. Explicit scope must be
        inside MAGNEMO_SCOPE; omitted scope means "everything I'm allowed"."""
        if scope is not None:
            if scope not in self.vault.partitions:
                raise ValueError(f"unknown scope: {scope!r} (one of {', '.join(self.vault.partitions)})")
            if scope not in self.read_scope:
                raise PermissionError(
                    f"SCOPE WALL: agent '{self.agent}' may not {verb} partition '{scope}'. "
                    f"Read scope: {', '.join(self.read_scope)}")
            return (scope,)
        return tuple(self.read_scope)

    # ---------------- retrieve ----------------
    def t_retrieve(self, a):
        query = (a.get("query") or "").strip()
        if not query:
            raise ValueError("retrieve requires a non-empty query")
        parts = self._gate_scope(a.get("scope"), "retrieve")
        k = max(1, min(int(a.get("k", 5)), 20))
        asked = int(a.get("budget", DEFAULT_BUDGET))
        budget = max(200, min(asked, MAX_BUDGET))
        # Candidate set from the existing index: scope-walled, receipt logged,
        # cost NOT logged here — the served (post-budget) payload is what counts.
        # P-74: a tainted note is never served to an agent until a keyholder clears it (`magnemo clear`)
        out = self.index.search(query, k, None, max_chars=SNIPPET_CHARS,
                                agent=self.agent, log_receipt=True, include_tainted=False,
                                partitions=None if set(parts) == set(self.vault.partitions) else parts,
                                log_cost=False)
        rendered, rendition, truncated = select_rendition(out["results"], budget)
        payload = {
            "rid": out["rid"], "query": query,
            "scope": list(parts), "budget": budget,
            "rendition": rendition, "truncated": truncated,
            "candidates": len(out["results"]), "served": len(rendered),
            "results": rendered,
        }
        text = json.dumps(payload, indent=1)
        nbytes = len(text.encode("utf-8"))
        payload["payload_bytes"] = nbytes
        foresight.log_cost(self.vault, "retrieval", nbytes, {
            "via": "mcp", "rid": out["rid"], "agent": self.agent, "k": k,
            "scope": ",".join(parts), "budget": budget, "budget_asked": asked,
            "rendition": rendition, "truncated": truncated,
            "candidates": len(out["results"]), "served": len(rendered)})
        if not rendered:
            payload["note"] = ("No canonical memory matches in scope. Staged notes are "
                               "excluded until a keyholder promotes them.")
        return json.dumps(payload, indent=1)

    # ---------------- stage ----------------
    def t_stage(self, a):
        note = a.get("note")
        prov = a.get("provenance")
        if not isinstance(note, dict):
            raise ValueError("REFUSED: 'note' must be an object")
        if not isinstance(prov, dict):
            raise ValueError("REFUSED: paperless note — 'provenance' object is mandatory")
        source = (prov.get("source") or "").strip()
        if not source:
            raise ValueError("REFUSED: paperless note — provenance.source is mandatory "
                             "(run id / gate id / audit id)")
        # P-54 · PROVENANCE ENFORCED AT THE DOOR: the author of an MCP stage is the seat
        # (MAGNEMO_AGENT), always. A seat may not sign as a keyholder; a different non-keyholder
        # name is kept as `claimed_author` (an appended provenance field), never as the author.
        claimed = (prov.get("author") or "").strip()
        author = self.agent
        if claimed:
            from .config import load_config as _lc
            from . import trust as _trust
            if _trust.is_human(_lc(self.vault.root), claimed):
                try:
                    _trust.record(self.vault, self.agent, "stage", "denied", by="magnemo.mcp",
                                  reason=f"an agent seat cannot sign as a keyholder: claimed author {claimed!r}")
                except Exception:
                    pass
                raise PermissionError(
                    f"REFUSED: an agent seat cannot sign as a keyholder ({claimed!r}); "
                    "say who directed it in `source`")
        title = (note.get("title") or "").strip()
        body = (note.get("body") or "").strip()
        part = note.get("partition")
        store = note.get("store")
        missing = [k for k, v in (("title", title), ("body", body),
                                  ("partition", part), ("store", store)) if not v]
        if missing:
            raise ValueError(f"REFUSED: malformed note — missing {', '.join(missing)}")
        if part not in self.vault.partitions:
            raise ValueError(f"REFUSED: unknown partition {part!r}")
        if store not in self.vault.stores[part]:
            raise ValueError(f"REFUSED: store {store!r} is not valid in partition "
                             f"'{part}' (valid: {', '.join(self.vault.stores[part])})")
        if part not in self.write_partitions:
            # P-02: a wall hit is a recorded `denied` event for this agent in `stage`
            # — small, decaying, and visible on the scorecard. Never raises into the refusal.
            try:
                from . import trust
                trust.record(self.vault, self.agent, "stage", "denied", by="magnemo.mcp",
                             reason=f"partition wall: tried to stage into '{part}'")
            except Exception:
                pass
            raise PermissionError(
                f"DENIED: agent '{self.agent}' may not stage into partition '{part}'. "
                f"Write partitions: {', '.join(self.write_partitions)}")
        impact = note.get("impact") or "info"
        # P-74 · SENTINEL AT THE GATE: the main door is swept like the inbox and the Room.
        from . import sentinel
        sv = sentinel.gate(self.vault, title, body, partition=part, store=store, source=source, door="MCP")
        title, body = sv["title"], sv["body"]
        # Pattern separation: is this a near-duplicate of something already
        # known (canon in-partition) or already waiting (staged)?
        dup = nearest_duplicate(title, body, part, self.vault)
        # The ONLY write path: governance.agent_write → vault.stage → _staging/.
        # KAIROS salience is computed inside agent_write, at stage time.
        n = self.gov.agent_write(
            title=title, body=body, partition=part, store=store,
            author=author, source=source, tags=note.get("tags", "") or "",
            supersedes=note.get("supersedes", "") or "", taint=sv["taint"] or note.get("taint", "") or "",
            impact=impact, contact=sv["contact"])
        if claimed and claimed != author:
            n.extra["claimed_author"] = claimed
            self.vault.rewrite(n)
        if dup:
            n.extra["dup_of"] = dup["id"]
            n.extra["dup_sim"] = f"{dup['sim']:.4f}"
            tags = [t.strip() for t in n.tags.split(",") if t.strip()]
            if DUP_TAG not in tags:
                tags.append(DUP_TAG)
            n.tags = ",".join(tags)
            self.vault.rewrite(n)
        # P-106 addendum A · THE EMPTY DESK: stage never waits. No question here, on any transport; the ask is at a pause.
        nbytes = len(n.to_markdown().encode("utf-8"))
        foresight.log_cost(self.vault, "stage", nbytes, {
            "via": "mcp", "id": n.id, "agent": author, "partition": part, "store": store,
            "salience": n.salience, "dup_of": dup["id"] if dup else "",
            "taint": bool(n.taint)})
        return json.dumps({
            "staged": n.id, "status": n.status,
            "path": f"_staging/{n.id}.md",
            "salience": n.salience, "salience_components": json.loads(n.salience_components or "{}"),
            "duplicate_of": dup["id"] if dup else None,
            "duplicate_similarity": round(dup["sim"], 4) if dup else None,
            "taint": n.taint or None,
            "sentinel": sv["verdict"] and {"verdict": sv["verdict"].upper(), "pattern": sv["pattern"], "alert": sv["alert"]},
            "contact": sv["contact"] or None,
            "bytes": nbytes,
            "note": ({"held": f"HELD by Sentinel: secret-shaped text (pattern {sv['pattern']}). The value was not stored — "
                              "the note carries the redaction line and a taint. Move the secret out of what you stage.",
                      "tainted": f"TAINTED by Sentinel: an instruction-shaped line (pattern {sv['pattern']}). Staged with a "
                                 "taint beside an ALERT note; retrieve will not serve it until a keyholder clears it."}
                     .get(sv["verdict"], "")
                     + (" " if sv["verdict"] else "")
                     + (f"Labelled: {sv['contact']} (kept as written; asked once before it leaves this computer). "
                        if sv["contact"] else "")
                     + STAGED_LINE),
            "say": STAGED_LINE,
        }, indent=1)

    # ---------------- P-106 · THE CHAT YES ----------------
    def _staged_note(self, ref: str):
        ref = (ref or "").strip()
        if not ref:
            raise ValueError("REFUSED: name the note (its id, or the last 8 characters the stage result showed)")
        hits = [n for n in self.vault.staged() if n.status == "staged" and (n.id == ref or n.id.endswith(ref))]
        if not hits:
            raise ValueError(f"no note waiting with the id {ref!r}")
        if len(hits) > 1:
            raise ValueError(f"{ref!r} names {len(hits)} waiting notes; use the full id")
        return hits[0]

    def chat_label(self) -> str:
        return "chat-text:" + self.client_label() + " · unverified"

    def _keyholder(self) -> str:
        from .config import load_config
        humans = (load_config(self.vault.root).get("trust") or {}).get("humans") or []
        return humans[0] if humans else "founder"

    def held_note_words(self, n) -> str:
        return ("Not kept: Sentinel is holding this note (%s). A yes in the chat does not clear a hold; it needs a verified "
                "yes: the person reads the note and gives it at their own terminal (magnemo yes %s)." % (n.taint, n.id[-8:]))

    def chat_keeps_today(self) -> int:
        """Chat keeps in the vault's local day: the clock of the computer the vault is on (TZ, if set), reset at its
        midnight. The ledger stamps UTC; each stamp is read in local time before it is counted."""
        today = local_day()
        return sum(1 for e in self.gov.ledger.entries() if e.get("action_class") == "memory.promote"
                   and e.get("verdict") == "approved" and e.get("door") == "chat-text" and local_day(e.get("ts")) == today)

    def chat_cap(self) -> int:
        from .config import load_config
        try:
            return int((load_config(self.vault.root).get("chat_keeps_per_day")) or CHAT_KEEPS_PER_DAY)
        except (TypeError, ValueError):
            return CHAT_KEEPS_PER_DAY

    def waiting(self) -> list:
        """What waits for the person (desk.waiting): staged or held, not Sentinel's own alert notes, not handoffs."""
        return desk.waiting(self.vault)

    def t_pending(self, a):
        ref = str(a.get("note") or a.get("id") or "").strip()
        if ref:
            return self.read_staged(ref)
        notes = self.waiting()
        free = [n for n in notes if not desk.is_held(n)]
        rows = [{"id": n.id, "title": n.title, "author": n.author, "held": desk.is_held(n), "written": desk.local(n.written),
                 **({"contact": n.extra["contact"]} if n.extra.get("contact") else {}),
                 "first_line": next((ln.strip() for ln in n.body.split("\n") if ln.strip()), "")[:160]} for n in notes]
        return json.dumps({
            "header": desk.count_line(notes),                # addendum C · ONE COUNT: the boot pack and keep all say the same
            "pending": len(free), "held": len(notes) - len(free), "notes": rows,
            "say": batch_line(len(free)) if free else "Nothing waits for a keep.",
            "note": ("Say the line once, at the end of your turn. keep all: call keep with \"all\". pick: ask which, and keep "
                     "those. later, or no answer: leave them; nothing blocks." if free else "")
                    + (" Held notes need a verified yes at the person's own terminal." if len(notes) > len(free) else ""),
        }, indent=1)

    def read_staged(self, ref: str) -> str:
        """P-106 addendum B · THE UNKEPT BODY: one staged note, whole, with its provenance and the label that says what it
        is. Not `retrieve` (which serves Memory only, P-104); a held or tainted note gives its alert and no body
        (Sentinel's rule). The read scope wall holds."""
        hits = [n for n in self.vault.staged() if n.status in ("staged", "held") and (n.id == ref or n.id.endswith(ref))]
        if not hits:
            raise ValueError(f"no staged note with the id {ref!r} (pending, with no id, lists them)")
        if len(hits) > 1:
            raise ValueError(f"{ref!r} names {len(hits)} staged notes; use the full id")
        n = hits[0]
        if n.partition not in self.read_scope:
            raise PermissionError(f"SCOPE WALL: agent '{self.agent}' may not read partition '{n.partition}'. "
                                  f"Read scope: {', '.join(self.read_scope)}")
        out = {"id": n.id, "title": n.title, "label": "staged · not yet Memory",
               "provenance": {"author": n.author, "source": n.source, "written": desk.local(n.written)},
               "partition": n.partition, "store": n.store, "tags": n.tags or ""}
        if n.extra.get("contact"):
            out["contact"] = n.extra["contact"]
        if n.taint or n.status == "held":
            alerts = sorted((x for x in self.vault.staged() if x.author == "sentinel" and n.source
                             and (x.source or "").split(":", 1)[-1] == n.source), key=lambda x: x.written or "")
            alert = alerts[-1].id if alerts else None
            out.update({"label": "held by Sentinel · not yet Memory", "body": None, "held": n.taint or n.status,
                        "alert": alert,
                        "note": "Sentinel is holding this note (%s); its body is not served. The person reads it at their "
                                "own terminal (magnemo show %s) and clears or drops it." % (n.taint or "held", n.id[-8:])})
        else:
            out["body"] = n.body
            out["note"] = ("This is a staged note, not Memory: nobody has kept it. Use it as what you proposed, and do "
                           "not say it is remembered until the person keeps it.")
        text = json.dumps(out, indent=1)
        foresight.log_cost(self.vault, "pending", len(text.encode("utf-8")),
                           {"via": "mcp", "id": n.id, "agent": self.agent, "held": bool(n.taint)})
        return text

    def t_keep(self, a):
        if str(a.get("note") or "").strip().lower() == "all":
            return self.keep_all()
        n = self._staged_note(a.get("note"))
        if n.taint:
            return self.held_note_words(n)
        cap = self.chat_cap()
        if self.chat_keeps_today() >= cap:
            return ("Not kept: %d notes were kept by a yes in the chat today, the most a day allows (chat_keeps_per_day; "
                    "the day is this computer's, and it resets at local midnight). This one waits; after midnight it can "
                    "be kept the same way, or the person gives a verified yes at their own terminal (magnemo yes %s)."
                    % (cap, n.id[-8:]))
        who = self._keyholder()
        self.gov.promote(n.id, who, "approved in the chat", ran_by="mcp:" + self.agent, answered_by=self.chat_label())
        by = self.client.get("name") or "your agent"
        return f"Kept. Written by {n.author}, your yes in the chat ({by}). \u201c{n.title}\u201d is Memory now."

    def keep_all(self) -> str:
        """The person's "keep all": each waiting note kept on its own ledger line; held notes stay held; the cap holds."""
        notes = self.waiting()
        if not notes:
            return "Nothing waits for a keep. 0 waiting · 0 held."
        before = desk.count_line(notes)
        lines, kept = [], 0
        for n in notes:
            if desk.is_held(n):                           # a held note is counted as held, and stays held
                lines.append(self.held_note_words(n) if n.taint else "Not kept: %s is held at the door." % n.id[-8:])
                continue
            lines.append(self.t_keep({"note": n.id}))
            kept += lines[-1].startswith("Kept.")
        w, h = desk.counts(notes)
        head = "%s: kept %d of the %d waiting." % (before, kept, w)
        if kept < w:
            head += " %d still waiting." % (w - kept)
        if h:
            head += " %d held by Sentinel, not kept." % h
        return head + "\n" + "\n".join(lines)

    def t_drop(self, a):
        n = self._staged_note(a.get("note"))
        reason = (a.get("reason") or "").strip() or "declined in the chat"
        self.gov.reject(n.id, self._keyholder(), reason, ran_by="mcp:" + self.agent, answered_by=self.chat_label())
        return f"Not kept. \u201c{n.title}\u201d is set aside as rejected, with your reason; it will not become Memory."

    # ---------------- the client, and the one question at a pause ----------------
    def client_label(self) -> str:
        name = re.sub(r"[^\w .@/+-]", "", str(self.client.get("name", "")))[:60].strip() or "unknown client"
        ver = re.sub(r"[^\w .+-]", "", str(self.client.get("version", "")))[:30].strip()
        return (name + " " + ver).strip()

    def batch_ask(self) -> dict:
        """P-106 addendum A: at a pause (handoff), ask the person once about every note still waiting, where the client
        can draw a question. Returns {"asked", "kept"}. Keep all promotes each note on its own ledger line; Pick, Later,
        a dismissed question or no answer leave every note staged. Nothing here blocks the work: the wait is bounded and
        the question is withdrawn when it ends."""
        free = [n for n in self.waiting() if not desk.is_held(n)]
        if not free:
            return {"asked": "not asked: nothing waits", "kept": 0}
        if (env("ASK", "") or "").strip().lower() in ("off", "0", "no", "false"):
            return {"asked": "not asked: MAGNEMO_ASK is off", "kept": 0}
        if not self.can_ask():
            return {"asked": "not asked: this client cannot draw a question; say the line at the end of your turn", "kept": 0}
        shown = free[:8]
        message = (batch_line(len(free)) + "\n\n" + "\n".join("- %s (%s)" % (n.title[:120], n.author) for n in shown)
                   + ("\n- and %d more" % (len(free) - len(shown)) if len(free) > len(shown) else ""))
        try:
            seconds = float(env("ASK_SECONDS", "") or ASK_SECONDS)
        except ValueError:
            seconds = ASK_SECONDS
        result, took, why = self.ask("elicitation/create", {"mode": "form", "message": message, "requestedSchema": BATCH_SCHEMA}, seconds)
        if result is None:
            return {"asked": "asked; no answer (%s): left for later" % why, "kept": 0}
        action = str(result.get("action", "")).lower()
        content = result.get("content") if isinstance(result.get("content"), dict) else {}
        answer = str(content.get("answer", "Later" if action == "accept" else "")).strip().lower()
        if took < TOO_FAST_S and action != "accept":       # a client with nobody at it lets go at once: later, not an answer
            return {"asked": "asked; nobody was there (%s in %d ms): left for later" % (action or "no action", int(took * 1000)), "kept": 0}
        if took < TOO_FAST_S:                              # faster than a person reads: a harness answering in code
            try:
                self.gov.ledger.record("judgment.refused", "refused", self.agent, ",".join(n.id for n in free)[:2000],
                                       "the batch question was answered in %d ms: faster than a person can read it" % int(took * 1000),
                                       **{"class": "yes" if answer == "keep all" else "catch", "door": "dialog", "catch": "dialog",
                                          "answered_by": "refused:too-fast", "client": self.client_label(), "ms": int(took * 1000),
                                          "action": action, "batch": len(free)})
            except Exception:
                pass
            return {"asked": "refused: answered too fast to be a person (%d ms); nothing kept" % int(took * 1000), "kept": 0}
        if action == "accept" and answer == "keep all":
            who, label, kept = self._keyholder(), "elicitation:" + self.client_label(), 0
            for n in free:
                self.gov.promote(n.id, who, "kept in the chat (keep all)", ran_by="mcp:" + self.agent, answered_by=label)
                kept += 1
            return {"asked": "keep all", "kept": kept}
        if action == "accept" and answer == "pick":
            return {"asked": "pick: ask the person in the chat which to keep, then keep those", "kept": 0}
        return {"asked": "later: every note stays staged", "kept": 0}

    # ---------------- bootpack ----------------
    def t_bootpack(self, a):
        cls = a.get("class") or "worker"
        if cls not in CLASSES:
            raise ValueError(f"unknown class: {cls!r} (worker|partner)")
        scope = a.get("scope")
        parts = self._gate_scope(scope, "boot on")
        if scope is None and set(parts) != set(self.vault.partitions):
            if len(parts) == 1:
                scope = parts[0]
            else:
                raise ValueError(f"this agent's read scope is {','.join(parts)}; "
                                 "name one partition as scope")
        text = bootpack.generate(self.vault, cls, scope, actor=self.agent)
        foresight.log_cost(self.vault, "bootpack", len(text.encode("utf-8")),
                           {"via": "mcp", "class": cls, "scope": scope or "all",
                            "agent": self.agent, "to": "mcp"})
        return text

    # ---------------- handoff ----------------
    def t_handoff(self, a):
        if "usage" not in a or not a.get("trigger"):
            raise ValueError("handoff requires usage (0-100) and trigger "
                             f"({'|'.join(TRIGGERS)})")
        cut = (a.get("cut") or "").strip()
        e = handoff.record(self.vault, a["usage"], a["trigger"], cut,
                           actor=self.agent, source=f"mcp/handoff/{a['trigger']}")
        foresight.log_cost(self.vault, "handoff", len(json.dumps(e).encode("utf-8")),
                           {"via": "mcp", "agent": self.agent, "note_id": e["note_id"],
                            "usage_pct": e["usage_pct"], "trigger": e["trigger"]})
        asked = self.batch_ask()                         # P-106 addendum A: the pause is where the person is asked, once
        left = desk.counts(self.waiting())[0]
        return json.dumps({
            "recorded": e, "telemetry": "_ledger/handoffs.jsonl (append-only)",
            "staged_note": f"_staging/{e['note_id']}.md",
            "pending": left, "asked": asked["asked"], "kept": asked["kept"],
            "say": batch_line(left) if left else "",
            "note": "The next bootpack inherits this boundary (LAST HANDOFF section)."
                    + (" Say the line once; later, or no answer, leaves them staged." if left else ""),
        }, indent=1)


# ---------------- deterministic helpers (no clock, no RNG, no model) ----------------
DUP_TAG = "dup-candidate"
DUP_THRESHOLD = 0.6   # trigram-Jaccard; above this the note is flagged as a near-duplicate


def nearest_duplicate(title: str, body: str, partition: str, vault) -> dict | None:
    """Pattern separation: the most similar existing note (canon in the same
    partition, or any staged note) above DUP_THRESHOLD. Uses the KAIROS
    trigram machinery — same algorithm that feeds the novelty component."""
    mine = kairos.trigrams(title + " " + body)
    best = None
    pool = [n for n in vault.canonical(partition)] + \
           [n for n in vault.staged() if n.status == "staged"]
    for c in pool:
        sim = kairos._jaccard(mine, kairos.trigrams(c.title + " " + c.body))
        if sim >= DUP_THRESHOLD and (best is None or sim > best["sim"]):
            best = {"id": c.id, "sim": sim, "status": c.status}
    return best


def pointer(r: dict) -> str:
    """mn:// pointer: a stable address, not a payload."""
    return f"mn://{r['partition']}/{r['store']}/{r['id']}"


def select_rendition(results: list, budget: int) -> tuple:
    """Fit the result set into `budget` bytes, deterministically:
      1. 'snippet'  — pointer + title + score + snippet, all results
      2. 'snippet'  — drop lowest-ranked results until it fits
      3. 'pointer'  — pointers only (id/title/score/yield), dropping from the tail if needed
    Returns (rendered, rendition, truncated)."""
    def snip(r):
        d = {"pointer": pointer(r), "id": r["id"], "title": r["title"],
             "score": r["score"], "yield": r["yield"], "snippet": r["snippet"]}
        if r.get("taint"):
            d["taint"] = r["taint"]
        return d

    def ptr(r):
        d = {"pointer": pointer(r), "id": r["id"], "title": r["title"],
             "score": r["score"], "yield": r["yield"]}
        if r.get("taint"):
            d["taint"] = r["taint"]
        return d

    def size(items):
        return len(json.dumps(items, indent=1).encode("utf-8"))

    full = [snip(r) for r in results]
    if size(full) <= budget:
        return full, "snippet", False
    for cut in range(len(full) - 1, 0, -1):
        if size(full[:cut]) <= budget:
            return full[:cut], "snippet", True
    ptrs = [ptr(r) for r in results]
    for cut in range(len(ptrs), 0, -1):
        if size(ptrs[:cut]) <= budget:
            return ptrs[:cut], "pointer", True
    return [], "pointer", True


def main():
    os.environ["MAGNEMO_MCP_SESSION"] = str(os.getpid())      # a command started from inside this session is not a person's yes
    MemoryServer().run()


if __name__ == "__main__":
    main()
