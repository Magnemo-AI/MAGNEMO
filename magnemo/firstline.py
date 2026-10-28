"""magnemo.firstline — the sign on the door (P-106 addendum B).

A new session reads one file before anything else: Claude Code reads `CLAUDE.md`, Cursor reads its rules. Unless that
file says where this project's memory is, the agent answers "what do you remember" from somewhere else (the Stranger
Run's D1). `magnemo mount` writes a short block into it; `magnemo unmount` takes it out. The block sits between fenced
markers, so writing it twice changes nothing and removing it leaves every other line as it was.

Claude Desktop reads no project file first; the same words are in the manual for the person to put where it reads
instructions.
"""
from __future__ import annotations
import os

FIRST_LINE = ("This project's Memory is MAGNEMO. At the start of a session call `bootpack`. Before answering anything "
              "about this project, call `retrieve`. Each time you finish a step or make a decision, `stage` it right "
              "then, unasked — one note per step, after a restart too. Remembering means proposing; the person's keep "
              "makes it Memory. Never stop to ask; at the end of your turn say `pending`'s line.")
BOOT_LINE = ("This project's Memory is MAGNEMO: call `retrieve` before answering anything about it; each time you finish "
             "a step or make a decision, `stage` it right then, unasked — one note per step, after a restart too "
             "(remembering means proposing; the person's keep makes it Memory); never stop to ask.")

BEGIN = "<!-- MAGNEMO:BEGIN · written by `magnemo mount`; `magnemo unmount` removes it -->"
END = "<!-- MAGNEMO:END -->"
BLOCK = BEGIN + "\n" + FIRST_LINE + "\n" + END + "\n"
CURSOR_RULE = ("---\ndescription: This project's Memory is MAGNEMO\nalwaysApply: true\n---\n" + BLOCK)


def target_for(mount_file: str) -> tuple:
    """(client, path) of the file the client reads first, for the MCP config `mount` wrote; path None when the client
    reads no such file (Claude Desktop, or a config this does not know)."""
    mf = os.path.abspath(mount_file)
    folder, name = os.path.dirname(mf), os.path.basename(mf)
    if name == "mcp.json" and os.path.basename(folder) == ".cursor":
        return "Cursor", os.path.join(folder, "rules", "magnemo.mdc")
    if name == ".mcp.json":
        return "Claude Code", os.path.join(folder, "CLAUDE.md")
    return "", None


def _strip(text: str) -> str:
    """The text with the block taken out (and the blank line `write` put before it)."""
    a = text.find(BEGIN)
    if a < 0:
        return text
    b = text.find(END, a)
    b = len(text) if b < 0 else b + len(END)
    if text[b:b + 1] == "\n":
        b += 1
    head = text[:a]
    if head.endswith("\n\n"):
        head = head[:-1]
    return head + text[b:]


def has_block(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            t = f.read()
    except OSError:
        return False
    return BEGIN in t and END in t and FIRST_LINE in t


def has_old_block(path: str) -> bool:
    """The markers are there and the words are an older first line's."""
    try:
        with open(path, encoding="utf-8") as f:
            t = f.read()
    except OSError:
        return False
    return BEGIN in t and FIRST_LINE not in t


def write(path: str) -> str:
    """Write the block into `path`: 'written', 'updated' (an older block replaced) or 'already there'."""
    cursor = path.endswith(".mdc")
    old = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if has_block(path):
        return "already there"
    rest = _strip(old)
    if cursor and not rest.strip():
        new = CURSOR_RULE
    else:
        new = (rest.rstrip("\n") + "\n\n" if rest.strip() else "") + BLOCK
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return "updated" if BEGIN in old else "written"


def remove(path: str) -> str:
    """Take the block out of `path`: 'removed', 'removed the file' (nothing else was in it) or 'not there'."""
    if not os.path.isfile(path):
        return "not there"
    with open(path, encoding="utf-8") as f:
        old = f.read()
    if BEGIN not in old:
        return "not there"
    rest = _strip(old)
    if not rest.strip() or (path.endswith(".mdc") and rest.strip() == CURSOR_RULE.replace(BLOCK, "").strip()):
        os.remove(path)
        return "removed the file"
    with open(path, "w", encoding="utf-8") as f:
        f.write(rest)
    return "removed"
