"""Embedding-based gap detection.

For every requirement we find the most similar policy chunk (cosine
similarity) and turn the score into a label using two thresholds.

Caveat: similarity measures topical closeness, not compliance. A chunk can
be about the same subject and still not satisfy the requirement.
"""
from functools import lru_cache

import numpy as np
import pandas as pd

DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_COVERED = 0.55  # placeholder: tune on your answer key
DEFAULT_PARTIAL = 0.40  # placeholder: tune on your answer key


def label_from_score(score, covered_th=DEFAULT_COVERED, partial_th=DEFAULT_PARTIAL):
    if score >= covered_th:
        return "covered"
    if score >= partial_th:
        return "partial"
    return "gap"


@lru_cache(maxsize=2)
def get_embedder(model_name=DEFAULT_MODEL):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def similarity_matrix(reqs, chunks, embedder):
    r = embedder.encode([x["text"] for x in reqs], normalize_embeddings=True)
    c = embedder.encode([x["text"] for x in chunks], normalize_embeddings=True)
    return np.asarray(r) @ np.asarray(c).T


def detect_gaps(
    reqs,
    chunks,
    model_name=DEFAULT_MODEL,
    covered_th=DEFAULT_COVERED,
    partial_th=DEFAULT_PARTIAL,
    embedder=None,
):
    """Return a DataFrame with one row per requirement.

    `embedder` can be any object with .encode(list_of_str, normalize_embeddings=True).
    """
    if not reqs:
        raise ValueError("No requirements loaded. Run `policylens ingest` first.")
    if not chunks:
        raise ValueError("The policy produced no chunks. Is the file empty?")
    embedder = embedder or get_embedder(model_name)
    sims = similarity_matrix(reqs, chunks, embedder)

    rows = []
    for i, req in enumerate(reqs):
        order = np.argsort(-sims[i])
        best = int(order[0])
        score = float(sims[i, best])
        top_sections = []
        for j in order[:3]:
            s = chunks[int(j)]["section"]
            if s not in top_sections:
                top_sections.append(s)
        rows.append(
            {
                "standard": req.get("standard", ""),
                "req_id": req["req_id"],
                "title": req["title"],
                "status": label_from_score(score, covered_th, partial_th),
                "score": round(score, 3),
                "best_section": chunks[best]["section"],
                "top_sections": "; ".join(top_sections),
                "best_chunk": chunks[best]["text"],
            }
        )
    return pd.DataFrame(rows)
