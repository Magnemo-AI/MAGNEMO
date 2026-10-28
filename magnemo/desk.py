"""magnemo.desk — what a person reads about the queue (P-106 addendum C).

ONE COUNT. The boot pack, `pending`'s header and `keep all` say the same two numbers from the same list: "N waiting ·
M held". The list is the notes a person is asked about: staged, not Sentinel's own alert notes, not handoff records.
A held note is one Sentinel holds (a secret's redaction, an injection's taint); it is counted once, as held, never as
waiting too. Handoffs and alerts are never counted as notes anywhere a person reads.

LOCAL TIME. Stamps stay UTC in the files and the ledger. Every line a person reads shows the time of the computer the
vault is on, with its offset: "Oct 27, 10:12 PM −07:00".
"""
from __future__ import annotations
import calendar, time

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def is_held(n) -> bool:
    return bool(n.taint) or n.status == "held"


def waiting(vault, scope: str | None = None) -> list:
    """The notes a person is asked about, in the order they were written."""
    out = []
    for n in vault.staged():
        tags = {t.strip() for t in (n.tags or "").split(",")}
        if n.status in ("staged", "held") and n.author != "sentinel" and "handoff" not in tags \
                and (scope is None or n.partition == scope):
            out.append(n)
    return sorted(out, key=lambda n: (n.written or "", n.id))


def counts(notes) -> tuple:
    """(waiting, held) over one list: each note is one or the other."""
    held = sum(1 for n in notes if is_held(n))
    return len(notes) - held, held


def count_line(notes) -> str:
    w, h = counts(notes)
    return f"{w} waiting · {h} held"


def _epoch(ts):
    try:
        return calendar.timegm(time.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return None


def local(ts) -> str:
    """A UTC stamp (…Z) as a person reads it: 'Oct 27, 10:12 PM −07:00'. Anything that is not a stamp comes back as is."""
    t = _epoch(ts)
    if t is None:
        return str(ts)
    lt = time.localtime(t)
    off = lt.tm_gmtoff if lt.tm_gmtoff is not None else -time.timezone
    sign, off = ("−" if off < 0 else "+"), abs(int(off))
    return "%s %d, %d:%02d %s %s%02d:%02d" % (_MONTHS[lt.tm_mon - 1], lt.tm_mday, lt.tm_hour % 12 or 12, lt.tm_min,
                                             "AM" if lt.tm_hour < 12 else "PM", sign, off // 3600, off % 3600 // 60)


def local_day(ts: str | None = None) -> str:
    """YYYY-MM-DD in this computer's local time, for a ledger stamp (UTC, ...Z) or for now."""
    if ts is None:
        return time.strftime("%Y-%m-%d", time.localtime())
    t = _epoch(ts)
    return time.strftime("%Y-%m-%d", time.localtime(t)) if t is not None else str(ts)[:10]
