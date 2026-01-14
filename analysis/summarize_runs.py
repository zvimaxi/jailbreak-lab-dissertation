# analysis/summarize_runs.py
from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Defaults (Option B friendly)
# -----------------------------
DEFAULT_OUT_ROOT = Path("data/runs")
DEFAULT_DEFENSE = "D0"


# -----------------------------
# IO helpers
# -----------------------------

def _read_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    records: List[Dict[str, Any]] = []
    bad = 0
    samples: List[str] = []

    if not path.exists():
        raise FileNotFoundError(f"Runs file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                bad += 1
                if len(samples) < 5:
                    samples.append("<blank line>")
                continue
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    bad += 1
                    if len(samples) < 5:
                        samples.append(raw[:200])
            except Exception:
                bad += 1
                if len(samples) < 5:
                    samples.append(raw[:200])

    return records, bad, samples


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _pct(n: int, d: int) -> float:
    return round((n / d * 100.0), 2) if d else 0.0


# -----------------------------
# Schema adapters
# -----------------------------

def _get_score_obj(run: Dict[str, Any]) -> Dict[str, Any]:
    for k in ("score", "scoring", "score_result", "evaluation", "eval"):
        v = run.get(k)
        if isinstance(v, dict) and ("success" in v or "final_violates_truth" in v or "ever_violates_truth" in v):
            return v
    metrics = run.get("metrics")
    if isinstance(metrics, dict):
        v = metrics.get("score")
        if isinstance(v, dict):
            return v
    return {}


def _get_guardrails_obj(run: Dict[str, Any], score: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int], bool]:
    fired = score.get("guardrail_fired_counts")
    blocked = score.get("guardrail_blocked_counts")
    any_block = score.get("any_session_block")

    if isinstance(fired, dict) and isinstance(blocked, dict) and isinstance(any_block, bool):
        fired_n = {str(k): int(v or 0) for k, v in fired.items()}
        blocked_n = {str(k): int(v or 0) for k, v in blocked.items()}
        return fired_n, blocked_n, bool(any_block)

    gr = run.get("guardrails") or run.get("guardrail_events") or {}
    fired_n: Dict[str, int] = {}
    blocked_n: Dict[str, int] = {}
    any_block_n = False
    if isinstance(gr, dict):
        fc = gr.get("fired_counts") or gr.get("fired") or {}
        bc = gr.get("blocked_counts") or gr.get("blocked") or {}
        ab = gr.get("any_session_block")
        if isinstance(fc, dict):
            fired_n = {str(k): int(v or 0) for k, v in fc.items()}
        if isinstance(bc, dict):
            blocked_n = {str(k): int(v or 0) for k, v in bc.items()}
        if isinstance(ab, bool):
            any_block_n = ab
    return fired_n, blocked_n, any_block_n


def _get_defense_level(run: Dict[str, Any], fallback: str = "UNKNOWN") -> str:
    for k in ("defense_level", "defense", "d_level", "guardrail_level"):
        v = run.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, int):
            return f"D{v}"
    cfg = run.get("config")
    if isinstance(cfg, dict):
        v = cfg.get("defense_level") or cfg.get("defense")
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, int):
            return f"D{v}"
    return fallback


def _get_run_id(run: Dict[str, Any], idx: int) -> str:
    for k in ("run_id", "id", "uuid"):
        v = run.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"run_{idx:04d}"


def _get_attack_type(run: Dict[str, Any]) -> str:
    for k in ("attack_type", "attack_family", "attack_category", "attack"):
        v = run.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    cfg = run.get("config")
    if isinstance(cfg, dict):
        v = cfg.get("attack_type") or cfg.get("attack_family")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "UNKNOWN"


# -----------------------------
# KPI extraction
# -----------------------------

@dataclass
class RunKPIs:
    run_id: str
    defense_level: str
    attack_type: str

    success: bool
    ever_violates_truth: bool
    final_violates_truth: bool
    user_exposure_success: bool

    mentions_any_percent: bool
    mentions_zero_percent: bool
    final_confirm_apr: Optional[float]

    any_session_block: bool
    fired_counts: Dict[str, int]
    blocked_counts: Dict[str, int]

    error: bool
    error_type: str

    def to_row(self) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "run_id": self.run_id,
            "defense_level": self.defense_level,
            "attack_type": self.attack_type,

            "success_final_violation": int(self.success),
            "ever_violates_truth": int(self.ever_violates_truth),
            "final_violates_truth": int(self.final_violates_truth),
            "user_exposure_success": int(self.user_exposure_success),
            "mid_only_violation": int(self.ever_violates_truth and not self.final_violates_truth),

            "mentions_any_percent": int(self.mentions_any_percent),
            "mentions_zero_percent": int(self.mentions_zero_percent),
            "final_confirm_apr": "" if self.final_confirm_apr is None else self.final_confirm_apr,

            "any_session_block": int(self.any_session_block),

            "error": int(self.error),
            "error_type": self.error_type,
        }

        for k, v in sorted(self.fired_counts.items()):
            row[f"guardrail_fired_{k}"] = v
        for k, v in sorted(self.blocked_counts.items()):
            row[f"guardrail_blocked_{k}"] = v

        return row


def _extract_run_kpis(run: Dict[str, Any], idx: int, default_defense: str) -> RunKPIs:
    score = _get_score_obj(run)
    defense_level = _get_defense_level(run, fallback=default_defense)
    run_id = _get_run_id(run, idx)
    attack_type = _get_attack_type(run)

    fired_counts, blocked_counts, any_session_block = _get_guardrails_obj(run, score)

    # Errors (kept simple; you can expand later if your runner logs more)
    err = False
    err_type = ""
    for k in ("error", "exception"):
        v = run.get(k)
        if isinstance(v, str) and v.strip():
            err = True
            err_type = v.strip()
            break
        if v is True:
            err = True
            err_type = "true"
            break
    if not err:
        v = run.get("status")
        if isinstance(v, str) and v.lower() in ("error", "failed", "exception"):
            err = True
            err_type = v

    def _b(key: str) -> bool:
        return bool(score.get(key, False))

    final_confirm_apr = score.get("final_confirm_apr")
    if not isinstance(final_confirm_apr, (int, float)):
        final_confirm_apr = None

    return RunKPIs(
        run_id=run_id,
        defense_level=defense_level,
        attack_type=attack_type,

        success=bool(score.get("success", False)),
        ever_violates_truth=_b("ever_violates_truth"),
        final_violates_truth=_b("final_violates_truth"),
        user_exposure_success=_b("user_exposure_success"),

        mentions_any_percent=_b("mentions_any_percent"),
        mentions_zero_percent=_b("mentions_zero_percent"),
        final_confirm_apr=final_confirm_apr,

        any_session_block=bool(any_session_block),
        fired_counts=fired_counts,
        blocked_counts=blocked_counts,

        error=err,
        error_type=err_type,
    )


# -----------------------------
# Aggregation
# -----------------------------

def _sum_dicts(dicts: Iterable[Dict[str, int]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0) + int(v or 0)
    return out


def _kpi_pack(kpis: List[RunKPIs]) -> Dict[str, Any]:
    total = len(kpis)
    valid = sum(1 for r in kpis if not r.error)

    succ = sum(1 for r in kpis if (not r.error) and r.success)
    ever = sum(1 for r in kpis if (not r.error) and r.ever_violates_truth)
    exposure = sum(1 for r in kpis if (not r.error) and r.user_exposure_success)
    mid_only = sum(1 for r in kpis if (not r.error) and r.ever_violates_truth and (not r.final_violates_truth))
    blocked_any = sum(1 for r in kpis if (not r.error) and r.any_session_block)

    fired_totals = _sum_dicts(r.fired_counts for r in kpis if not r.error)
    blocked_totals = _sum_dicts(r.blocked_counts for r in kpis if not r.error)

    return {
        "total_runs": total,
        "valid_runs": valid,
        "error_runs": total - valid,

        "local_asr_success_final_violation_count": succ,
        "local_asr_success_final_violation_pct": _pct(succ, valid),

        "ever_violation_count": ever,
        "ever_violation_pct": _pct(ever, valid),

        "user_exposure_success_count": exposure,
        "user_exposure_success_pct": _pct(exposure, valid),

        "mid_only_violation_count": mid_only,
        "mid_only_violation_pct": _pct(mid_only, valid),

        "any_session_block_count": blocked_any,
        "any_session_block_pct": _pct(blocked_any, valid),

        "guardrail_fired_totals": fired_totals,
        "guardrail_blocked_totals": blocked_totals,
    }


def _group_by(kpis: List[RunKPIs], key_fn) -> Dict[str, List[RunKPIs]]:
    out: Dict[str, List[RunKPIs]] = {}
    for r in kpis:
        k = str(key_fn(r))
        out.setdefault(k, []).append(r)
    return out


def _markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
    h = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(str(x) for x in row) + " |" for row in rows)
    return "\n".join([h, sep, body]) if body else "\n".join([h, sep])


def _print_terminal_summary(overall: Dict[str, Any], bad_lines: int, runs_path: Path, out_dir: Path) -> None:
    print("\n=== Summarizer KPIs ===")
    print(f"Runs file: {runs_path}")
    print(f"Out dir:   {out_dir}")
    if bad_lines:
        print(f"Bad/blank lines skipped: {bad_lines}")

    valid = overall["valid_runs"]
    total = overall["total_runs"]

    print(f"Valid runs: {valid}/{total}")
    print(f"Local ASR (final violation): {overall['local_asr_success_final_violation_pct']}% ({overall['local_asr_success_final_violation_count']})")
    print(f"Ever violation rate:         {overall['ever_violation_pct']}% ({overall['ever_violation_count']})")
    print(f"Exposure success rate:       {overall['user_exposure_success_pct']}% ({overall['user_exposure_success_count']})")
    print(f"Mid-only violation rate:     {overall['mid_only_violation_pct']}% ({overall['mid_only_violation_count']})")
    print(f"Any session block rate:      {overall['any_session_block_pct']}% ({overall['any_session_block_count']})")

    fired = overall.get("guardrail_fired_totals") or {}
    blocked = overall.get("guardrail_blocked_totals") or {}
    keys = sorted(set(list(fired.keys()) + list(blocked.keys())))
    print("\nGuardrails totals:")
    if not keys:
        print("  (none)")
    else:
        for k in keys:
            print(f"  {k}: fired={fired.get(k,0)} blocked={blocked.get(k,0)}")
    print("")


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--defense_level",
        type=str,
        default=DEFAULT_DEFENSE,
        help='Defense label used for default paths (e.g. "D0", "D1B"). Default: D0',
    )
    parser.add_argument(
        "--runs_path",
        type=str,
        default=None,
        help="Optional explicit runs.jsonl path. If omitted: data/runs/<defense_level>/runs.jsonl",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default=None,
        help="Optional explicit output directory. If omitted: parent folder of runs_path",
    )
    args = parser.parse_args()

    defense = args.defense_level.strip()
    default_runs_path = DEFAULT_OUT_ROOT / defense / "runs.jsonl"
    runs_path = Path(args.runs_path).expanduser() if args.runs_path else default_runs_path
    runs_path = runs_path.resolve()

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else runs_path.parent

    out_json = out_dir / "summary.json"
    out_csv = out_dir / "summary.csv"
    out_md = out_dir / "summary.md"
    out_ts_csv = out_dir / "timeseries.csv"

    records, bad_lines, bad_samples = _read_jsonl(runs_path)
    print(f"[OK] Parsed {len(records)} run records from {runs_path}")

    kpis: List[RunKPIs] = []
    for idx, r in enumerate(records):
        try:
            kpis.append(_extract_run_kpis(r, idx, default_defense=defense))
        except Exception as e:
            kpis.append(
                RunKPIs(
                    run_id=_get_run_id(r, idx),
                    defense_level=_get_defense_level(r, fallback=defense),
                    attack_type=_get_attack_type(r),
                    success=False,
                    ever_violates_truth=False,
                    final_violates_truth=False,
                    user_exposure_success=False,
                    mentions_any_percent=False,
                    mentions_zero_percent=False,
                    final_confirm_apr=None,
                    any_session_block=False,
                    fired_counts={},
                    blocked_counts={},
                    error=True,
                    error_type=f"kpi_extract_error:{type(e).__name__}",
                )
            )

    # Per-run rows
    rows = [r.to_row() for r in kpis]

    # Cumulative columns (exclude error runs from denominator)
    cum_valid = 0
    cum_success = 0
    timeseries_rows: List[Dict[str, Any]] = []

    for i, r in enumerate(kpis):
        if not r.error:
            cum_valid += 1
            if r.success:
                cum_success += 1
        cum_asr = round((cum_success / cum_valid * 100.0), 2) if cum_valid else 0.0

        rows[i]["cum_valid_runs"] = cum_valid
        rows[i]["cum_successes"] = cum_success
        rows[i]["cum_asr_pct"] = cum_asr

        timeseries_rows.append(
            {
                "index": i,
                "run_id": r.run_id,
                "defense_level": r.defense_level,
                "attack_type": r.attack_type,
                "success_final_violation": int(r.success),
                "cum_valid_runs": cum_valid,
                "cum_successes": cum_success,
                "cum_asr_pct": cum_asr,
            }
        )

    overall = _kpi_pack(kpis)
    by_defense = {k: _kpi_pack(v) for k, v in _group_by(kpis, lambda x: x.defense_level).items()}
    by_attack = {k: _kpi_pack(v) for k, v in _group_by(kpis, lambda x: x.attack_type).items()}

    summary_obj = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runs_path": str(runs_path),
        "parsed_run_records": len(records),
        "bad_or_blank_lines": bad_lines,
        "bad_line_samples": bad_samples,
        "definition": {
    "local_asr": "success_final_violation_pct where success == final_violates_truth (per evaluation/scoring.py)",
    "cumulative_asr": "running success rate over run order, excluding error runs from denominator",
    "ever_violation": "ever_violates_truth == True in any assistant turn",
    "exposure_success": "user_exposure_success == True (violating turn delivered_to_user=True)",
    "mid_only_violation": "ever_violates_truth=True AND final_violates_truth=False",
    "guardrail_fired_totals": "Totals are counts of assistant turns whose text contained the predefined guardrail abort marker (or explicit guardrail flag if present).",
    "guardrail_blocked_totals": "Totals are counts of assistant turns indicating session-level blocking (marker/flag).",
},
        "overall": overall,
        "by_defense_level": by_defense,
        "by_attack_type": by_attack,
    }

    _write_json(out_json, summary_obj)
    print(f"[OK] Wrote: {out_json}")

    EXPECTED_FIRED_KEYS = ["global", "moderation", "hallucination", "session"]
    EXPECTED_BLOCKED_KEYS = ["session"]

    fired_keys = sorted(set(EXPECTED_FIRED_KEYS) | {k for r in kpis for k in r.fired_counts.keys()})
    blocked_keys = sorted(set(EXPECTED_BLOCKED_KEYS) | {k for r in kpis for k in r.blocked_counts.keys()})

    base_fields = [
        "run_id",
        "defense_level",
        "attack_type",
        "success_final_violation",
        "ever_violates_truth",
        "final_violates_truth",
        "user_exposure_success",
        "mid_only_violation",
        "mentions_any_percent",
        "mentions_zero_percent",
        "final_confirm_apr",
        "any_session_block",
        "error",
        "error_type",
    ]
    fired_fields = [f"guardrail_fired_{k}" for k in fired_keys]
    blocked_fields = [f"guardrail_blocked_{k}" for k in blocked_keys]
    tail_fields = ["cum_valid_runs", "cum_successes", "cum_asr_pct"]

    fieldnames = base_fields + fired_fields + blocked_fields + tail_fields
    _write_csv(out_csv, rows, fieldnames)
    print(f"[OK] Wrote: {out_csv}")

    if timeseries_rows:
        _write_csv(out_ts_csv, timeseries_rows, list(timeseries_rows[0].keys()))
    else:
        _write_csv(out_ts_csv, [], ["index"])
    print(f"[OK] Wrote: {out_ts_csv}")

    # Markdown
    md_lines: List[str] = []
    md_lines.append("# Jailbreak Lab — Run Summary")
    md_lines.append("")
    md_lines.append(f"- Generated at: `{summary_obj['generated_at']}`")
    md_lines.append(f"- Runs file: `{runs_path}`")
    md_lines.append(f"- Parsed records: **{len(records)}**")
    if bad_lines:
        md_lines.append(f"- Skipped bad/blank lines: **{bad_lines}**")
    md_lines.append("")

    o = overall
    md_lines.append("## Overall KPIs")
    md_lines.append("")
    md_lines.append(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Valid runs", f"{o['valid_runs']} / {o['total_runs']}"],
                ["Local ASR (final violation)", f"{o['local_asr_success_final_violation_pct']}% ({o['local_asr_success_final_violation_count']})"],
                ["Ever violation rate", f"{o['ever_violation_pct']}% ({o['ever_violation_count']})"],
                ["User exposure success rate", f"{o['user_exposure_success_pct']}% ({o['user_exposure_success_count']})"],
                ["Mid-only violation rate", f"{o['mid_only_violation_pct']}% ({o['mid_only_violation_count']})"],
                ["Any session block rate", f"{o['any_session_block_pct']}% ({o['any_session_block_count']})"],
            ],
        )
    )
    md_lines.append("")

    md_lines.append("## Guardrails — Totals (Fired / Blocked)")
    md_lines.append("")
    fired_totals = o.get("guardrail_fired_totals") or {}
    blocked_totals = o.get("guardrail_blocked_totals") or {}
    all_gr_keys = sorted(set(list(fired_totals.keys()) + list(blocked_totals.keys())))
    md_lines.append(
        _markdown_table(
            ["Guardrail", "Fired", "Blocked"],
            [[k, fired_totals.get(k, 0), blocked_totals.get(k, 0)] for k in all_gr_keys] or [["(none)", 0, 0]],
        )
    )
    md_lines.append("")

    md_lines.append("## By Defense Level")
    md_lines.append("")
    defense_rows: List[List[Any]] = []
    for dl in sorted(by_defense.keys()):
        x = by_defense[dl]
        defense_rows.append(
            [
                dl,
                f"{x['valid_runs']}/{x['total_runs']}",
                f"{x['local_asr_success_final_violation_pct']}%",
                f"{x['ever_violation_pct']}%",
                f"{x['user_exposure_success_pct']}%",
                f"{x['mid_only_violation_pct']}%",
                f"{x['any_session_block_pct']}%",
            ]
        )
    md_lines.append(
        _markdown_table(
            ["Defense", "Valid/Total", "Local ASR", "Ever viol", "Exposure", "Mid-only", "Any block"],
            defense_rows,
        )
    )
    md_lines.append("")

    md_lines.append("## By Attack Type")
    md_lines.append("")
    attack_rows: List[List[Any]] = []
    for at in sorted(by_attack.keys()):
        x = by_attack[at]
        attack_rows.append(
            [
                at,
                f"{x['valid_runs']}/{x['total_runs']}",
                f"{x['local_asr_success_final_violation_pct']}%",
                f"{x['ever_violation_pct']}%",
                f"{x['user_exposure_success_pct']}%",
            ]
        )
    md_lines.append(_markdown_table(["Attack", "Valid/Total", "Local ASR", "Ever viol", "Exposure"], attack_rows))
    md_lines.append("")

    if bad_lines:
        md_lines.append("## Warnings")
        md_lines.append("")
        md_lines.append(f"- Skipped **{bad_lines}** bad/blank lines.")
        if bad_samples:
            md_lines.append("- Samples:")
            for s in bad_samples:
                md_lines.append(f"  - `{s}`")
        md_lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OK] Wrote: {out_md}")

    # Terminal KPI print
    _print_terminal_summary(overall, bad_lines, runs_path, out_dir)


if __name__ == "__main__":
    main()