"""Split a markdown/plain-text policy into chunks with their section heading."""
import re


def _split_long(block, max_chars):
    """Split an over-long block on sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", block)
    pieces, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            pieces.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def chunk_markdown(text, min_chars=40, max_chars=1200, mode="paragraph"):
    """Return a list of {"section": str, "text": str}.

    mode="paragraph": one chunk per blank-line separated block.
    mode="sentence":  one chunk per sentence (finer, for single-idea matching).
    Lines starting with '#' set the current section name. Chunks shorter than
    min_chars are dropped (20 chars in sentence mode).
    """
    if mode not in ("paragraph", "sentence"):
        raise ValueError("mode must be 'paragraph' or 'sentence'")
    min_len = min_chars if mode == "paragraph" else 20
    chunks, section = [], "Untitled"
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            first, _, rest = block.partition("\n")
            section = first.lstrip("# ").strip() or section
            block = rest.strip()
            if not block:
                continue
        for piece in _split_long(block, max_chars):
            parts = re.split(r"(?<=[.!?])\s+", piece) if mode == "sentence" else [piece]
            for part in parts:
                part = part.strip()
                if len(part) >= min_len:
                    chunks.append({"section": section, "text": part})
    return chunks