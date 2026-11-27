"""LLM verification pass: does the policy state EVERY element of a requirement?

Embedding similarity finds the right topic but cannot tell "covered" from
"partial". Here, for each requirement we retrieve the top-k policy chunks and
ask a local LLM to split the requirement into elements and say, element by
element, whether the excerpts state a control, with quoted evidence.

Safeguards:
* the status is derived by code from the elements (all stated = covered,
  none = gap, otherwise partial), not taken from the model's opinion;
* an element only counts as stated if its quoted evidence really appears in
  the retrieved policy text (blocks invented quotes).
Small local models can still be wrong, so treat this as a second opinion.
"""
import json
import re

import numpy as np
import pandas as pd

from .gap import DEFAULT_MODEL, get_embedder, similarity_matrix

SYSTEM_V1 = (
    "You are a careful compliance reviewer. You get one requirement from a "
    "security standard and excerpts from a company policy. "
    "Split the requirement into its separate checkable elements (each bullet "
    "or distinct obligation is one element; if the requirement offers "
    "alternatives joined by OR, treat the whole OR as one element). "
    "For each element decide whether the excerpts explicitly state a control "
    "that satisfies it. Vague or generic wording (for example 'be secure' or "
    "'in a timely manner') does NOT satisfy an element. Use ONLY the excerpts, "
    "never outside knowledge. Reply with JSON only, in this form: "
    '{"elements": [{"element": "short description", "stated": true, '
    '"evidence": "exact words copied from the excerpts, or empty if not stated"}]}'
)

SYSTEM_V2 = (
    "You are a careful compliance reviewer. You get one requirement from a "
    "security standard and excerpts from a company policy. "
    "Step 1: split the requirement into at most 5 separate obligations. "
    "Exceptions ('except', 'unless', 'where ... is ...') and examples belong to "
    "the obligation they modify; they are NOT separate obligations. If the "
    "requirement offers alternatives joined by OR, treat the whole OR as one "
    "obligation. "
    "Step 2: for each obligation, find a sentence in the excerpts that "
    "explicitly states a control satisfying it. A stricter policy statement "
    "also satisfies it (for example 'must never' satisfies 'must not, except "
    "when ...'). "
    "Evidence must be copied word for word from the excerpts. If you cannot "
    "copy such a sentence, set stated to false and evidence to an empty "
    "string. Vague or generic wording (for example 'be secure' or 'in a "
    "timely manner') does NOT satisfy an obligation. Use ONLY the excerpts. "
    "Reply with JSON only, in this form: "
    '{"elements": [{"element": "short description", "stated": true, '
    '"evidence": "sentence copied from the excerpts"}]}'
)

PROMPTS = {"v1": SYSTEM_V1, "v2": SYSTEM_V2}

MIN_EVIDENCE_CHARS = 12


def _norm(s):
    return re.sub(r"\W+", " ", str(s).lower()).strip()


def parse_llm_json(text):
    text = re.sub(r"```(?:json)?", "", str(text)).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def check_elements(raw_elements, context):
    """An element counts as stated only if the model says so AND its evidence is in the text."""
    ctx, out = _norm(context), []
    for e in raw_elements or []:
        if not isinstance(e, dict):
            continue
        evidence = str(e.get("evidence", "")).strip()
        said = bool(e.get("stated"))
        ev = _norm(evidence)
        found = len(ev) >= MIN_EVIDENCE_CHARS and ev in ctx
        out.append(
            {
                "element": str(e.get("element", ""))[:200],
                "stated": said and found,
                "llm_said_stated": said,
                "evidence_found": found,
                "evidence": evidence if said else "",
            }
        )
    return out


def derive_status(elements):
    if not elements:
        return "error"
    n = sum(e["stated"] for e in elements)
    return "covered" if n == len(elements) else ("gap" if n == 0 else "partial")


def verify_requirement(req, context, call, system=SYSTEM_V1):
    """call(system, user) -> str. Returns a dict describing the verdict."""
    user = f"Requirement {req['req_id']}:\n{req['text']}\n\nPolicy excerpts:\n{context}"
    data = parse_llm_json(call(system, user))  
    raw = data.get("elements", []) if isinstance(data, dict) else []
    elements = check_elements(raw, context)
    n, s = len(elements), sum(e["stated"] for e in elements)
    return {
        "status": derive_status(elements),
        "score": round(s / n, 3) if n else 0.0,  # fraction of elements stated
        "n_elements": n,
        "n_stated": s,
        "elements": elements,
    }


def verify_policy(reqs, chunks, call, model_name=DEFAULT_MODEL, top_k=3,
                  embedder=None, progress=print, prompt="v1"):
    if not reqs or not chunks:
        raise ValueError("Need requirements and policy chunks.")
    embedder = embedder or get_embedder(model_name)
    sims = similarity_matrix(reqs, chunks, embedder)
    rows = []
    for i, req in enumerate(reqs):
        top = np.argsort(-sims[i])[:top_k]
        context = "\n\n".join(f"[{chunks[j]['section']}] {chunks[j]['text']}" for j in top)
        res = verify_requirement(req, context, call, PROMPTS[prompt]) 
        if progress:
            progress(f"{req['req_id']:<8} {res['status']:<8} {res['n_stated']}/{res['n_elements']} elements stated")
        rows.append(
            {
                "standard": req.get("standard", ""),
                "req_id": req["req_id"],
                "title": req["title"],
                "status": res["status"],
                "score": res["score"],
                "n_elements": res["n_elements"],
                "n_stated": res["n_stated"],
                "sections": "; ".join(dict.fromkeys(chunks[j]["section"] for j in top)),
                "elements": json.dumps(res["elements"], ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def ollama_caller(model="llama3.2"):
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=model, temperature=0, format="json")

    def call(system, user):
        return llm.invoke([("system", system), ("human", user)]).content

    return call