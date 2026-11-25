"""Turn a standard (PDF) into a list of requirements stored as JSON.

Each requirement is a dict with: standard, req_id, title, text,
section_id, section_title, and (when present) customized_objective and
applicability_notes.

Two modes, chosen per standard in config/standards.yaml:

* layout mode (``layout:`` block present): for PDFs laid out as a table with
  columns (Requirement | Testing Procedures | Guidance), such as PCI DSS.
  Only the left column is read, so testing procedures and guidance do not
  get mixed into the requirement text.
* plain mode (no ``layout:`` block): reads lines in normal order and groups
  them under dotted ids like "6.4.1". Works for single-column documents.

PDF layouts differ. Always inspect the output and the --debug dump.
"""
import json
import re
from pathlib import Path

from .config import get_standard

# ---- shared ---------------------------------------------------------------
REQ_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\s+(\S.*)$")  # plain mode
ID3_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){2,3})\s+(\S.*)$")  # 6.4.1 / 6.2.3.1
HDR2_RE = re.compile(r"^(\d{1,2}\.\d{1,2})\s+(\S.*)$")  # section row: 6.4 Title
HDR2_ID = re.compile(r"^\d{1,2}\.\d{1,2}$")

# Sub-headings inside the left column -> field they start
SUBHEADS = {
    "defined approach requirements": "text",
    "customized approach objective": "customized_objective",
    "applicability notes": "applicability_notes",
}


def clean_lines(lines, noise_patterns=()):
    compiled = [re.compile(p) for p in noise_patterns]
    return [l for l in lines if not any(p.search(l) for p in compiled)]


def _tidy(text):
    text = text.replace("\u2022", " - ")
    return re.sub(r"\s+", " ", text).strip()


def _short_title(text, limit=110):
    first = re.split(r"(?<=[.:])\s", text, maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 3].rstrip() + "..."


# ---- plain mode -----------------------------------------------------------
def extract_lines(pdf_path):
    import pdfplumber  # imported here so tests run without a PDF

    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(l.strip() for l in text.split("\n") if l.strip())
    return lines


def parse_requirements(lines, standard_id, include_top_level=None):
    """Group lines under the requirement id that precedes them (plain mode).

    include_top_level: list like ["6"]; None or [] keeps everything.
    If an id appears twice, the later text is appended to the first entry.
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
            current = None  # id from a section we are not keeping
        elif current:
            current["text"] += " " + line
    for r in reqs:
        r["text"] = re.sub(r"\s+", " ", r["text"]).strip()
    return reqs


# ---- layout mode ----------------------------------------------------------
def extract_layout_items(pdf_path, layout, noise_patterns=()):
    """Return [(kind, text)] in reading order; kind is 'header' or 'left'.

    'header' = full-width section row such as "6.4 Public-facing web ...".
    'left'   = a visual line of the left column only.
    layout keys: left_col [x_min, x_max], top, bottom (y crop that removes the
    running header/footer), pages [first, last] (1-based, inclusive).
    """
    import pdfplumber

    left_min, left_max = layout.get("left_col", [72, 293])
    top_min = layout.get("top", 108)
    bottom_max = layout.get("bottom", 540)
    first, last = layout.get("pages") or [None, None]
    noise = [re.compile(p) for p in noise_patterns]

    items = []
    with pdfplumber.open(pdf_path) as pdf:
        start = (first or 1) - 1
        end = last or len(pdf.pages)
        for page in pdf.pages[start:end]:
            words = [
                w for w in page.extract_words() if top_min <= w["top"] <= bottom_max
            ]
            words.sort(key=lambda w: (w["top"], w["x0"]))
            lines, cur, cur_top = [], [], None
            for w in words:
                if cur and abs(w["top"] - cur_top) > 3:
                    lines.append(cur)
                    cur = []
                if not cur:
                    cur_top = w["top"]
                cur.append(w)
            if cur:
                lines.append(cur)
            for ws in lines:
                ws.sort(key=lambda w: w["x0"])
                full = " ".join(w["text"] for w in ws)
                if HDR2_ID.match(ws[0]["text"]) and ws[0]["x0"] < left_min + 25:
                    items.append(("header", full))
                    continue
                left = " ".join(w["text"] for w in ws if w["x0"] < left_max - 1)
                if left and not any(p.search(left) for p in noise):
                    items.append(("left", left))
    return items


def parse_layout_items(items, standard_id, include_top_level=None):
    """Build requirements from (kind, text) items. Pure function (testable).

    A new requirement starts only on the line right after the sub-heading
    "Defined Approach Requirements", so ids mentioned inside wrapped text are
    never mistaken for new requirements.
    """
    keep = set(include_top_level or [])
    reqs, by_id = [], {}
    current, field, expect_id = None, None, False
    section_id, section_title = "", ""

    for kind, text in items:
        text = text.strip()
        if kind == "header":
            m = HDR2_RE.match(text)
            section_id, section_title = (m.group(1), m.group(2)) if m else ("", text)
            current, field, expect_id = None, None, False
            continue
        low = text.lower()
        if low in SUBHEADS:
            field = SUBHEADS[low]
            expect_id = field == "text"
            continue
        if expect_id:
            expect_id = False
            m = ID3_RE.match(text)
            if m and (not keep or m.group(1).split(".")[0] in keep):
                rid = m.group(1)
                if rid in by_id:  # defensive: repeated id
                    current = by_id[rid]
                    current["text"] += " " + m.group(2)
                else:
                    current = {
                        "standard": standard_id,
                        "req_id": rid,
                        "title": "",
                        "text": m.group(2),
                        "section_id": section_id,
                        "section_title": section_title,
                        "customized_objective": "",
                        "applicability_notes": "",
                    }
                    reqs.append(current)
                    by_id[rid] = current
            else:
                current = None
            continue
        if current is not None and field:
            current[field] += " " + text

    for r in reqs:
        for k in ("text", "customized_objective", "applicability_notes"):
            r[k] = _tidy(r[k])
        r["title"] = _short_title(r["text"])
        for k in ("customized_objective", "applicability_notes"):
            if not r[k]:
                del r[k]
    return reqs


# ---- entry point ----------------------------------------------------------
def ingest(standard_id, debug=False):
    std = get_standard(standard_id)
    pdf_path = Path(std["pdf"])
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"{pdf_path} not found. Download the standard first (see docs/DATA.md)."
        )
    out = Path(std["output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    noise = std.get("noise_patterns", [])
    keep = std.get("include_top_level")
    layout = std.get("layout")

    if layout:
        if not layout.get("pages"):
            print("WARNING: no layout.pages set; reading every page (slow, may add noise).")
        items = extract_layout_items(pdf_path, layout, noise)
        if debug:
            raw_path = out.with_suffix(".raw.txt")
            raw_path.write_text(
                "\n".join(f"[{k}] {t}" for k, t in items), encoding="utf-8"
            )
            print(f"Raw extracted lines written to {raw_path}")
        reqs = parse_layout_items(items, std["id"], keep)
    else:
        raw = extract_lines(pdf_path)
        if debug:
            raw_path = out.with_suffix(".raw.txt")
            raw_path.write_text("\n".join(raw), encoding="utf-8")
            print(f"Raw extracted lines written to {raw_path}")
        reqs = parse_requirements(clean_lines(raw, noise), std["id"], keep)

    out.write_text(json.dumps(reqs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(reqs)} requirements to {out}")
    if not reqs:
        print("WARNING: no requirements found. Check the raw dump and the layout settings.")
    return reqs