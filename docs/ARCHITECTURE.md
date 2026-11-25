# Architecture

## Components

| Module | Responsibility | Notes |
|---|---|---|
| `config.py` | Reads `config/standards.yaml`, loads parsed requirements | Paths are relative to the repo root |
| `ingest.py` | PDF to requirement list | pdfplumber text extraction, regex on dotted IDs, noise filters from config |
| `chunking.py` | Policy text to chunks | Splits on blank lines, tracks `#` headings, splits very long blocks by sentence |
| `gap.py` | Gap detection | sentence-transformers embeddings, cosine similarity, two thresholds |
| `rag.py` | Question answering | LangChain + Chroma (in-memory) + ChatOllama |
| `evaluate.py` | Metrics | Per-class precision/recall/F1, macro-F1, threshold sweep |
| `cli.py` | Command line | `policylens <command>` |
| `app/streamlit_app.py` | Web UI | Gap report tab and chat tab |

## Gap detection

1. Embed every requirement text and every policy chunk with the same model, with normalised vectors.
2. Similarity matrix = requirements times chunks (dot product of normalised vectors equals cosine similarity).
3. For each requirement, take the highest-scoring chunk. Score at or above the covered threshold gives `covered`; at or above the partial threshold gives `partial`; otherwise `gap`.

The default thresholds (0.55 and 0.40) are placeholders. Tune them with `policylens eval --sweep`.

**Known weakness:** this measures topical similarity only. A planned improvement is a second step where an LLM reads the requirement and the matched chunk and judges whether the chunk actually states the control.

## RAG chat

1. Chunks are embedded and stored in a Chroma collection (in-memory, unique name per instance).
2. A question retrieves the top 4 chunks.
3. The prompt tells the model to answer only from the supplied context and to say "The policy does not cover this." otherwise.
4. The answer is shown with the retrieved sections so a reviewer can check it.
5. If the LLM cannot be reached, the app still shows the retrieved sections.

## Design choices

- **Plain code for gap detection, LangChain for RAG.** Gap detection is a matrix product; a framework adds nothing. RAG is what LangChain is built for.
- **Local-first.** Embeddings and the LLM run on the user's machine, so policy text stays local.
- **Config-driven standards.** Adding a standard is a config entry plus parser checks, not new code.
- **Tests use a fake embedder.** CI never downloads models.
