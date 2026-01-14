from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

def load_ground_truth_normalized(path: str = "data/ground_truth_normalized.json") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Ground truth file not found: {p.resolve()}")
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class CardAPR:
    card_name: str
    card_name_norm: str
    apr_min: float
    apr_max: float


@dataclass(frozen=True)
class GroundTruth:
    issuer: str
    cards: List[CardAPR]

    def find_card(self, name_or_norm: str) -> Optional[CardAPR]:
        q = (name_or_norm or "").strip().lower()
        for c in self.cards:
            if q == c.card_name_norm or q == c.card_name.lower():
                return c
        return None


def _project_root() -> Path:
    # .../jailbreak_lab/evaluation/ground_truth.py -> root is parent of evaluation/
    return Path(__file__).resolve().parents[1]


def load_ground_truth(path: str = "data/ground_truth_normalized.json") -> GroundTruth:
    root = _project_root()
    p = (root / path).resolve()
    if not p.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {p}\n"
            f"Expected: {root / 'data/ground_truth_normalized.json'}\n"
            f"Run: python -m ground_truth.normalize"
        )

    raw: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    issuer = raw.get("issuer", "Unknown Issuer")
    cards_raw = raw.get("cards", [])

    cards: List[CardAPR] = []
    for c in cards_raw:
        cards.append(
            CardAPR(
                card_name=c["card_name"],
                card_name_norm=c["card_name_norm"],
                apr_min=float(c["apr_min"]),
                apr_max=float(c["apr_max"]),
            )
        )

    return GroundTruth(issuer=issuer, cards=cards)