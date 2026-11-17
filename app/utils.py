from __future__ import annotations
import math
import re
from datetime import date, datetime
from dateutil import parser as date_parser

FALLBACK = "I do not have that in the data provided."


def normalize_id(value) -> str:
    digits = re.findall(r"\d+", str(value))
    if not digits:
        raise ValueError(f"Cannot normalise initiative identifier: {value!r}")
    return f"INIT-{int(digits[0]):03d}"


def parse_date(value) -> date:
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    s = str(value).strip()
    if not s or s.lower() in {"nan", "nat", "none"}:
        raise ValueError("Date is empty")
    # ISO first: prevents day-first parsing from reinterpreting yyyy-mm-dd.
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return date.fromisoformat(s[:10])
    return date_parser.parse(s, dayfirst=True, fuzzy=False).date()


def parse_number(value) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip().replace(",", "").replace("$", "").replace("₹", "")
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("() ")
    multiplier = 1.0
    if s.lower().endswith("k"):
        multiplier = 1000.0
        s = s[:-1]
    elif s.lower().endswith("m"):
        multiplier = 1_000_000.0
        s = s[:-1]
    n = float(s) * multiplier
    return -n if negative else n


def safe_float(value):
    if value is None:
        return None
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def normalise_title(value: str) -> str:
    s = re.sub(r"\s+", " ", str(value)).strip()
    if s.islower():
        s = s.title()
    # Restore common initialisms used in initiative names.
    s = re.sub(r"\bHr\b", "HR", s)
    s = re.sub(r"\bIt\b", "IT", s)
    s = re.sub(r"\bAi\b", "AI", s)
    return s
