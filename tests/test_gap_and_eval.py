import numpy as np
import pandas as pd
import pytest

from policylens.evaluate import evaluate, load_key, metrics, sweep_thresholds
from policylens.gap import detect_gaps, label_from_score


class FakeEmbedder:
    """Bag-of-words hashing embedder so tests need no model download."""

    def encode(self, texts, normalize_embeddings=True):
        out = np.zeros((len(texts), 64))
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, hash(w.strip(".,")) % 64] += 1
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


REQS = [
    {"standard": "s", "req_id": "1.1", "title": "code review", "text": "code review before merge"},
    {"standard": "s", "req_id": "1.2", "title": "firewall", "text": "web application firewall attacks"},
]
CHUNKS = [
    {"section": "Review", "text": "every code review happens before merge by a developer"},
    {"section": "Other", "text": "unrelated holiday schedule policy"},
]


def test_label_thresholds():
    assert label_from_score(0.7) == "covered"
    assert label_from_score(0.45) == "partial"
    assert label_from_score(0.1) == "gap"


def test_detect_gaps_picks_best_chunk():
    df = detect_gaps(REQS, CHUNKS, embedder=FakeEmbedder())
    assert df.loc[df.req_id == "1.1", "best_section"].iloc[0] == "Review"
    assert set(df.columns) >= {"req_id", "status", "score", "best_chunk"}


def test_detect_gaps_rejects_empty_inputs():
    with pytest.raises(ValueError):
        detect_gaps([], CHUNKS, embedder=FakeEmbedder())
    with pytest.raises(ValueError):
        detect_gaps(REQS, [], embedder=FakeEmbedder())


def test_metrics_perfect_and_wrong():
    m = metrics(["gap", "covered"], ["gap", "covered"])
    assert m["accuracy"] == 1.0 and m["gap"]["recall"] == 1.0
    m = metrics(["gap", "gap"], ["covered", "covered"])
    assert m["gap"]["recall"] == 0.0 and m["accuracy"] == 0.0


def test_load_key_rejects_blank_labels(tmp_path):
    p = tmp_path / "key.csv"
    p.write_text("req_id,label\n1.1,\n")
    with pytest.raises(ValueError):
        load_key(p)


def test_sweep_finds_perfect_thresholds(tmp_path):
    report = pd.DataFrame({"req_id": ["a", "b", "c"], "score": [0.9, 0.5, 0.1]})
    p = tmp_path / "key.csv"
    p.write_text("req_id,label\na,covered\nb,partial\nc,gap\n")
    res = sweep_thresholds(report, load_key(p))
    assert res.iloc[0]["accuracy"] == 1.0


def test_evaluate_merges_on_req_id(tmp_path):
    report = pd.DataFrame(
        {"req_id": ["a", "b"], "status": ["covered", "gap"], "score": [0.8, 0.1]}
    )
    p = tmp_path / "key.csv"
    p.write_text("req_id,label\na,covered\nb,gap\n")
    m, merged = evaluate(report, load_key(p))
    assert m["accuracy"] == 1.0 and len(merged) == 2
