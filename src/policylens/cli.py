"""Command-line interface: `policylens <command>` (run from the repo root)."""
import argparse
from pathlib import Path

import pandas as pd

from .chunking import chunk_markdown
from .config import load_requirements


def _read_policy(path, mode="paragraph"):
    return chunk_markdown(Path(path).read_text(encoding="utf-8"), mode=mode)


def cmd_ingest(a):
    from .ingest import ingest

    ingest(a.standard, debug=a.debug)


def cmd_gap(a):
    from .gap import detect_gaps

    df = detect_gaps(
        load_requirements(a.standard),
        _read_policy(a.policy, a.chunk_mode),
        model_name=a.model,
        covered_th=a.covered,
        partial_th=a.partial,
    )
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(df[["req_id", "status", "score", "best_section"]].to_string(index=False))
    print("\n" + df["status"].value_counts().to_string())
    print(f"\nFull report: {out}")


def cmd_verify(a):
    from .verify import ollama_caller, verify_policy

    reqs = load_requirements(a.standard)
    if a.only:
        wanted = {x.strip() for x in a.only.split(",")}
        reqs = [r for r in reqs if r["req_id"] in wanted]
    try:
        df = verify_policy(
            reqs,
            _read_policy(a.policy, a.chunk_mode),
            ollama_caller(a.llm),
            model_name=a.model,
            top_k=a.top_k,
            prompt=a.prompt,
        )
    except Exception as exc:  # most often: Ollama not installed/running or model not pulled
        raise SystemExit(
            f"Verification failed ({type(exc).__name__}: {exc}).\n"
            f"Is Ollama running and the model pulled? Try: ollama pull {a.llm}"
        )
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print("\n" + df["status"].value_counts().to_string())
    print(f"\nFull report: {out}")
    print(f"Score it with: policylens eval --report {out}")


def cmd_init_key(a):
    from .evaluate import init_answer_key

    path = init_answer_key(load_requirements(a.standard), a.out)
    print(f"Blank answer key written to {path}. Fill the 'label' column.")


def cmd_eval(a):
    from .evaluate import evaluate, format_metrics, load_key, sweep_thresholds

    report, key = pd.read_csv(a.report, dtype={"req_id": str}), load_key(a.key)
    m, _ = evaluate(report, key)
    print(format_metrics(m))
    if a.sweep:
        print("\nTop threshold settings:")
        print(sweep_thresholds(report, key).head(10).to_string(index=False))


def cmd_ask(a):
    from .rag import PolicyRAG

    rag = PolicyRAG(_read_policy(a.policy, a.chunk_mode), llm=a.llm)
    answer, sources = rag.ask(a.question)
    print(answer)
    print("\nSources:")
    for s in sources:
        print(f"- [{s['section']}] {s['text'][:120]}...")


def _common(s, with_model=True):
    s.add_argument("--policy", default="data/policies/finco_policy.md")
    s.add_argument("--chunk-mode", choices=["paragraph", "sentence"], default="paragraph")
    if with_model:
        s.add_argument("--model", default="all-MiniLM-L6-v2", help="embedding model")


def main(argv=None):
    p = argparse.ArgumentParser(prog="policylens")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="parse a standard PDF into JSON")
    s.add_argument("standard")
    s.add_argument("--debug", action="store_true", help="also dump raw PDF lines")
    s.set_defaults(fn=cmd_ingest)

    s = sub.add_parser("gap", help="run embedding-based gap detection")
    s.add_argument("--standard", default="pci-dss-4")
    _common(s)
    s.add_argument("--covered", type=float, default=0.55)
    s.add_argument("--partial", type=float, default=0.40)
    s.add_argument("--out", default="data/processed/gap_report.csv")
    s.set_defaults(fn=cmd_gap)

    s = sub.add_parser("verify", help="LLM check of each requirement element (needs Ollama)")
    s.add_argument("--standard", default="pci-dss-4")
    _common(s)
    s.add_argument("--llm", default="llama3.2")
    s.add_argument("--top-k", type=int, default=3, help="policy chunks shown to the LLM")
    s.add_argument("--prompt", choices=["v1", "v2"], default="v1", help="instruction wording")
    s.add_argument("--only", help="comma-separated req ids, e.g. 6.5.5,6.4.1")
    s.add_argument("--out", default="data/processed/verified_report.csv")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("init-key", help="create a blank answer key to label by hand")
    s.add_argument("standard")
    s.add_argument("--out", default="data/eval/answer_key.csv")
    s.set_defaults(fn=cmd_init_key)

    s = sub.add_parser("eval", help="score a report against the answer key")
    s.add_argument("--report", default="data/processed/gap_report.csv")
    s.add_argument("--key", default="data/eval/answer_key.csv")
    s.add_argument("--sweep", action="store_true", help="try threshold combinations")
    s.set_defaults(fn=cmd_eval)

    s = sub.add_parser("ask", help="ask one question about a policy (needs Ollama)")
    s.add_argument("question")
    _common(s, with_model=False)
    s.add_argument("--llm", default="llama3.2")
    s.set_defaults(fn=cmd_ask)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()