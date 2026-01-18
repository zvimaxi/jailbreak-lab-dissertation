# analysis/summarize_runs.py
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------
# Defaults (matches your repo)
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


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:120] or "x"


# -----------------------------
# Schema adapters
# -----------------------------

def _get_score_obj(run: Dict[str, Any]) -> Dict[str, Any]:
    for k in ("score", "scoring", "score_result", "evaluation", "eval"):
        v = run.get(k)
        if isinstance(v, dict) and (
            "success" in v
            or "final_violates_truth" in v
            or "ever_violates_truth" in v
            or "user_exposure_success" in v
        ):
            return v
    metrics = run.get("metrics")
    if isinstance(metrics, dict):
        v = metrics.get("score")
        if isinstance(v, dict):
            return v
    return {}


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
    # Your data uses both "attack" and "attack_type"
    for k in ("attack_type", "attack", "attack_family", "attack_category"):
        v = run.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    cfg = run.get("config")
    if isinstance(cfg, dict):
        v = cfg.get("attack_type") or cfg.get("attack_family") or cfg.get("attack")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "UNKNOWN"


def _get_transcript(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    t = run.get("transcript")
    if isinstance(t, list):
        return [x for x in t if isinstance(x, dict)]
    # fallback if future schema changes
    t2 = run.get("messages") or run.get("turns")
    if isinstance(t2, list):
        return [x for x in t2 if isinstance(x, dict)]
    return []


def _get_guardrail_flags_from_transcript(run: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int], bool]:
    """
    Your transcript assistant turns contain:
      turn["guardrails"] with {global_guardrail_fired, moderation_guardrail_fired, ...}
      turn["blocked"] boolean
    Also score contains guardrail_fired_counts etc.
    We'll prefer score totals; but if missing, compute here.
    """
    fired: Dict[str, int] = {"global": 0, "moderation": 0, "hallucination": 0, "session": 0}
    blocked: Dict[str, int] = {"session": 0}
    any_block = False

    for turn in _get_transcript(run):
        if turn.get("role") != "assistant":
            continue
        gr = turn.get("guardrails")
        if isinstance(gr, dict):
            if gr.get("global_guardrail_fired") is True:
                fired["global"] += 1
            if gr.get("moderation_guardrail_fired") is True:
                fired["moderation"] += 1
            if gr.get("hallucination_guardrail_fired") is True:
                fired["hallucination"] += 1
            if gr.get("session_guardrail_fired") is True:
                fired["session"] += 1
            if gr.get("session_guardrail_blocked") is True:
                blocked["session"] += 1
                any_block = True

        if turn.get("blocked") is True:
            blocked["session"] += 1
            any_block = True

    return fired, blocked, any_block


def _get_guardrails_obj(run: Dict[str, Any], score: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int], bool]:
    fired = score.get("guardrail_fired_counts")
    blocked = score.get("guardrail_blocked_counts")
    any_block = score.get("any_session_block")

    if isinstance(fired, dict) and isinstance(blocked, dict) and isinstance(any_block, bool):
        fired_n = {str(k): int(v or 0) for k, v in fired.items()}
        blocked_n = {str(k): int(v or 0) for k, v in blocked.items()}
        return fired_n, blocked_n, bool(any_block)

    # fallback: compute from transcript
    return _get_guardrail_flags_from_transcript(run)


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

    # Errors (simple)
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
# Aggregation helpers
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


# -----------------------------
# Appendix sample extraction
# -----------------------------

@dataclass
class AppendixPick:
    pick_type: str
    defense_level: str
    attack_type: str
    run_id: str
    any_session_block: bool
    ever_violates_truth: bool
    final_violates_truth: bool
    user_exposure_success: bool
    out_path: str


def _render_transcript_md(run: Dict[str, Any]) -> str:
    score = _get_score_obj(run) or {}
    t = _get_transcript(run)

    lines: List[str] = []
    lines.append(f"# Appendix Evidence — {run.get('defense_level','UNKNOWN')} / {run.get('attack','UNKNOWN')} / {run.get('run_id','UNKNOWN')}")
    lines.append("")
    lines.append("## Key outcome flags (from score)")
    lines.append("")
    flags = [
        ("success (final violation)", score.get("success")),
        ("ever_violates_truth", score.get("ever_violates_truth")),
        ("final_violates_truth", score.get("final_violates_truth")),
        ("user_exposure_success", score.get("user_exposure_success")),
        ("any_session_block", score.get("any_session_block")),
        ("final_confirm_apr", score.get("final_confirm_apr")),
        ("ground_truth_apr_min", score.get("ground_truth_apr_min")),
        ("ground_truth_apr_max", score.get("ground_truth_apr_max")),
    ]
    for k, v in flags:
        lines.append(f"- **{k}**: `{v}`")
    lines.append("")

    ev = score.get("evidence")
    if isinstance(ev, dict):
        lines.append("## Automated evidence snippets")
        for k in ("ever_violation", "user_exposure", "final_violation"):
            x = ev.get(k)
            if isinstance(x, dict):
                lines.append("")
                lines.append(f"### {k}")
                reason = x.get("reason")
                turn_index = x.get("turn_index")
                txt = x.get("text") or x.get("line")
                lines.append(f"- **reason**: `{reason}`")
                if turn_index is not None:
                    lines.append(f"- **turn_index**: `{turn_index}`")
                if txt:
                    lines.append("")
                    lines.append("> " + str(txt).replace("\n", "\n> "))
        lines.append("")

    lines.append("## Full transcript (role-ordered)")
    lines.append("")
    for i, turn in enumerate(t):
        role = turn.get("role", "unknown")
        text = turn.get("text", "")
        delivered = turn.get("delivered_to_user")
        blocked = turn.get("blocked")
        meta = []
        if role == "assistant":
            if delivered is not None:
                meta.append(f"delivered_to_user={delivered}")
            if blocked is not None:
                meta.append(f"blocked={blocked}")
        meta_s = f" ({', '.join(meta)})" if meta else ""
        lines.append(f"### Turn {i} — {role}{meta_s}")
        lines.append("")
        lines.append(str(text))
        lines.append("")

    return "\n".join(lines)


def _select_appendix_examples(
    runs: List[Dict[str, Any]],
    kpis_by_run_id: Dict[str, RunKPIs],
    max_per_defense: int = 4,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Returns list of (pick_type, run) for appendix.

    We prefer picks that support Chapter 6 claims:
      - FINAL_VIOLATION (commitment failure)
      - MID_ONLY (reasoning drift but self-correct)
      - BLOCKED_BASELINE (usability collapse / session block)
      - CLEAN_DEFENSE (attack resisted & usable)

    This selection is heuristic and can be tuned later.
    """
    picks: List[Tuple[str, Dict[str, Any]]] = []

    # group by defense
    by_def = {}
    for r in runs:
        dl = _get_defense_level(r, fallback="UNKNOWN")
        by_def.setdefault(dl, []).append(r)

    for dl, group in sorted(by_def.items()):
        # sort stable by created_at_utc if present
        group_sorted = sorted(group, key=lambda x: str(x.get("created_at_utc", "")))

        # classify candidates
        final_violation = []
        mid_only = []
        blocked_any = []
        clean = []

        for r in group_sorted:
            rid = _get_run_id(r, 0)
            k = kpis_by_run_id.get(rid)
            if not k or k.error:
                continue

            if k.any_session_block:
                blocked_any.append(r)

            if k.final_violates_truth:
                final_violation.append(r)
            elif k.ever_violates_truth and not k.final_violates_truth:
                mid_only.append(r)
            elif (not k.ever_violates_truth) and (not k.any_session_block):
                clean.append(r)

        # pick at most max_per_defense, in priority order
        local: List[Tuple[str, Dict[str, Any]]] = []

        if final_violation:
            local.append(("FINAL_VIOLATION", final_violation[0]))
        if mid_only:
            local.append(("MID_ONLY", mid_only[0]))
        if blocked_any:
            local.append(("ANY_SESSION_BLOCK", blocked_any[0]))
        if clean:
            local.append(("CLEAN_DEFENSE", clean[0]))

        picks.extend(local[:max_per_defense])

    return picks


def _build_appendix(
    runs_path: Path,
    runs: List[Dict[str, Any]],
    kpis: List[RunKPIs],
    out_dir: Path,
) -> None:
    """
    Writes:
      - <out_dir>/appendix_samples/*.md
      - <out_dir>/appendix_index.csv
    """
    out_samples = out_dir / "appendix_samples"
    out_samples.mkdir(parents=True, exist_ok=True)

    kpis_by_id = {k.run_id: k for k in kpis}
    picks = _select_appendix_examples(runs, kpis_by_id)

    index_rows: List[Dict[str, Any]] = []
    for pick_type, run in picks:
        rid = run.get("run_id", "")
        dl = run.get("defense_level", _get_defense_level(run, fallback="UNKNOWN"))
        at = run.get("attack_type", run.get("attack", _get_attack_type(run)))

        k = kpis_by_id.get(rid)
        if not k:
            continue

        fname = f"{_slug(dl)}__{_slug(at)}__{_slug(pick_type)}__{_slug(rid)}.md"
        fpath = out_samples / fname
        fpath.write_text(_render_transcript_md(run), encoding="utf-8")

        index_rows.append(
            {
                "pick_type": pick_type,
                "defense_level": dl,
                "attack_type": at,
                "run_id": rid,
                "any_session_block": int(k.any_session_block),
                "ever_violates_truth": int(k.ever_violates_truth),
                "final_violates_truth": int(k.final_violates_truth),
                "user_exposure_success": int(k.user_exposure_success),
                "out_path": str(fpath),
            }
        )

    if index_rows:
        _write_csv(out_dir / "appendix_index.csv", index_rows, list(index_rows[0].keys()))
    else:
        _write_csv(out_dir / "appendix_index.csv", [], [
            "pick_type","defense_level","attack_type","run_id",
            "any_session_block","ever_violates_truth","final_violates_truth","user_exposure_success","out_path"
        ])

    print(f"[OK] Appendix samples: {out_samples}")
    print(f"[OK] Appendix index:   {out_dir / 'appendix_index.csv'}")


# -----------------------------
# Main summarization
# -----------------------------

def _summarize_one_defense(defense: str, runs_path: Path, out_dir: Path) -> None:
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

    # Cumulative columns
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
            "local_asr": "success_final_violation_pct where success == final_violates_truth (per score.success)",
            "cumulative_asr": "running success rate over run order, excluding error runs from denominator",
            "ever_violation": "ever_violates_truth == True in any assistant turn",
            "exposure_success": "user_exposure_success == True (violating turn delivered_to_user=True)",
            "mid_only_violation": "ever_violates_truth=True AND final_violates_truth=False",
        },
        "overall": overall,
        "by_defense_level": by_defense,
        "by_attack_type": by_attack,
    }

    out_json = out_dir / "summary.json"
    out_csv = out_dir / "summary.csv"
    out_md = out_dir / "summary.md"
    out_ts_csv = out_dir / "timeseries.csv"

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

    # NEW: Appendix extraction
    _build_appendix(runs_path, records, kpis, out_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--defense_level",
        type=str,
        default=DEFAULT_DEFENSE,
        help='Defense label (e.g. "D0", "D1B"). Default: D0',
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
    parser.add_argument(
        "--all_defenses",
        action="store_true",
        help="If set, summarize ALL defense folders found under data/runs/",
    )
    args = parser.parse_args()

    if args.all_defenses:
        root = DEFAULT_OUT_ROOT
        if not root.exists():
            raise FileNotFoundError(f"Runs root not found: {root}")

        defense_dirs = sorted([p for p in root.iterdir() if p.is_dir() and (p / "runs.jsonl").exists()])
        if not defense_dirs:
            raise FileNotFoundError(f"No defense folders with runs.jsonl found under: {root}")

        for d in defense_dirs:
            defense = d.name
            runs_path = (d / "runs.jsonl").resolve()
            out_dir = d.resolve()
            print(f"\n=== Summarizing {defense} ===")
            _summarize_one_defense(defense, runs_path, out_dir)

        print("\n[OK] Completed all defenses.")
        return

    defense = args.defense_level.strip()
    default_runs_path = DEFAULT_OUT_ROOT / defense / "runs.jsonl"
    runs_path = Path(args.runs_path).expanduser() if args.runs_path else default_runs_path
    runs_path = runs_path.resolve()

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else runs_path.parent
    _summarize_one_defense(defense, runs_path, out_dir)


if __name__ == "__main__":
    main()