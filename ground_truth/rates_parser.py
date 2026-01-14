from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

CARD_HINTS = ["visa", "credit card", "platinum", "secured", "youth", "home equity", "cash back", "low rate"]


def _pct_values(s: str) -> List[float]:
    vals = []
    for m in PCT_RE.finditer(s):
        try:
            v = float(m.group(1))
            if 0 < v <= 40:
                vals.append(v)
        except ValueError:
            pass
    return vals


def parse_hapo_rates_page(html_bytes: bytes) -> Dict[str, Any]:
    """
    Best-effort:
    - find tables
    - choose the one that contains "Credit Cards" or Visa-ish rows
    - extract rows containing percent values
    """
    soup = BeautifulSoup(html_bytes, "lxml")
    tables = soup.find_all("table")

    extracted_rows: List[Dict[str, Any]] = []

    def score_table(t) -> int:
        txt = t.get_text(" ", strip=True).lower()
        score = 0
        if "credit card" in txt or "credit cards" in txt:
            score += 5
        if "visa" in txt:
            score += 3
        if "apr" in txt:
            score += 2
        for h in CARD_HINTS:
            if h in txt:
                score += 1
        return score

    best = None
    best_score = -1
    for t in tables:
        s = score_table(t)
        if s > best_score:
            best_score = s
            best = t

    if not best:
        return {"table_found": False, "rows": []}

    # header
    headers = []
    thead = best.find("thead")
    if thead:
        headers = [th.get_text(" ", strip=True) for th in thead.find_all(["th", "td"])]
    if not headers:
        first_tr = best.find("tr")
        if first_tr:
            headers = [c.get_text(" ", strip=True) for c in first_tr.find_all(["th", "td"])]

    # body rows
    for tr in best.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        row_text = " ".join(cells)
        pcts = _pct_values(row_text)
        if pcts:
            extracted_rows.append(
                {
                    "cells": cells,
                    "percentages": pcts,
                }
            )

    return {
        "table_found": True,
        "table_score": best_score,
        "headers": headers,
        "rows": extracted_rows,
    }