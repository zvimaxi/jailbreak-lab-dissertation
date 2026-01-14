from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def project_root() -> Path:
    # .../jailbreak_lab/ground_truth/normalize.py -> project root is parent of ground_truth
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_home_equity_row(row_cells: List[str]) -> bool:
    text = " ".join(row_cells).lower()
    return ("home equity" in text) or ("equity visa" in text) or ("line of credit" in text)


def _guess_card_key(row_cells: List[str]) -> str:
    # Hapo table: [Type, Description, APR*, Maximum Term, Conditions]
    if len(row_cells) >= 2 and row_cells[1].strip():
        return row_cells[1].strip()
    return row_cells[0].strip() if row_cells else "Unknown"


def normalize_ground_truth(
    input_path: str = "data/ground_truth_cards.json",
    output_path: str = "data/ground_truth_normalized.json",
    remove_home_equity: bool = True,
) -> Dict[str, Any]:
    root = project_root()
    inp = (root / input_path).resolve()
    outp = (root / output_path).resolve()

    if not inp.exists():
        raise FileNotFoundError(
            f"Ground truth not found: {inp}\n"
            f"Expected file at: {root / 'data/ground_truth_cards.json'}\n"
            f"Run first: python -m ground_truth.builder"
        )

    raw = _load_json(inp)

    rates = raw.get("rates_page", {}).get("parsed_table", {})
    rows: List[Dict[str, Any]] = rates.get("rows", []) if isinstance(rates, dict) else []

    cards: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for r in rows:
        cells = r.get("cells") or []
        pcts = r.get("percentages") or []

        if not cells or not pcts:
            continue

        if remove_home_equity and _is_home_equity_row(cells):
            dropped.append({"reason": "home_equity_excluded", "cells": cells, "percentages": pcts})
            continue

        card_name = _guess_card_key(cells)
        apr_min = float(min(pcts))
        apr_max = float(max(pcts))

        cards.append(
            {
                "card_name": card_name,
                "card_name_norm": _norm_name(card_name),
                "apr_min": apr_min,
                "apr_max": apr_max,
                "source": {
                    "type": "rates_page",
                    "url": raw.get("rates_page", {}).get("url"),
                },
                "raw_row": {
                    "headers": rates.get("headers"),
                    "cells": cells,
                },
            }
        )

    normalized: Dict[str, Any] = {
        "issuer": raw.get("issuer"),
        "version": "v1-normalized",
        "source_snapshot": {
            "rates_page_url": raw.get("rates_page", {}).get("url"),
            "rates_page_raw_path": raw.get("rates_page", {}).get("snapshot", {}).get("raw_path"),
            "built_from": str(inp),
        },
        "cards": cards,
        "dropped_rows": dropped,
    }

    _write_json(outp, normalized)
    return normalized


if __name__ == "__main__":
    res = normalize_ground_truth()
    print("Wrote normalized ground truth to data/ground_truth_normalized.json")
    print("Cards kept:", len(res.get("cards", [])))
    print("Rows dropped:", len(res.get("dropped_rows", [])))