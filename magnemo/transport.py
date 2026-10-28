"""magnemo.transport — stdio JSON-RPC plumbing for the MCP server (zero deps).

Speaks Model Context Protocol over stdin/stdout: newline-delimited JSON-RPC 2.0.
Declares NO tools of its own — `magnemo.mcp.MemoryServer` is the one server and
the only tool surface. Least privilege is enforced here: only tools DECLARED by
`tools_spec()` are dispatchable; a private or inherited method never becomes a
tool by accident.

Configuration (env):
  MAGNEMO_VAULT       path to the vault root                 (required)
  MAGNEMO_AGENT       calling agent's identity, e.g. "ops-agent"   (default "agent")
  MAGNEMO_PARTITIONS  comma list this agent may WRITE to     (default: all)
"""
from __future__ import annotations
import sys, os, json, traceback, time, threading, queue, collections
from .vault import Vault, PARTITIONS
from .governance import Governance
from .search import Index
from .config import env
from . import __version__

PROTOCOL_FALLBACK = "2025-06-18"
# The protocol revisions this server speaks, newest first. A client that asks for one of them gets it; a client that
# asks for any other (a newer one) is answered with the newest of these, and decides for itself, as the protocol says.
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "magnemo", "title": "Magnemo — governed memory for AI agents", "version": __version__}


class Server:
    def __init__(self):
        root = env("VAULT")
        if not root:
            sys.stderr.write("MAGNEMO_VAULT env var is required\n")
            sys.exit(2)
        self.vault = Vault(root)
        if not self.vault.exists():
            self.vault.init()
        self.gov = Governance(self.vault)
        self.index = Index(self.vault)
        self.agent = env("AGENT", "agent")
        self.client, self.client_caps = {}, {}           # who connected and what it said it can do (initialize)
        self._inbox, self._later, self._asked, self._calling = None, collections.deque(), 0, None
        wp = env("PARTITIONS", ",".join(self.vault.partitions))
        self.write_partitions = self.vault.resolve_scope(wp.split(",")) or tuple(p.strip() for p in wp.split(",") if p.strip())
        # KAIROS: report review-queue depth at session start (stderr — never
        # pollutes the JSON-RPC channel on stdout).
        from . import desk                               # P-106 addendum C · ONE COUNT
        sys.stderr.write(f"[magnemo] review queue: {desk.count_line(desk.waiting(self.vault))}\n")

    def tools_spec(self) -> list:
        """The declared tool surface. The transport declares nothing; the server does."""
        return []

    # ---------------- JSON-RPC plumbing ----------------
    def handle(self, msg: dict):
        method = msg.get("method", "")
        mid = msg.get("id")
        if method == "initialize":
            p = msg.get("params") or {}
            client_ver = p.get("protocolVersion", PROTOCOL_FALLBACK)
            self.client = p.get("clientInfo") if isinstance(p.get("clientInfo"), dict) else {}
            self.client_caps = p.get("capabilities") if isinstance(p.get("capabilities"), dict) else {}
            self._connected(self.client)
            return self._result(mid, {
                "protocolVersion": client_ver if client_ver in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            })
        if method in ("notifications/initialized", "initialized"):
            return None  # notification: no response
        if method == "ping":
            return self._result(mid, {})
        if method == "tools/list":
            return self._result(mid, {"tools": self.tools_spec()})
        if method == "tools/call":
            p = msg.get("params") or {}
            name = p.get("name", "")
            name = getattr(self, "TOOL_ALIASES", {}).get(name, name)       # P-106 v3: approve/reject are keep/drop's other names
            args = p.get("arguments") or {}
            # Least privilege: only tools DECLARED by tools_spec() are callable.
            declared = {t["name"] for t in self.tools_spec()}
            fn = getattr(self, "t_" + name, None) if name in declared else None
            if fn is None:
                return self._error(mid, -32601, f"unknown tool: {name}")
            self._calling = mid
            try:
                text = fn(args)
                return self._result(mid, {"content": [{"type": "text", "text": text}],
                                          "isError": False})
            except Exception as e:  # tool errors are results, not protocol errors
                return self._result(mid, {"content": [{"type": "text",
                                          "text": f"ERROR: {e}"}], "isError": True})
        if mid is not None:
            return self._error(mid, -32601, f"unknown method: {method}")
        return None

    def _connected(self, client: dict):
        """P-74: one line per MCP session start, so `doctor` can tell a mounted server from one that never connected.
        Never raises into the protocol."""
        try:
            from .vault import now_iso
            d = os.path.join(self.vault.root, "_ledger")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "connections.jsonl"), "a") as f:
                f.write(json.dumps({"ts": now_iso(), "agent": self.agent, "client": str(client.get("name", ""))[:80],
                                    "client_version": str(client.get("version", ""))[:40], "server": __version__}) + "\n")
        except Exception:
            pass

    @staticmethod
    def _result(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    @staticmethod
    def _error(mid, code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    # ---------------- a question to the client (a server-to-client request), and the loop that leaves room for one
    def can_ask(self) -> bool:
        """True when the client said at `initialize` that it can put a form to its user (the elicitation capability,
        form mode: `{}` and `{"form": {}}` both mean it), and there is a channel to ask on."""
        e = self.client_caps.get("elicitation")
        return self._inbox is not None and isinstance(e, dict) and (not e or "form" in e)

    def _send(self, msg: dict):
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    def ask(self, method: str, params: dict, timeout: float):
        """Send one request to the client and wait for its answer: (result or None, seconds it took, why not).
        While it waits the server still answers a ping; any other message is kept and handled after. The wait ends
        early if the client cancels the tool call this question belongs to. A question nobody answered is withdrawn."""
        if self._inbox is None:
            return None, 0.0, "no channel"
        self._asked += 1
        rid = "magnemo-%d" % self._asked
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        t0, why = time.monotonic(), "timeout"
        while True:
            left = timeout - (time.monotonic() - t0)
            if left <= 0:
                break
            try:
                item = self._inbox.get(timeout=left)
            except queue.Empty:
                break
            if item is None:                                # the client went away
                self._inbox.put(None)
                why = "closed"
                break
            msg, arrived = item
            if msg.get("id") == rid and "method" not in msg:
                if "error" in msg:
                    return None, arrived - t0, "error: %s" % str((msg["error"] or {}).get("message", ""))[:120]
                return (msg.get("result") if isinstance(msg.get("result"), dict) else {}), arrived - t0, ""
            if msg.get("method") == "ping":
                self._send(self._result(msg.get("id"), {}))
            elif msg.get("method") == "notifications/cancelled" and (msg.get("params") or {}).get("requestId") == self._calling:
                why = "cancelled"
                break
            else:
                self._later.append(msg)
        self._send({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": rid, "reason": why}})
        return None, time.monotonic() - t0, why

    def _read(self):
        """The reader: every line the client sends, with the moment it arrived. Runs beside the loop so the loop can
        wait for an answer with a limit, on any platform."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict):
                self._inbox.put((msg, time.monotonic()))
        self._inbox.put(None)

    def run(self):
        self._inbox = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()
        while True:
            if self._later:
                msg = self._later.popleft()
            else:
                item = self._inbox.get()
                if item is None:
                    break
                msg = item[0]
            if "method" not in msg:                         # an answer to a question already given up on: nothing to do
                continue
            try:
                resp = self.handle(msg)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                resp = self._error(msg.get("id"), -32603, "internal error")
            if resp is not None:
                self._send(resp)
