from policylens.chunking import chunk_markdown

POLICY = """# Title

## 1. Scope

This policy applies to all developers and contractors at the company.

## 2. Review

Every change must be reviewed by another developer before it is merged.

Tiny.

## 3. Long

""" + ("This is a sentence that repeats. " * 80)


def test_sections_are_tracked():
    chunks = chunk_markdown(POLICY)
    assert chunks[0]["section"] == "1. Scope"
    assert chunks[1]["section"] == "2. Review"


def test_short_blocks_are_dropped():
    assert all("Tiny." != c["text"] for c in chunk_markdown(POLICY))


def test_long_blocks_are_split():
    long_chunks = [c for c in chunk_markdown(POLICY, max_chars=500) if c["section"] == "3. Long"]
    assert len(long_chunks) > 1
    assert all(len(c["text"]) <= 600 for c in long_chunks)


def test_empty_text():
    assert chunk_markdown("") == []
