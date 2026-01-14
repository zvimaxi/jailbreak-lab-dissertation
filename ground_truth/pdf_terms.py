from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pathlib import Path

# We’ll use PyPDF2 (likely installed). If not: pip install pypdf
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


APR_LINE_RE = re.compile(r"(\d+(?:\.\d+)?)%\s*(?:introductory|Introductory)?", re.IGNORECASE)
AFTER_THAT_RE = re.compile(r"After that\s+(\d+(?:\.\d+)?)%\s*(?:-\s*(\d+(?:\.\d+)?)%)?", re.IGNORECASE)
FOR_MONTHS_RE = re.compile(r"for\s+(\d+)\s+months", re.IGNORECASE)


def parse_pdf_apr_table(pdf_path: str) -> Dict[str, Any]:
    """
    Best-effort extractor for the “intro APR for X months; after that Y%-Z%” style lines
    in the Hapo disclosure.
    Returns a dict with raw text and extracted patterns for later normalization.
    """
    if PdfReader is None:
        raise RuntimeError("pypdf not installed. Run: pip install pypdf")

    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(p))
    full_text_parts: List[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        full_text_parts.append(txt)

    full_text = "\n".join(full_text_parts)

    # Extract “Intro APR … for X months … After that …”
    extracted: List[Dict[str, Any]] = []
    for line in full_text.splitlines():
        line_stripped = " ".join(line.split())
        if not line_stripped:
            continue

        if "Introductory APR" in line_stripped or "After that" in line_stripped:
            intro_apr = None
            intro_months = None
            after_min = None
            after_max = None

            m_intro = APR_LINE_RE.search(line_stripped)
            if m_intro:
                intro_apr = float(m_intro.group(1))

            m_months = FOR_MONTHS_RE.search(line_stripped)
            if m_months:
                intro_months = int(m_months.group(1))

            m_after = AFTER_THAT_RE.search(line_stripped)
            if m_after:
                after_min = float(m_after.group(1))
                after_max = float(m_after.group(2)) if m_after.group(2) else after_min

            if intro_apr is not None or after_min is not None:
                extracted.append(
                    {
                        "line": line_stripped,
                        "intro_apr": intro_apr,
                        "intro_months": intro_months,
                        "post_intro_apr_min": after_min,
                        "post_intro_apr_max": after_max,
                    }
                )

    return {
        "pdf_path": pdf_path,
        "extracted_lines": extracted,
        "raw_text_len": len(full_text),
    }