from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
MONTHS_RE = re.compile(r"(\d+)\s*(?:months?|mos\.)", re.IGNORECASE)

APR_KEYWORDS = [
    "apr", "interest rate", "rate", "purchase apr", "annual percentage rate",
    "intro", "introductory", "after that", "variable", "prime"
]


def extract_title_and_text(html_bytes: bytes) -> Dict[str, Any]:
    soup = BeautifulSoup(html_bytes, "lxml")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = " ".join(h1.get_text(" ", strip=True).split())

    text = soup.get_text("\n", strip=True)
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    return {"title": title, "text": text}


def classify_card_name(raw_title: Optional[str]) -> Optional[str]:
    if not raw_title:
        return None
    t = raw_title.replace("| Hapo Community Credit Union", "").strip()
    t = re.sub(r"\s+-\s+Hapo.*$", "", t).strip()
    return t


def extract_intro_months(text: str) -> Optional[int]:
    for m in MONTHS_RE.finditer(text):
        try:
            return int(m.group(1))
        except ValueError:
            continue
    return None


def _has_apr_context(window: str) -> bool:
    w = window.lower()
    return any(k in w for k in APR_KEYWORDS)


def extract_apr_candidates(text: str, window_chars: int = 80) -> List[float]:
    """
    Extract percentage values that appear near APR/rate keywords and are within sane bounds.
    Filters out garbage like 110% or random % used for non-APR content.
    """
    vals: List[float] = []
    for m in PCT_RE.finditer(text):
        try:
            v = float(m.group(1))
        except ValueError:
            continue

        # sane APR bounds for credit cards; keep penalty APRs too but avoid nonsense
        if v <= 0 or v > 40:
            continue

        start = max(0, m.start() - window_chars)
        end = min(len(text), m.end() + window_chars)
        window = text[start:end]

        if _has_apr_context(window):
            vals.append(v)

    return sorted(set(vals))