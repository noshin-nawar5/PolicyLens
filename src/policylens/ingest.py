"""Turn a standard (PDF) into a list of requirements stored as JSON.

Each requirement is a dict: standard, req_id, title, text.

IMPORTANT: PDF layouts differ. The regex below expects lines that start with
a dotted requirement id, e.g. "6.4.1 Some requirement text". Always inspect
the output (and the --debug raw dump) and tune `noise_patterns` in
config/standards.yaml for headers and footers.
"""
import json
import re
from pathlib import Path

from .config import get_standard

REQ_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\s+(\S.*)$")


def extract_lines(pdf_path):
    import pdfplumber  # imported here so tests run without a PDF

    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(l.strip() for l in text.split("\n") if l.strip())
    return lines


def clean_lines(lines, noise_patterns=()):
    compiled = [re.compile(p) for p in noise_patterns]
    return [l for l in lines if not any(p.search(l) for p in compiled)]


def parse_requirements(lines, standard_id, include_top_level=None):
    """Group lines under the requirement id that precedes them.

    include_top_level: list like ["6"]; None or [] keeps everything.
    If an id appears twice (e.g. again in a testing-procedure table), the
    later text is appended to the first entry instead of creating a duplicate.
    """
    keep = set(include_top_level or [])
    reqs, by_id, current = [], {}, None
    for line in lines:
        m = REQ_RE.match(line)
        if m and (not keep or m.group(1).split(".")[0] in keep):
            rid, rest = m.group(1), m.group(2)
            if rid in by_id:
                current = by_id[rid]
                current["text"] += " " + rest
            else:
                current = {
                    "standard": standard_id,
                    "req_id": rid,
                    "title": rest,
                    "text": rest,
                }
                reqs.append(current)
                by_id[rid] = current
        elif m:
            # A requirement id from a section we are not keeping: stop
            # collecting so its text does not leak into the previous entry.
            current = None
        elif current:
            current["text"] += " " + line
    for r in reqs:
        r["text"] = re.sub(r"\s+", " ", r["text"]).strip()
    return reqs


def ingest(standard_id, debug=False):
    std = get_standard(standard_id)
    pdf_path = Path(std["pdf"])
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"{pdf_path} not found. Download the standard first (see docs/DATA.md)."
        )
    raw = extract_lines(pdf_path)
    lines = clean_lines(raw, std.get("noise_patterns", []))
    out = Path(std["output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    if debug:
        raw_path = out.with_suffix(".raw.txt")
        raw_path.write_text("\n".join(raw), encoding="utf-8")
        print(f"Raw extracted lines written to {raw_path}")
    reqs = parse_requirements(lines, std["id"], std.get("include_top_level"))
    out.write_text(json.dumps(reqs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(reqs)} requirements to {out}")
    if not reqs:
        print("WARNING: no requirements found. Check the raw dump and the regex.")
    return reqs
