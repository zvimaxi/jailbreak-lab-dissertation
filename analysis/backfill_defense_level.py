from __future__ import annotations

import json
from pathlib import Path

RUNS_PATH = Path("data/runs/runs.jsonl")

def main(defense_level: str = "D0") -> None:
    if not RUNS_PATH.exists():
        raise FileNotFoundError(f"Missing: {RUNS_PATH}")

    lines = RUNS_PATH.read_text(encoding="utf-8").splitlines()
    out_lines = []
    updated = 0
    kept = 0
    skipped_blank = 0
    bad_json = 0

    for line in lines:
        raw = line.strip()
        if not raw:
            skipped_blank += 1
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            bad_json += 1
            # keep the original line (or you can drop it); I'd keep for forensics
            out_lines.append(line)
            continue

        if isinstance(obj, dict):
            if not obj.get("defense_level"):
                obj["defense_level"] = defense_level
                updated += 1
            # optional: normalize key for summarizer grouping
            if not obj.get("attack_type") and obj.get("attack"):
                obj["attack_type"] = obj["attack"]
            out_lines.append(json.dumps(obj, ensure_ascii=False))
            kept += 1

    RUNS_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"[OK] Rewrote {RUNS_PATH}")
    print(f"  kept_records={kept}")
    print(f"  updated_defense_level={updated} -> {defense_level}")
    print(f"  skipped_blank={skipped_blank}")
    print(f"  bad_json_lines={bad_json}")

if __name__ == "__main__":
    main()