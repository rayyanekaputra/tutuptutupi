"""per-value masking functions. none of them log or return the real value."""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import random
import string
from datetime import datetime, timedelta

STAR = "*"
_KEEP_DIRECTIVES = {"%Y", "%y", "%b", "%B"}


class Keyer:
    """hmac-keyed randomness: same value -> same output within a run."""

    def __init__(self, seed: int | None = None) -> None:
        self.key = hashlib.sha256(str(seed).encode()).digest() if seed is not None else os.urandom(32)
        self.date_shift = timedelta(days=self.rng("__date_shift__").randint(-365, 365))

    def rng(self, value: object, salt: str = "") -> random.Random:
        digest = hmac.new(self.key, f"{salt}\x00{value}".encode(), hashlib.sha256).digest()
        return random.Random(int.from_bytes(digest[:8], "big"))


# ---------- partial ----------

def partial_text(value: str) -> str:
    """keep the first and last quarter of the alphanumeric chars, star the middle.
    non-alphanumerics (spaces, @, ., -) stay so the format is still readable."""
    s = str(value)
    pos = [i for i, c in enumerate(s) if c.isalnum()]
    k = math.ceil(len(pos) / 2)
    head, tail = (k + 1) // 2, k // 2
    visible = set(pos[:head]) | (set(pos[len(pos) - tail:]) if tail else set())
    return "".join(c if (i in visible or not c.isalnum()) else STAR for i, c in enumerate(s))


def partial_id(value: object, width: int = 8, keyer: Keyer | None = None) -> str:
    """fixed width output that hides the real length; reveals up to 2 real chars.
    with a keyer the revealed chars are picked per value, so sequential ids still differ."""
    s = "".join(c for c in _id_str(value) if c.isalnum())
    reveal = max(0, min(2, len(s) - 2, width - 2))
    out = [STAR] * width
    if reveal:
        r = keyer.rng(s, "id") if keyer else None
        src = sorted(r.sample(range(len(s)), reveal)) if r else range((len(s) - reveal) // 2, (len(s) + reveal) // 2)
        for j, i in enumerate(src):
            out[2 + j] = s[i]
    return "".join(out)


def partial_date(value: datetime, fmt: str) -> str:
    """format the date, starring everything except year / month name."""
    parts, i = [], 0
    while i < len(fmt):
        if fmt[i] == "%" and i + 1 < len(fmt):
            d = fmt[i:i + 2]
            text = value.strftime(d)
            parts.append(text if d in _KEEP_DIRECTIVES else STAR * len(text))
            i += 2
        else:
            parts.append(fmt[i])
            i += 1
    return "".join(parts)


# ---------- full ----------

def full_text(value: object) -> str:
    return "".join(STAR if c.isalnum() else c for c in str(value))


def full_id(value: object, width: int = 8) -> str:
    return STAR * width


# ---------- fake ----------

def fake_text(value: object, keyer: Keyer) -> str:
    """same character classes and punctuation, different characters."""
    r = keyer.rng(value, "text")
    out = []
    for c in str(value):
        if c.isdigit():
            out.append(r.choice(string.digits))
        elif c.isupper():
            out.append(r.choice(string.ascii_uppercase))
        elif c.islower():
            out.append(r.choice(string.ascii_lowercase))
        else:
            out.append(c)
    return "".join(out)


def fake_int(value: int, keyer: Keyer) -> int:
    n = int(value)
    digits = len(str(abs(n)))
    r = keyer.rng(n, "int")
    lo = 0 if digits == 1 else 10 ** (digits - 1)
    fake = r.randint(lo, 10 ** digits - 1)
    return -fake if n < 0 else fake


def fake_float(value: float, keyer: Keyer) -> float:
    v = float(value)
    if v == 0 or not math.isfinite(v):
        return v
    r = keyer.rng(v, "float")
    exp = math.floor(math.log10(abs(v)))
    decimals = _decimals(v)
    fake = round(r.uniform(10 ** exp, 10 ** (exp + 1)), decimals)
    return -fake if v < 0 else fake


def fake_date(value: datetime, keyer: Keyer) -> datetime:
    jitter = timedelta(days=keyer.rng(value, "date").randint(-15, 15))
    return value + keyer.date_shift + jitter


def fake_bool(value: bool, keyer: Keyer) -> bool:
    return bool(keyer.rng(value, "bool").getrandbits(1))


# ---------- helpers ----------

def _id_str(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _decimals(v: float) -> int:
    s = repr(v)
    return len(s.split(".")[1]) if "." in s and "e" not in s else 0
