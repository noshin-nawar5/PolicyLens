"""PolicyLens web app. Run from the repo root: streamlit run app/streamlit_app.py"""
from pathlib import Path

import streamlit as st

from policylens.chunking import chunk_markdown
from policylens.config import get_standard, load_requirements, load_standards
from policylens.gap import DEFAULT_MODEL, detect_gaps, get_embedder

SAMPLE = Path("data/policies/finco_policy.md")
COLORS = {"covered": "#c8e6c9", "partial": "#fff3c4", "gap": "#ffcdd2"}

st.set_page_config(page_title="PolicyLens", layout="wide")
st.title("PolicyLens")
st.caption(
    "Compare a security policy with a public standard, then ask questions about it. "
    "A review aid, not an audit verdict."
)


@st.cache_resource(show_spinner="Loading embedding model...")
def embedder(name):
    return get_embedder(name)


@st.cache_resource(show_spinner="Indexing policy for chat...")
def build_rag(policy_text, model_name, llm):
    from policylens.rag import PolicyRAG

    return PolicyRAG(chunk_markdown(policy_text), model_name=model_name, llm=llm)


# ---- sidebar ---------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    standards = [s["id"] for s in load_standards()]
    std_id = st.selectbox("Standard", standards)
    model_name = st.selectbox(
        "Embedding model",
        [DEFAULT_MODEL, "all-mpnet-base-v2", "BAAI/bge-small-en-v1.5"],
    )
    covered = st.slider("Covered threshold", 0.2, 0.9, 0.55, 0.01)
    partial = st.slider("Partial threshold", 0.1, 0.8, 0.40, 0.01)
    llm = st.text_input("Ollama model", "llama3.2")
    if partial >= covered:
        st.warning("Partial threshold should be lower than covered.")

up = st.file_uploader("Upload a policy (.md or .txt)", type=["md", "txt"])
if up:
    policy_text = up.read().decode("utf-8", errors="ignore")
    st.info(f"Using uploaded file: {up.name}")
elif SAMPLE.exists():
    policy_text = SAMPLE.read_text(encoding="utf-8")
    st.info("Using the bundled fictional FinCo sample policy.")
else:
    st.stop()

try:
    reqs = load_requirements(std_id)
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

chunks = chunk_markdown(policy_text)
st.write(
    f"**{get_standard(std_id)['name']}**: {len(reqs)} requirements | "
    f"policy: {len(chunks)} chunks"
)

tab_gap, tab_chat = st.tabs(["Gap report", "Ask the policy"])

# ---- gap report ------------------------------------------------------------
with tab_gap:
    df = detect_gaps(
        reqs, chunks, model_name, covered, partial, embedder=embedder(model_name)
    )
    counts = df["status"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("Covered", int(counts.get("covered", 0)))
    c2.metric("Partial", int(counts.get("partial", 0)))
    c3.metric("Gap", int(counts.get("gap", 0)))

    view = df[["req_id", "title", "status", "score", "best_section"]]
    st.dataframe(
        view.style.map(
            lambda v: f"background-color: {COLORS.get(v, '')}", subset=["status"]
        ),
        width="stretch",
        hide_index=True,
    )
    pick = st.selectbox("Inspect a requirement", df["req_id"])
    row = df[df["req_id"] == pick].iloc[0]
    st.markdown(f"**Requirement {pick}**: {row['title']}")
    st.markdown(f"**Best matching policy text** ({row['best_section']}, score {row['score']}):")
    st.write(row["best_chunk"])
    st.caption(
        "High similarity means the policy talks about the same topic. "
        "It does not prove the requirement is met. Review matches manually."
    )
    st.download_button(
        "Download report (CSV)", df.to_csv(index=False), "gap_report.csv", "text/csv"
    )

# ---- chat ------------------------------------------------------------------
with tab_chat:
    st.write(
        "Example: *What does the policy say about code review?* or "
        "*Is anything said about web application firewalls?*"
    )
    q = st.text_input("Your question")
    if q:
        try:
            rag = build_rag(policy_text, model_name, llm)
            with st.spinner("Thinking..."):
                answer, sources = rag.ask(q)
            st.write(answer)
            with st.expander("Retrieved policy sections"):
                for s in sources:
                    st.markdown(f"**{s['section']}**")
                    st.write(s["text"])
        except ImportError as e:
            st.error(f"Missing dependency for chat: {e}. Run: pip install -e '.[ml]'")
