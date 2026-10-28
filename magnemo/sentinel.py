"""magnemo.sentinel — the shared sweep: secret formats and injection patterns.

Sentinel guards the GATE (stage → canon) and the COPY (chest push). It never
quotes a matched value back; it names the pattern. S1–S13 are the injection
shapes an agent's context can carry; a hit taints the note and raises an alert.
S14 (P-106 addendum C) labels a person's contact: an email address or a phone number in a staged note is kept as
written, and the note carries a `contact` line ("contact details present: email ×1"), as does the ledger. Nothing is
held and no alert is raised; the note stages and keeps like any other. The ask is where THE TWO-YES LAW puts it: the
chest push asks once for a batch that carries labelled notes, and names them.

THE FOUR DOORS (P-74): the chest push (blocks), the inbox (holds a secret, taints an
injection + an ALERT note), the Room (redacts a secret, taints an injection), and
`stage` — the MCP tool and the CLI verb — through `gate()` below: a secret never
lands (the body becomes the redaction line), an injection stages tainted beside an
ALERT note. `retrieve` never serves a tainted note to an agent until a keyholder
clears it (`magnemo clear`). What Sentinel is today: a deterministic sweep — secret
formats and thirteen instruction shapes, regex, no model — at every door a memory
enters by. What it is not yet: a reviewer that understands intent.

P-102 · THE TUNE: at the inbox door, a drop from a seat on the vault's own map is read as a report. A quote, a mention
and a control's name do not flag it (five shapes only: S3, S4, S6, S9, S13); its own instruction still does, and the
other eight shapes trip quoted or not. Every other door, and every unknown hand, is read at full weight as before.
`magnemo flags` reads the flagged notes again (read-only); `magnemo clear --all-false` is the keyholder's one word.
"""
from __future__ import annotations
import re

INJECTION = [
    ("S1-ignore-instructions", re.compile(r"(?i)\bignore\s+(all\s+|the\s+|any\s+|previous\s+|prior\s+|everything\s+)?(instructions?|rules?|the\s+founder|the\s+human|above\b)")),
    ("S2-disregard", re.compile(r"(?i)\bdisregard\s+(all\s+|the\s+|your\s+)?(instructions?|rules?|governance|the\s+ledger)")),
    ("S3-merge-now", re.compile(r"(?i)\b(merge|ship|deploy|publish)\s+(it\s+)?now\b")),
    ("S4-promote-now", re.compile(r"(?i)\b(promote|approve|canonize)\s+(this|it|everything|the\s+note)\b")),
    ("S5-you-are-now", re.compile(r"(?i)\byou\s+are\s+now\s+(a|an|the|in)\b")),
    ("S6-system-prompt", re.compile(r"(?i)\b(system\s+prompt|developer\s+message)\b")),
    ("S7-bypass", re.compile(r"(?i)\b(bypass|skip|disable)\s+(the\s+)?(sweep|sentinel|review|gate|permission|approval|guard)")),
    ("S8-impersonate-authority", re.compile(r"(?i)\b(as|i\s+am)\s+the\s+founder\b.*\b(authorize|approve|order)")),
    ("S9-act-without-approval", re.compile(r"(?i)\bwithout\s+(human\s+)?(approval|review|the\s+founder)")),
    ("S10-exfiltrate", re.compile(r"(?i)\b(send|post|upload|exfiltrate)\s+(the\s+|all\s+)?(keys?|tokens?|secrets?|credentials?|vault)\b")),
    ("S11-delete-ledger", re.compile(r"(?i)\b(delete|wipe|truncate|rewrite)\s+(the\s+)?(ledger|history|receipts?)")),
    ("S12-autonomous-mode", re.compile(r"(?i)\b(autonomous\s+mode|no\s+human\s+in\s+the\s+loop|god\s+mode)\b")),
    ("S13-destroy-vault", re.compile(r"(?i)\b(delete|destroy|wipe|erase|rm\s+-rf?|remove)\s+(the\s+|all\s+|every\s+)?(vault|boardroom|canon|memories|memory|files?|everything)\b")),
]


# ---------------------------------------------------------------- P-102 · THE TUNE: a quote is not an instruction
# A drop from a seat on the vault's own map (inbox.seats), through the inbox door, is read the way a person reads a
# report: what it QUOTES and what it MENTIONS is not what it TELLS an agent to do. Only the five shapes below bend,
# and only at that door. Everything else, at every door, weighs what it always weighed: S1, S2, S5, S7, S8, S10, S11,
# S12 trip wherever they stand, quoted or not, from anyone.
SOFT = ("S3", "S4", "S6", "S9", "S13")
FULL, LOW, TRIPS = 1.0, 0.25, 1.0
_FENCE = re.compile(r"(?m)^[ \t]{0,3}(```|~~~)")
_SPANS = (re.compile(r"`[^`\n]+`"), re.compile(r'"[^"\n]+"'), re.compile(r"“[^”\n]+”"), re.compile(r"‘[^’\n]+’"),
          re.compile(r"(?<![\w])'[^'\n]+'(?![\w])"))
_THEIRS = re.compile(r"(?i)\b(their|his|her)\s+(own\s+)?words\b|\bin\s+(their|his|her)\s+words\b|(?<![\w.])@[A-Za-z0-9_][\w.-]+|https?://"
                     r"|\ba\s+builder\b|\b(wrote|said|says|asked|writes)\s*:")
_LEAD = re.compile(r"(?i)(?:^|[\s(\[\"“'‘*_`])(?:and|then|now|please|just|so|also|or|must|should|shall|will|always|immediately|first|next"
                   r"|agent|claude|assistant|you\s+(?:must|should|will|shall|can|may|need\s+to|have\s+to|are\s+to))[,:]?\s*$")
_MARKUP = re.compile(r"^[\s>#*+\-\d.)\]|]*$")
_S6_TELLS = re.compile(r"(?i)\b(reveal|print|show|repeat|output|dump|leak|ignore|override|replace|change|rewrite|update|forget|new|your|this\s+is\s+(?:the|a|your))"
                       r"\s+(?:me\s+)?(?:(?:your|the|its|a)\s+)?(?:(?:hidden|real|full|new|updated|original)\s+)?$")
_S9_VERB = re.compile(r"(?i)\b(act|merge|ship|deploy|publish|promote|approve|canonize|proceed|go\s+ahead|do\s+(?:it|this|that)|push|send|delete|run|write|save|commit|continue)\b")


def _fenced(text: str) -> list:
    marks = [m.start() for m in _FENCE.finditer(text)]
    return [(marks[i], marks[i + 1]) for i in range(0, len(marks) - 1, 2)]


def _line_of(text: str, at: int) -> tuple:
    a = text.rfind("\n", 0, at) + 1
    b = text.find("\n", at)
    return a, (len(text) if b < 0 else b)


def _quoted(text: str, a: int, b: int, fences: list) -> bool:
    """Is text[a:b] inside a fenced block, a blockquote line, or a quoted span on its own line?"""
    if any(fa <= a and b <= fb for fa, fb in fences):
        return True
    la, lb = _line_of(text, a)
    line = text[la:lb]
    if line.lstrip().startswith(">"):
        return True
    return any(la + m.start() < a and b < la + m.end() + 1 and b <= la + m.end() for rx in _SPANS for m in rx.finditer(line))


def _attributed(text: str, a: int) -> bool:
    """Does the note say whose words these are: on the line, the two lines above it, or the nearest heading above?"""
    la, lb = _line_of(text, a)
    above = text[:la].split("\n")
    near = [text[la:lb]] + above[-3:-1][::-1] + [next((l for l in reversed(above) if l.lstrip().startswith("#")), "")]
    return any(_THEIRS.search(l) for l in near)


def _clause_start(text: str, a: int) -> bool:
    """Does the match open a clause of the note's own: the start of a line, after a stop, or after a word that leads
    an order ("and", "then", "please", "you must")? "until you approve it" and "to approve it" do not."""
    la, _ = _line_of(text, a)
    pre = text[la:a].rstrip("\"“'‘`*_ ")                 # an opening quote or emphasis mark is not a word before it
    if _MARKUP.match(pre):
        return True
    return pre[-1:] in ".!?;:,·→—–(" or bool(_LEAD.search(pre + " "))


def _label(text: str, a: int, b: int) -> bool:
    """A control's name in capitals inside ordinary prose (SHIP NOW), or a cell of a table row."""
    la, lb = _line_of(text, a)
    line, word = text[la:lb], text[a:b]
    return line.lstrip().startswith("|") or (word.isupper() and not line.isupper())


def hits(text: str, known_seat: bool = False) -> list:
    """Every instruction-shaped match: [{pattern, line, text, weight, why}]. From an unknown hand every match weighs
    FULL. From a known seat through the door, a SOFT shape weighs nothing when it is a quote or is not the note's own
    order, and LOW when it is a control's name or a table cell. The matched line is returned (it is not a secret)."""
    out, fences = [], (_fenced(text) if known_seat else [])
    for name, rx in INJECTION:
        for m in rx.finditer(text):
            a, b = m.span()
            la, lb = _line_of(text, a)
            weight, why = FULL, "an instruction-shaped line"
            sid = name.split("-", 1)[0]
            if known_seat and sid in SOFT:
                if _quoted(text, a, b, fences) and (sid != "S13" or _attributed(text, a)):
                    weight, why = 0.0, "a quote"
                elif sid == "S6":
                    if not (_S6_TELLS.search(text[la:a]) or (_MARKUP.match(text[la:a]) and text[b:b + 1] == ":")):
                        weight, why = 0.0, "names the thing; tells no one to do anything"
                elif sid == "S9":
                    stop = max(text.rfind(c, la, a) for c in ".!?;")
                    clause = text[(stop + 1 if stop >= 0 else la):a]
                    v = _S9_VERB.search(clause)
                    if not (v and _clause_start(text, (stop + 1 if stop >= 0 else la) + v.start())):
                        weight, why = 0.0, "describes; tells no one to do anything"
                elif not _clause_start(text, a):
                    weight, why = 0.0, "describes; tells no one to do anything"
                elif sid in ("S3", "S4") and _label(text, a, b):
                    weight, why = LOW, "a control's name or a table cell"
            out.append({"pattern": name, "line": text.count("\n", 0, a) + 1, "text": " ".join(text[la:lb].split())[:240],
                        "match": text[a:b], "weight": weight, "why": why})
    return out


def weigh(found: list) -> tuple:
    """(total, pattern). A LOW match counts once per note however often its words recur; the pattern named is the
    heaviest, first in S-order."""
    seen, total, best = set(), 0.0, None
    for h in found:
        if h["weight"] <= 0:
            continue
        if h["weight"] < FULL:
            k = (h["pattern"], h["match"].lower())
            if k in seen:
                continue
            seen.add(k)
        total += h["weight"]
        if best is None or h["weight"] > best["weight"]:
            best = h
    return total, (best["pattern"] if best else None)


def sweep_text(text: str, known_seat: bool = False):
    """(kind, pattern_name) — kind is 'secret', 'injection', or None. The value is never returned.
    `known_seat` (P-102): the drop came through the inbox door under a seat on the vault's map; see `hits`."""
    from .chest import PATTERNS
    for name, rx in PATTERNS:
        if rx.search(text):
            return "secret", name
    total, pat = weigh(hits(text, known_seat))
    if total >= TRIPS:
        return "injection", pat
    return None, None


def came_by_a_seat(note, seat_map: dict) -> bool:
    """Was this note a drop through the inbox door under a seat on the map? Read from what the door wrote."""
    return (note.source or "").startswith("inbox:") and (note.author or "").lower() in {s.lower() for s in (seat_map or {})}


def rescore(vault, seat_map: dict) -> list:
    """The staged notes Sentinel tainted as injections, read again under the rules as they stand:
    [{note, pattern, false, hits, alerts}]. `false`: it came by a seat's door and no longer trips. `alerts`: the
    Sentinel ALERT notes staged beside it (same file, same sha)."""
    staged = vault.staged()
    out = []
    for n in staged:
        if not (n.taint or "").startswith("sentinel:injection:") or n.author == "sentinel":   # an alert is not the subject
            continue
        body = n.body.split("\n\n> taint '", 1)[0]
        seat = came_by_a_seat(n, seat_map)
        found = hits(body, seat)                       # the door swept the file's text; that is the body
        key = " ".join((n.source or "").split()[:2])
        alerts = [x for x in staged if x.author == "sentinel" and key.startswith("inbox:") and "sha256:" in key and (x.source or "").startswith(key + " ")]
        out.append({"note": n, "pattern": n.taint.rsplit(":", 1)[-1], "false": seat and weigh(found)[0] < TRIPS, "seat": seat, "hits": found, "alerts": alerts})
    return out


# ---------------------------------------------------------------- P-106 addendum C · S14: a person's contact, labelled
# The Stranger Run's D7: the person's account email went into a note. There is nothing wrong with an email (the founder,
# Oct 27): it is kept as written. S14 counts what it sees and labels the note; the question is asked only when a
# labelled note would leave the machine.
_EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}(?![\w-])")
_NOT_A_PERSON = re.compile(r"(?i)^(git|noreply|no-reply)@|@(?:[\w-]+\.)*(example\.(com|org|net)|users\.noreply\.github\.com)$"
                           r"|\.(example|test|invalid|localhost)$")
_PHONE = (re.compile(r"(?<![\w.+/-])\+\d{1,3}(?:[ .-]?\(?\d{1,5}\)?){2,5}(?![\w.-]*\d)"),                       # +44 20 7946 0958
          re.compile(r"(?<![\w.+/-])(?:1[ .-])?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?![\w-]|\.\d)"))       # (415) 555-0134, 415-555-0134


def contacts(text: str) -> dict:
    """{"email": n, "phone": n}: how many email addresses and phone numbers the text carries. The text is not changed
    and the values are never returned."""
    found = {"email": sum(1 for m in _EMAIL.finditer(text) if not _NOT_A_PERSON.search(m.group(0))), "phone": 0}
    seen = []
    for rx in _PHONE:
        for m in rx.finditer(text):
            if 10 <= sum(c.isdigit() for c in m.group(0)) <= 15 and not any(a < m.end() and m.start() < b for a, b in seen):
                seen.append((m.start(), m.end()))
    found["phone"] = len(seen)
    return found


def contact_label(counts: dict) -> str:
    """'contact details present: email ×1, phone ×1', or '' when there are none."""
    parts = [f"{k} ×{counts[k]}" for k in ("email", "phone") if counts.get(k)]
    return ("contact details present: " + ", ".join(parts)) if parts else ""


REDACTED = "[REDACTED by Sentinel on stage: secret-shaped text, pattern {pat}. The value never became a memory.]"


def stage_alert(vault, note) -> str:
    """Stage one of Sentinel's own notices, scored like every staged note (so the queue never says "unscored")."""
    from . import kairos
    from .config import load_config
    try:
        kairos.apply(note, vault.canonical(note.partition), load_config(vault.root))
    except (KeyError, ValueError):
        pass
    return vault.stage(note)


def a_door(door: str) -> str:
    """'an MCP stage', 'a CLI stage': the article follows how the door's name is said."""
    return ("an " if door == "MCP" or door[:1].lower() in "aeiou" else "a ") + door


def gate(vault, title: str, body: str, *, partition: str, store: str, source: str, door: str) -> dict:
    """The stage door's sweep (P-74). Returns {verdict: None|'held'|'tainted', pattern, title, body, taint, alert, contact}.
    A secret: the value never lands — the body is the redaction line (and the title, if it carried the secret).
    An injection: the text lands as written, tainted, and a Sentinel ALERT note is staged beside it.
    A person's contact (S14): the text lands as written; `contact` is the label line the note and the ledger carry."""
    kind, pat = sweep_text(title + "\n" + body)
    if kind == "secret":
        t = title if sweep_text(title)[0] != "secret" else f"Held by Sentinel — secret-shaped text ({pat})"
        return {"verdict": "held", "pattern": pat, "title": t, "body": REDACTED.format(pat=pat),
                "taint": f"sentinel:secret:{pat}", "alert": None, "contact": ""}
    nt, nb = contacts(title), contacts(body)
    label = contact_label({k: nt[k] + nb[k] for k in nt})
    if kind is None:
        return {"verdict": None, "pattern": None, "title": title, "body": body, "taint": "", "alert": None, "contact": label}
    from .vault import Note, now_iso
    taint = f"sentinel:injection:{pat}"
    aid = vault.new_id(f"sentinel alert {door} stage")
    stage_alert(vault, Note(id=aid, title=f"Sentinel ALERT: {a_door(door)} stage carries an instruction-shaped line ({pat})",
                     author="sentinel", written=now_iso(), source=f"{door.lower()}-stage:{source}", status="staged",
                     partition=partition, store=store, impact="security", tags="sentinel-alert",
                     body=(f"A note staged through the {door} door carries text shaped like an instruction to an agent "
                           f"(pattern **{pat}**). It was staged TAINTED; nothing acts on it; `retrieve` will not serve it "
                           "to an agent. A keyholder reads it, then rejects it or clears the taint "
                           "(`magnemo clear <id> --reason …`).")))
    return {"verdict": "tainted", "pattern": pat, "title": title, "body": body, "taint": taint, "alert": aid,
            "contact": label}

