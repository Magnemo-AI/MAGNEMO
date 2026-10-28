# Installing Magnemo (for an agent doing the install)

Magnemo is an MCP server for memory. It runs on this machine, imports no network module, and keeps memory as plain
markdown files in a folder the user owns. Needs Python 3.11 or newer.

1. Install the engine: `pip install magnemo` (or `uv tool install magnemo` if pip cannot find it). This gives the
   `magnemo` command and the `magnemo-mcp` server. `uvx magnemo-mcp` also works without a prior install.
2. Make a vault — ask the user which folder, or use `./vault` in the project: `magnemo init ./vault`.
3. Register the server with the client. Every client takes the same stdio server:
   command `uvx`, args `["magnemo-mcp"]`, env `MAGNEMO_VAULT` = the absolute path of that vault folder.
   The README's "Install in your client" section has the exact block for Claude Code, Claude Desktop, Cursor, VS Code,
   Windsurf, Cline, Continue, Gemini CLI, Codex CLI and Zed. For Cline: `cline_mcp_settings.json`, the `mcpServers`
   block from the README, `disabled: false`.
   `magnemo mount` writes the server's absolute path, and a short block in `CLAUDE.md` (Claude Code) or
   `.cursor/rules/magnemo.mdc` (Cursor) saying this project's Memory is MAGNEMO; `magnemo unmount` takes both out.
4. Verify: `magnemo doctor` must end in `0 fail`. It checks Python, the vault, the config, the ledger and the mount.
5. Tell the user: remembering means proposing. What you write with the `stage` tool waits in the vault's `_staging/`
   until they say keep (`pending` with an id reads one back whole). Never
   stop to ask while you work: `stage` returns at once. At the end of your turn, if `pending` lists notes, say its one
   line ("N notes staged since you left. keep all / pick / later."); when they say keep, call `keep` (the record marks
   that yes unverified). The approval is never yours to give: the agent drafts and carries the person's yes, the person
   keeps.

No API key, no account, no token. The four verbs are `retrieve`, `stage`, `bootpack`, `handoff`; `keep` and `drop`
carry the person's yes or no; `pending` lists what waits.
