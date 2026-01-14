from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

import requests


@dataclass
class Snapshot:
    url: str
    fetched_at_utc: str
    status_code: int
    content_type: str
    sha256: str
    raw_path: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_and_snapshot(url: str, snapshots_dir: str = "data/snapshots", timeout_s: int = 30) -> Snapshot:
    os.makedirs(snapshots_dir, exist_ok=True)

    resp = requests.get(
        url,
        timeout=timeout_s,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; jailbreak-lab/1.0; +https://example.com)"
        },
    )

    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip() or "application/octet-stream"
    body = resp.content

    sha = hashlib.sha256(body).hexdigest()
    ext = "html" if "html" in content_type else "bin"
    raw_path = os.path.join(snapshots_dir, f"{sha}.{ext}")

    # Write only if not already saved
    if not os.path.exists(raw_path):
        with open(raw_path, "wb") as f:
            f.write(body)

    return Snapshot(
        url=url,
        fetched_at_utc=_utc_now_iso(),
        status_code=resp.status_code,
        content_type=content_type,
        sha256=sha,
        raw_path=raw_path,
    )