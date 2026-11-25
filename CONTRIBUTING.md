# Contributing

Issues and pull requests are welcome.

```bash
pip install -r requirements.txt
pytest
```

- Keep tests runnable without model downloads (use the fake embedder pattern in `tests/test_gap_and_eval.py`).
- Do not commit standards PDFs, text extracted from them, or any real company policy.
- Open an issue before large changes.
