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


def chunk_markdown(text, min_chars=40, max_chars=1200):
    """Return a list of {"section": str, "text": str}.

    Blocks are separated by blank lines. Lines starting with '#' set the
    current section name. Blocks shorter than min_chars are dropped.
    """
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
            if len(piece) >= min_chars:
                chunks.append({"section": section, "text": piece})
    return chunks
