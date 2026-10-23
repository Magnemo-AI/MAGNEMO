"""P-104 · THE WORTHY YES: a yes is only for something proposed as Memory.

A report, a sheet, a standup, a watch note, an order: a seat's RECEIPT. Through the inbox door it files itself, with
`status: receipt`, signed by the seat that wrote it, on the record and searchable by `magnemo receipts`. It asks nobody
anything: "waiting for you" shows Memory proposals only, and `retrieve` never serves a receipt (it serves canon).

Which drop is a receipt is read from the drop: a `kind:` line in its first lines says so outright (`kind: memory`, or a
`propose:` line, keeps it a proposal); otherwise its file name, which the seats already write to say what it is."""
import re

KINDS = ("report", "sheet", "standup", "watch", "order")
_BY_NAME = (
    ("watch", re.compile(r"^watch-")),
    ("order", re.compile(r"^(withdrawn-)?order-")),
    ("standup", re.compile(r"standup")),
    ("sheet", re.compile(r"(^|[-_])sheet([-_.]|$)|^field-(warm|queue|campaign)|^desk-")),
    ("report", re.compile(r"(^|[-_])reports?([-_.]|$)|^cc-to-|^field-field-|(^|[-_])receipts?[-_]")),
)
_KIND_LINE = re.compile(r"(?im)^\s*kind:\s*([a-z]+)\s*$")
_PROPOSE = re.compile(r"(?im)^\s*propose:")


def kind_of(name: str, text: str = "") -> str:
    """'report' · 'sheet' · 'standup' · 'watch' · 'order' for a receipt; '' for a Memory proposal."""
    head = "\n".join((text or "").split("\n")[:30])
    if _PROPOSE.search(head):
        return ""
    m = _KIND_LINE.search(head)
    if m:
        k = m.group(1).lower()
        return k if k in KINDS else ""
    n = (name or "").lower()
    if n.endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf")):
        return ""                                   # an upload asks the rights question; not a receipt
    return next((k for k, rx in _BY_NAME if rx.search(n)), "")


def drop_name(note) -> str:
    """The file a note came through the inbox door as ('' when it did not come by the door)."""
    m = re.match(r"inbox:(\S+)", note.source or "")
    return m.group(1) if m else ""


def listed(vault, seat: str = "") -> list:
    """Receipts, newest first; one seat's when `seat` is named."""
    rows = [n for n in vault.staged() if n.status == "receipt" and (not seat or n.author.lower() == seat.lower())]
    return sorted(rows, key=lambda n: (n.written or "", n.id), reverse=True)


def settled_alerts(vault, cleared: set = frozenset()) -> list:
    """Sentinel alerts still waiting whose note is no longer flagged (cleared before, or in this run): the question the
    alert asked has been answered. An alert whose note still carries its flag, or whose note is not found, stays."""
    staged = vault.staged()
    out = []
    for a in staged:
        if a.author != "sentinel" or a.status != "staged":
            continue
        key = " ".join((a.source or "").split()[:2])
        if not (key.startswith("inbox:") and "sha256:" in key):
            continue
        subj = [n for n in staged if n.author != "sentinel" and (n.source or "").startswith(key + " ")]
        if subj and all(not n.taint or n.id in cleared for n in subj):
            out.append(a)
    return out


def candidates(vault, seat_map: dict, also_clean: set = frozenset()) -> list:
    """Waiting notes that rule 1 makes receipts: [(note, kind)]. A note by the door from a seat on the map, whose drop
    is a receipt kind, with no flag on it (or a flag in `also_clean`, the false ones cleared in the same run).
    Sentinel's own alerts are not receipts; a held note stays held."""
    seats = {s.lower() for s in (seat_map or {})}
    out = []
    for n in vault.staged():
        if n.status != "staged" or n.author == "sentinel" or n.author.lower() not in seats:
            continue
        fn = drop_name(n)
        if not fn or (n.taint and n.id not in also_clean):
            continue
        k = kind_of(fn, n.body)
        if k:
            out.append((n, k))
    return out
