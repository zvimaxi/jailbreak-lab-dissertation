from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, Dict, List

from ground_truth.scraper import fetch_and_snapshot
from ground_truth.pdf_terms import parse_pdf_apr_table
from ground_truth.extractor_rules import extract_title_and_text, classify_card_name, extract_intro_months, extract_apr_candidates
from ground_truth.rates_parser import parse_hapo_rates_page


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def build_ground_truth(config_path: str, out_path: str = "data/ground_truth_cards.json") -> Dict[str, Any]:
    cfg = load_config(config_path)

    issuer = cfg.get("issuer")
    card_pages: List[str] = cfg.get("card_pages", [])
    rates_page: str = cfg.get("rates_page")
    disclosure_pdf_path: str = cfg.get("disclosure_pdf_path")

    results: Dict[str, Any] = {
        "issuer": issuer,
        "sources": [],
        "cards": [],
        "rates_page": None,
        "pdf_terms": None,
        "version": "v1",
    }

    # 1) scrape rates page
    if rates_page:
        snap = fetch_and_snapshot(rates_page)
        results["sources"].append(asdict(snap))
        html = read_bytes(snap.raw_path)
        meta = extract_title_and_text(html)

        parsed = parse_hapo_rates_page(html)

        results["rates_page"] = {
            "url": rates_page,
            "snapshot": asdict(snap),
            "title": meta["title"],
            "parsed_table": parsed
        }

    # 2) scrape each card page
    for url in card_pages:
        snap = fetch_and_snapshot(url)
        results["sources"].append(asdict(snap))

        html = read_bytes(snap.raw_path)
        meta = extract_title_and_text(html)
        text = meta["text"]

        card_name = classify_card_name(meta["title"]) or url.split("/")[-1]
        pcts = extract_apr_candidates(text)
        intro_months = extract_intro_months(text)

        results["cards"].append(
            {
                "card_name": card_name,
                "url": url,
                "snapshot": asdict(snap),
                "page_title": meta["title"],
                "percentages_found_on_page": pcts,
                "intro_months_hint": intro_months,
            }
        )

    # 3) parse PDF (authoritative term patterns)
    results["pdf_terms"] = {
        "pdf_path": disclosure_pdf_path,
        "note": "PDF parsed but did not yield numeric APR lines. Using rates page as authoritative source for APR ground truth."
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    res = build_ground_truth("configs/hapo_cards.json")
    print(f"Wrote ground truth to data/ground_truth_cards.json")
    print(f"Cards found: {len(res.get('cards', []))}")