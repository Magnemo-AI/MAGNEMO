"""THE DOOR ROUTES BY PREFIX (P-78). A shared inbox has many seats; each seat stages only its
own drops. `inbox.seats` in the vault's config names who owns which file names:

    "seats": {"cc": ["cc-report-*"], "marketing": ["marketing-*"], "boardroom-session": ["*"]}

A drop belongs to the seat whose matching glob is the most specific (the longest literal
start; the first declared wins a tie), so a catch-all `*` seat only gets what no one else
claims. With no `inbox.seats`, the door is as before: every drop stages under `--as`.

The map is written only through `set_seat` — a keyholder's word, ledgered as `inbox.seat`.
It touches `inbox.seats` and nothing else in the config."""
import fnmatch
import json
import os
import re

from .vault import Vault

SEAT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class SeatError(Exception):
    """Plain English, every time."""


def _literal(glob: str) -> int:
    n = 0
    for ch in glob:
        if ch in "*?[":
            break
        n += 1
    return n


def _globs(owned) -> list:
    return [owned] if isinstance(owned, str) else list(owned or [])


def seats(cfg: dict) -> dict:
    return (cfg.get("inbox") or {}).get("seats") or {}


def seat_of(seat_map: dict, name: str):
    """The seat that owns a file name, or None when no glob matches."""
    best, score = None, -1
    for seat, owned in seat_map.items():
        for g in _globs(owned):
            if fnmatch.fnmatch(name, g) and _literal(g) > score:
                best, score = seat, _literal(g)
    return best


def set_seat(v: Vault, seat: str, globs, by: str, reason: str, ran_by: str = "", remove: bool = False) -> dict:
    """Give a seat its prefixes (or take the seat off the map). A keyholder's word only."""
    from .config import config_path
    from .governance import TrustLedger
    from .room import is_human
    from . import guard
    if not is_human(v, by):
        raise SeatError(f"'seat' is a keyholder verb — '{by}' is not a keyholder (config trust.humans). "
                        "Who owns which drops is the keyholder's word.")
    seat = (seat or "").strip().lower()
    if not SEAT_NAME.match(seat):
        raise SeatError(f"'{seat}' is not a seat name: lowercase letters, digits and dashes.")
    if not (reason or "").strip():
        raise SeatError("a reason is required — the map of the door is a receipt.")
    globs = [g.strip() for g in _globs(globs) if g and g.strip()]
    if not remove and not globs:
        raise SeatError("--owns needs at least one file-name glob, e.g. \"marketing-*\".")
    bad = [g for g in globs if "/" in g or "\\" in g]
    if bad:
        raise SeatError(f"a glob names a file, not a path: {', '.join(bad)}")
    path = config_path(v.root)
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)                      # the file as written — never the defaults overlay
    table = cfg.setdefault("inbox", {}).setdefault("seats", {})
    if remove:
        if seat not in table:
            raise SeatError(f"'{seat}' has no seat in inbox.seats.")
        del table[seat]
    else:
        table[seat] = globs
    with guard.writable(v.root, path), open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    detail = (f"{seat} off the door" if remove else f"{seat} owns {', '.join(globs)}") + f" · {reason.strip()}"
    TrustLedger(v).record("inbox.seat", "removed" if remove else "set", by, seat, detail,
                          **({"ran_by": ran_by} if ran_by else {}))
    return dict(table)
