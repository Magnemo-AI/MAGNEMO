# KNOWN LIMITS — open beta (0.6.x)

Honesty is the product. These are the current edges, stated plainly. Every one
of them is a roadmap item, not a surprise left for you to find.

- **MAGNEMO never stops your agent to ask.** Notes wait in staging until you
  say keep; a yes in the chat counts, and the record says how it was given.
  `stage` asks nothing; the question comes at a pause (the end of the agent's
  turn, or a handoff), once, for everything that waits: keep all, pick, or
  later. Later, or no answer, blocks nothing and loses nothing.
- **A yes in the chat counts; the record says how it was given.** The agent
  cannot keep a note on its own authority: it carries your yes. You say yes in
  the chat, the agent calls `keep`, and the note is Memory. Over MCP the
  engine cannot tell your keyboard from the model's tool call, so the ledger
  writes that yes `chat-text:<client> · unverified`; a click your client draws
  or a terminal yes is a verified one. A model that misreads you, or words
  slipped into the conversation, can call `keep` too. That is why a yes in the
  chat counts half in the Trust Ledger's arithmetic, why at most 50 notes a day
  are kept that way (`chat_keeps_per_day` in `_config/magnemo.json`; the day is
  the local day of the computer the vault is on, reset at its midnight), and why a
  note Sentinel is holding is not kept by it: a hold needs a verified yes.
  `magnemo yes <id>` at your terminal on a note kept in the chat makes it
  verified, and the first yes stays on the record.
- **The terminal yes is checked.** `magnemo yes` (and `no`, `clear`, `promote`) requires an
  interactive terminal (a TTY on stdin) and a name in `trust.humans` — a
  keyholder: the vault's list of people whose yes counts; a name, not a
  password. It refuses with no TTY (an agent's tool call, a script, a pipe),
  with `MAGNEMO_AGENT` set, from inside an MCP session, or for a name not on
  the list; each refusal is a line in the ledger. It is a check on the hand,
  not a credential: a process that allocates its own TTY, clears
  `MAGNEMO_AGENT` and names a listed person passes — an agent with your shell
  and your terminal is still you.
- **The gate is on what is kept, not on what is written.** It stops a wrong
  thing from becoming memory without a person; it does not stop a wrong
  thing from being written. Reading the note before you say yes is the
  part no tool does for you.
- **The question at the pause is drawn by your client, not by MAGNEMO.** At a
  handoff the server asks the client to ask you (MCP elicitation) about the
  notes that wait, and takes the client's answer. The agent has no tool that answers it. A client set up
  to answer for you, by a hook or a harness, can: MAGNEMO refuses an answer
  that comes back in under 300 ms and logs it, and that catches only the
  crude case. Every yes says which surface it came through. Today the
  dialog has been seen in one client, Claude Code; `docs/MCP.md` has the
  table.
- **Beta software.** The engine runs its maker's company daily, but you are
  early. Expect rough edges in exactly the places this file names.
- **One client is tested.** Claude Code. Every other client's block in the
  README is written from that client's own docs and marked untested.
  `magnemo mount` writes `.mcp.json`, the file Claude Code reads, and the
  first line in `CLAUDE.md` (`--file .cursor/mcp.json` writes Cursor's rule);
  other clients take their config by hand. Claude Desktop reads no project
  file first, so the first line there is yours to put in.
- **Sentinel's S14 is a pattern, not a reader.** It labels what looks like
  an email address or a phone number at the stage door, and the chest asks
  once per remote before a labelled note goes there. A contact written another way ("jane at
  acme dot io"), a name, or an address on its own is not labelled, and so
  is not asked about. The inbox door and the Room do not run S14. Notes
  staged before 0.6.11 carry no label.
- **The record can lag the code within a turn.** An agent often writes a few
  steps' code at once and stages each step after it. The handoff closes the
  gap; a crash mid-turn loses what was not yet staged, as any crash does.
- **Local and single-machine.** The vault is plain markdown on one disk.
  Multi-machine continuity works the way git works — you sync the vault
  yourself (git is the tested path). There is no hosted sync service.
- **Keyword retrieval, not embeddings.** Search is walled BM25 over your
  vault. It is fast, deterministic, and auditable — and it will miss
  paraphrases that a semantic index would catch. The `Index.search()` seam
  exists so embedding retrieval can swap in behind the same wall later.
- **The review queue is a terminal.** `magnemo review` is a CLI. There is no
  web or app interface yet; viewers are windows, not foundations, and the
  markdown is readable in any editor today.
- **Trust math is young.** Autonomy levels are computed from a real
  append-only ledger, but the weights, half-lives, and thresholds are v1 and
  will be tuned. `promote-canon` and `publish` are hard-capped keyholder-only in
  code — that part is doctrine, not a tunable.
- **MCP over stdio only.** The server speaks stdio to local MCP clients
  (Claude Code, Claude Desktop, anything that speaks MCP). No HTTP/SSE
  transport yet.
- **Token counts are estimates.** Payload cost telemetry estimates tokens as
  bytes/4 (documented in the code). The seam accepts a real tokenizer later;
  the trend lines are honest, the absolute numbers are approximate.
- **Vault format may evolve before 1.0.** Notes are plain markdown with
  frontmatter, so your data is never trapped — but tooling-level migrations
  between beta versions may be needed. Breaking changes will be listed in the
  CHANGELOG with migration notes.
- **Python 3.11+ required.** Zero runtime dependencies, standard library
  only. Primary development and dogfood happen on macOS/Linux; Windows path
  handling is untested territory this release.

Found an edge not on this list? That is exactly the kind of receipt wanted here —
the beta channel at [magnemo.ai](https://magnemo.ai).
