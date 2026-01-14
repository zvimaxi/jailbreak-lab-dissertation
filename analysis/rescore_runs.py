# analysis/rescore_runs.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _project_root() -> Path:
    # .../jailbreak_lab/analysis/rescore_runs.py -> root is parent of analysis/
    return Path(__file__).resolve().parents[1]


# Ensure imports like `from evaluation...` work when running as a script
ROOT = _project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from evaluation.ground_truth import load_ground_truth_normalized  # noqa: E402
from evaluation.scoring import score_transcript  # noqa: E402


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Runs file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--defense_level", type=str, required=True)
    ap.add_argument("--in_path", type=str, default=None)
    ap.add_argument("--out_path", type=str, default=None)
    ap.add_argument("--gt", type=str, default="data/ground_truth_normalized.json")
    args = ap.parse_args()

    defense = args.defense_level.strip()

    in_path = Path(args.in_path).expanduser() if args.in_path else (Path("data/runs") / defense / "runs.jsonl")
    in_path = in_path.resolve()

    out_path = Path(args.out_path).expanduser() if args.out_path else in_path.with_name("runs.rescored.jsonl")
    out_path = out_path.resolve()

    gt = load_ground_truth_normalized(args.gt)

    records = read_jsonl(in_path)
    rescored: List[Dict[str, Any]] = []

    for r in records:
        transcript = r.get("transcript") or []
        target = r.get("target_card_norm") or ""
        new_score = score_transcript(transcript, gt, target_card_norm=target)
        r["score"] = new_score
        rescored.append(r)

    write_jsonl(out_path, rescored)
    print(f"[OK] Read:  {in_path} ({len(records)} records)")
    print(f"[OK] Wrote: {out_path}")


if __name__ == "__main__":
    main()