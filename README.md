<h1 align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Magnemo-AI/MAGNEMO/main/docs/assets/lockup-light.svg"><img alt="MAGNEMO" src="https://raw.githubusercontent.com/Magnemo-AI/MAGNEMO/main/docs/assets/lockup-dark.svg" width="440"></picture></h1>
**The Memory MCP. Your AI remembers. You keep what matters.**

MAGNEMO is Memory for your AI, kept on your computer in plain files. Your AI writes down what it learns as it works; nothing becomes Memory until you approve it, and every Memory shows who wrote it and who approved it.

Your agent writes one line down and keeps working. Say keep, and it is Memory.

[![PyPI](https://img.shields.io/pypi/v/magnemo)](https://pypi.org/project/magnemo/)
[![downloads](https://img.shields.io/pypi/dm/magnemo)](https://pypi.org/project/magnemo/)
[![tests](https://github.com/Magnemo-AI/magnemo/actions/workflows/test.yml/badge.svg)](https://github.com/Magnemo-AI/magnemo/actions/workflows/test.yml)
[![license](https://img.shields.io/pypi/l/magnemo)](LICENSE)
[![stars](https://img.shields.io/github/stars/Magnemo-AI/magnemo)](https://github.com/Magnemo-AI/magnemo/stargazers)
[![MCP registry](https://img.shields.io/badge/MCP_registry-ai.magnemo%2Fmagnemo-blue)](https://registry.modelcontextprotocol.io/?q=magnemo)

[Site](https://magnemo.ai) · [Manual](docs/MCP.md) · [Changelog](CHANGELOG.md) · [X @Magnemo_AI](https://x.com/Magnemo_AI) · [Known limits](KNOWN_LIMITS.md)

## Install in one paste
In three lines:

```bash
pip install MAGNEMO      # Python 3.11 or newer
magnemo init             # makes the vault: a folder of plain files
magnemo mount            # writes .mcp.json, the file Claude Code reads, and the first line in CLAUDE.md
```

Or let your agent do it. Open Claude Code in any of your project folders, and paste this. (Its `magnemo mount` step writes `.mcp.json`, the file Claude Code reads, and a short block in `CLAUDE.md` that tells every new session where this project's Memory is. In Cursor, Windsurf or another client, use the block for your client under "Install in your client".)

```text
Set up MAGNEMO in this project:
1. Install it: pip install MAGNEMO. It needs Python 3.11 or newer. If pip can't find it, install uv (curl -LsSf https://astral.sh/uv/install.sh | sh) and then run: uv tool install MAGNEMO
2. Initialize the vault: magnemo init
3. Register the MCP server: run magnemo mount — it adds MAGNEMO to this project's MCP config and keeps any servers already there.
4. Verify: run magnemo doctor and confirm everything passes.
5. Then ask me to restart you, so MAGNEMO's tools load, and to say this when you are back: "Look around this folder, tell me what this project is for, and stage that as the first note." Your agent never waits on you. When you want something kept, say keep.
If anything fails, show me what went wrong and fix it if you can.
```

Plant the seed: one paste, and your agent grows a Memory.

After the restart, say it: **Look around this folder, tell me what this project is for, and stage that as the first note.**
Your agent writes one line down and
keeps working. Say keep, and it is Memory. Then ask what it remembers.

## Works with
One server, the same in every client. Tested where it says so; the rest follow each client's own docs.

| Client | Tested | How |
|---|---|---|
| Claude Code | yes: Oct 26–28, 2026, Claude Code 2.1.309. Seven tools; the yes in the chat; `pending` reads a body. | `magnemo mount`, or `claude mcp add magnemo -e MAGNEMO_VAULT=/absolute/path/to/vault -- uvx magnemo-mcp` |
| Claude Desktop | untested end to end | the `uvx` block under "Install in your client", with absolute paths |
| Cursor | untested | the Add to Cursor link below, or `.cursor/mcp.json` |
| VS Code | untested | `.vscode/mcp.json` |
| Windsurf | untested | `~/.codeium/windsurf/mcp_config.json` |
| Cline | untested | `cline_mcp_settings.json` |
| Continue | untested | `~/.continue/config.yaml` |
| Gemini CLI | untested | `~/.gemini/settings.json` |
| Codex CLI | untested | `~/.codex/config.toml` |
| Zed | untested | `settings.json` → `context_servers` |

Each client's exact block is under "Install in your client".

## How it compares
Five questions, answered from each project's own docs (read Oct 12, 2026, checked again Oct 22; the pages are linked under the table).

| | MAGNEMO | Mem0 | Zep | Letta | Basic Memory |
|---|---|---|---|---|---|
| **Where the memory lives** | Plain markdown files in a folder on your computer | A hosted platform run by Mem0; open source: a local Qdrant store and a SQLite history file | Zep: a managed cloud service, or in your own VPC. Graphiti, its open-source engine: a graph database you run | Markdown files in a git repository that belongs to the agent: hosted by Letta, or on your device in local mode | Markdown files on your disk with a local SQLite index; an optional cloud |
| **Who approves a write** | You. An agent's write waits in staging until your yes | An LLM extracts facts from the messages and stores them; their docs describe no approval step | Messages are ingested into the graph as they arrive; their docs describe no approval step | The agent updates its own memory; the background review "does not ask you for approval" | The assistant writes notes directly; the cloud has suggested edits that can be accepted or rejected |
| **Author and approver on every entry** | Both, in each file's header (`author`, `reviewed_by`) and in an append-only ledger | User, agent, app and run ids, timestamps, and a change history per memory; their docs name no approver field | When a fact was true and when it stopped, traced to its source episode; their docs name no approver field | Every memory edit is a git commit; their docs do not say what the commit records | Title, type, tags and dates; `author` is a field you may add; their docs name no approver field |
| **Network calls of its own** | None. No model call and no embedding call; `git push` to a backup, if you add one | OpenAI by default for the model and the embeddings; other providers are listed, Ollama among them | Zep is a cloud API. Graphiti defaults to OpenAI; local model servers are documented | Local mode keeps state on your device; inference goes to the provider you choose, which can be a local one | Runs locally; the default embeddings run on your machine with no API key |
| **What you can take back** | A no is kept with its reason; a replaced note is archived with a forward link; nothing deletes; the files are yours to edit | Delete, update, and a history per memory; export is on the hosted platform | Delete nodes, edges and episodes; a replaced fact is invalidated, not deleted | The git history of every memory edit; the files can be read and edited | Plain files you edit and can track with git; a delete tool; the cloud keeps every saved version |

**Where each of them is ahead.** Mem0 extracts memories for you, searches them by meaning, and has Python and JavaScript SDKs, a REST API and a hosted platform. Zep keeps a knowledge graph that knows when each fact was true, as a managed service with SDKs in three languages. Letta is a whole agent platform, with an SDK, a CLI and background agents that tend the memory. Basic Memory searches by keyword and by meaning with embeddings that run on your machine, links notes into a graph, and syncs through its cloud. MAGNEMO has none of that: its search is keyword search ([KNOWN_LIMITS.md](KNOWN_LIMITS.md)), there is no graph and no hosted service. What it has is the approval and the record.

Their pages: Mem0 [overview](https://docs.mem0.ai/open-source/overview), [platform and open source](https://docs.mem0.ai/platform/platform-vs-oss), [add](https://docs.mem0.ai/core-concepts/memory-operations/add), [history](https://docs.mem0.ai/api-reference/memory/history-memory), [quickstart](https://docs.mem0.ai/open-source/python-quickstart), [delete](https://docs.mem0.ai/core-concepts/memory-operations/delete), [export](https://docs.mem0.ai/platform/features/memory-export) · Zep [concepts](https://help.getzep.com/concepts), [facts](https://help.getzep.com/v3/facts.md), [security](https://help.getzep.com/v3/security-compliance.md), [deleting data](https://help.getzep.com/deleting-data-from-the-graph), [Graphiti](https://github.com/getzep/graphiti) · Letta [MemFS](https://docs.letta.com/concepts/memfs), [memory settings](https://docs.letta.com/configuration/memory), [local mode](https://docs.letta.com/self-hosting) · Basic Memory [README](https://github.com/basicmachines-co/basic-memory), [what it is](https://docs.basicmemory.com/start-here/what-is-basic-memory), [tools](https://docs.basicmemory.com/reference/mcp-tools-reference), [note format](https://docs.basicmemory.com/concepts/knowledge-format), [semantic search](https://docs.basicmemory.com/raw/concepts/semantic-search.md), [suggestions](https://docs.basicmemory.com/raw/cloud/comments-and-suggestions.md), [file history](https://docs.basicmemory.com/raw/cloud/file-history.md). A cell that is wrong or out of date: open an issue and it is fixed.

**Listed on** the [official MCP registry](https://registry.modelcontextprotocol.io/?q=magnemo) (`ai.magnemo/magnemo`) · [PyPI](https://pypi.org/project/magnemo/) · [mcpservers.org](https://mcpservers.org/servers/magnemo-ai/magnemo) · [Glama](https://glama.ai/mcp/servers/Magnemo-AI/magnemo) · [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers).
**Tested on** every push, on Python 3.9, 3.11 and 3.12: 370 tests, as of Oct 28, 2026 ([the runs](https://github.com/Magnemo-AI/magnemo/actions/workflows/test.yml)).

## What's new
- **0.6.11** · Oct 28, 2026 · `magnemo mount` writes the first line in CLAUDE.md, so every new session knows where this project's Memory is. `pending` reads a note nobody has kept yet.
- **0.6.10** · Oct 26, 2026 · Your agent never stops to ask. Say keep in the chat, and the record says how the yes was given.
- **0.6.9** · Oct 22, 2026 · A seat's report files itself as a receipt and asks nothing; a yes is for Memory. Sentinel reads a seat's quote as a quote.

Every release: [CHANGELOG.md](CHANGELOG.md).

**For builders.** MAGNEMO is an MCP server with four verbs — `retrieve`, `stage`,
`bootpack`, `handoff` — plus `keep`, `drop`, `pending`, and a CLI for your side: review, promote, reject.
It runs on your machine, in plain markdown files you own. The package imports no network
module (`magnemo doctor` scans for one on every run); the only traffic is `git push` to a
backup destination, if you add one. Every promotion is recorded with who wrote the entry,
the name given for the yes, when, and through which gate. Trust is computed from that
record, never asserted. It mounts beside any memory you already
run (a folder of notes, Obsidian, a RAG stack). Python 3.11+, zero dependencies,
Apache-2.0.

Fresh vault? THE CHARTER section will say it isn't promoted yet — that is the
governance speaking: MAGNEMO never fabricates canon. Stage a charter, review it,
promote it, and every boot thereafter serves it back verbatim.
(`magnemo` not found after install? pip's script folder isn't on PATH —
`python3 -m magnemo` always works.)

**Open beta — read [KNOWN_LIMITS.md](KNOWN_LIMITS.md) before trusting it with anything you can't lose.** Honest caveats, no fine print.

## Install in your client
One server, said ten ways. Every block below is the same thing: `uvx magnemo-mcp` with `MAGNEMO_VAULT` pointing at
the folder your Memory lives in (make one with `magnemo init ./vault`). Tested on this Mac where it says so;
the rest is from each client's own docs and marked untested — corrections welcome, open an issue.

**Claude Code** — tested: a Claude Code session mounts the server, lists the seven tools and calls them; a yes in the
chat keeps a note, and `pending` reads a body (last run Oct 28, 2026: Claude Code 2.1.309, the 0.6.11 server).
```bash
claude mcp add magnemo -e MAGNEMO_VAULT=/absolute/path/to/vault -- uvx magnemo-mcp
```
(`claude mcp list` shows `magnemo … ✔ Connected`. Add `-s project` to write it into the repo's `.mcp.json` for your team.)
Only have the desktop app? `claude` may not be a command in your shell. On a Mac the app keeps its own copy at
`~/Library/Application Support/Claude/claude-code/<version>/claude.app/Contents/MacOS/claude`; run that in place of `claude`.

**Claude Desktop** — untested end to end here. The server this block starts was run the way Claude Desktop starts it
(Oct 28, 2026, the 0.6.11 server). Claude Desktop → Settings → Developer → Edit Config, then
`claude_desktop_config.json`. Claude Desktop does not read your shell's PATH, so both paths are absolute: `which uvx`
prints the first.
```json
{
  "mcpServers": {
    "magnemo": {
      "command": "/absolute/path/to/uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault", "MAGNEMO_AGENT": "claude-desktop" }
    }
  }
}
```
Restart Claude Desktop after saving.

**Cursor** — untested here (not installed on this Mac); the link and the block follow Cursor's docs.
[![Add to Cursor](https://img.shields.io/badge/Cursor-Add_Magnemo-000000?style=flat-square)](cursor://anysphere.cursor-deeplink/mcp/install?name=magnemo&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJtYWduZW1vLW1jcCJdLCJlbnYiOnsiTUFHTkVNT19WQVVMVCI6Ii9hYnNvbHV0ZS9wYXRoL3RvL3ZhdWx0In19)
Or `~/.cursor/mcp.json` (or `.cursor/mcp.json` in the project):
```json
{
  "mcpServers": {
    "magnemo": {
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" }
    }
  }
}
```

**VS Code / Copilot** — untested here; per VS Code's docs.
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Magnemo-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](vscode:mcp/install?%7B%22name%22%3A%22magnemo%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22magnemo-mcp%22%5D%2C%22env%22%3A%7B%22MAGNEMO_VAULT%22%3A%22%2Fabsolute%2Fpath%2Fto%2Fvault%22%7D%7D)
Or `.vscode/mcp.json` in the workspace:
```json
{
  "servers": {
    "magnemo": {
      "type": "stdio",
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" }
    }
  }
}
```

**Windsurf** — untested; `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "magnemo": {
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" }
    }
  }
}
```

**Cline** — untested; Cline → MCP Servers → Configure → `cline_mcp_settings.json`:
```json
{
  "mcpServers": {
    "magnemo": {
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" },
      "disabled": false
    }
  }
}
```

**Continue** — untested; `~/.continue/config.yaml` (or a file in `.continue/mcpServers/`):
```yaml
mcpServers:
  - name: magnemo
    command: uvx
    args: ["magnemo-mcp"]
    env:
      MAGNEMO_VAULT: /absolute/path/to/vault
```

**Gemini CLI** — untested; `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "magnemo": {
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" }
    }
  }
}
```

**Codex CLI** — untested; `~/.codex/config.toml`:
```toml
[mcp_servers.magnemo]
command = "uvx"
args = ["magnemo-mcp"]
env = { MAGNEMO_VAULT = "/absolute/path/to/vault" }
```

**Zed** — untested; `settings.json` → `context_servers`:
```json
{
  "context_servers": {
    "magnemo": {
      "source": "custom",
      "command": "uvx",
      "args": ["magnemo-mcp"],
      "env": { "MAGNEMO_VAULT": "/absolute/path/to/vault" }
    }
  }
}
```

**After the install**, the loop is the same everywhere: your agent writes to staging, you review.
```bash
magnemo yes             # promote the top of the queue (yes <id-fragment> · yes --all)
magnemo no <id> --reason "…"   # reject one — the reason is required; rejections teach
magnemo review          # the interactive queue, when you want to read first
magnemo doctor          # python, vault, config, ledger, and the mount — scans the package for network modules too
```
Anything that speaks MCP over stdio mounts the same way. The remote door (ChatGPT and hosted clients) is on its way in 0.7.0.

## How it works
**The yes is checked: nothing becomes Memory without a yes, and the engine can tell a person's yes from an agent's; a yes in the chat counts, and the record says how it was given.**

MAGNEMO is Memory with a constitution: every fact carries provenance, every agent write waits in your review queue
before it becomes Memory, and every decision lands in a Trust Ledger.

Your agent gets four verbs and cannot keep a note on its own authority; it carries your yes, and the record says so.
Say yes in the chat and `keep` carries it, ledgered unverified; a click your client draws or a yes at your terminal is a verified one. [KNOWN_LIMITS.md](KNOWN_LIMITS.md) says what that does and does not stop; [docs/MCP.md](docs/MCP.md) has the clients it works in.

| Actor  | Door                | Can do |
|--------|---------------------|--------|
| Agents | MCP server (stdio)  | `retrieve` canonical memory · `stage` → **staging only, the one write tool** · `bootpack` on wake · `handoff` at the boundary · `keep` / `drop` carry your yes or no · `pending` lists what waits |
| You    | CLI + git (any editor)| review the queue · **promote / reject** · edit anything · own everything |

**Zero dependencies.** Pure Python standard library, 3.11 or newer. Nothing else to install, nothing to trust but this code.

## The vault
```
vault/
  dev/      knowledge/ playbooks/ decisions/ debt/        ← example: a dev team's partition
  ops/      knowledge/ playbooks/ clients/ decisions/ style/  ← example: an ops team's partition
  shared/   tickets/ changelog/                            ← interop bus (gated)
  _staging/   agent writes await review here
  _index/     machine-managed
  _ledger/    trust_ledger.jsonl — append-only, never forgets
```
Every note is markdown with provenance frontmatter (author, written, source,
status, reviewed_by, supersedes, strength). **Provenance is the file format.**

## Privacy
Your Memory lives on your computer, in plain files you can open. No network calls of its own. Add a backup remote and it pushes there, nowhere else.
The precise version: the package imports no network module, and `magnemo doctor` scans for one every time it runs. If you add a backup destination, the engine runs `git push` to it. The full page: https://magnemo.ai/privacy

## Guarantees (Phase 1 — Governed Recall)
- Through the MCP server, agent writes NEVER reach canonical stores directly — staging only, always.
- Search returns canonical (promoted) notes only. Staged notes are not searched. The boot pack shows staged material marked as staged: the titles of open threads and of the top staged notes, and the last handoff's cut line with a pointer to its note.
- Partition walls enforced per agent (`MAGNEMO_PARTITIONS`); cross-partition = DENIED.
- Supersession is explicit: old notes archive with a forward link. Nothing deletes.
- Rejections are kept and recorded — rejections teach.
- Every promote/reject lands in the append-only Trust Ledger with actor + reason.

## Tests
```bash
python -m unittest discover -s tests -v     # incl. full MCP round-trips (legacy + four-verb)
# or: pip install -e ".[test]" && pytest
```
The same suite runs on every push, on Python 3.9, 3.11 and 3.12: [the runs](https://github.com/Magnemo-AI/magnemo/actions/workflows/test.yml).

## Everything that shipped
Release by release, with the design notes that used to live here: [CHANGELOG.md](CHANGELOG.md).

— Silver Valley Technologies Inc. · Phase 1 of 3 · The memory that learns is
the memory that is governed.

---
`mcp-name: ai.magnemo/magnemo` · [Source](https://github.com/Magnemo-AI/magnemo) · [Security](SECURITY.md) · [Privacy](https://magnemo.ai/privacy)
