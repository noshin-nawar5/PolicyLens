"""RAG chat over a policy, built with LangChain + Chroma + a local Ollama LLM.

Flow: question -> embed -> retrieve top-k policy chunks -> prompt -> LLM.
If the LLM is unreachable (e.g. Ollama not running) `ask` still returns the
retrieved chunks so the retrieval half can be used and tested on its own.

LangChain's API changes often. Versions are pinned in requirements-lock.txt
once you freeze your environment.
"""
import os
from uuid import uuid4

SYSTEM = (
    "You answer questions about a company's security policy using ONLY the "
    "context provided. If the context does not contain the answer, say "
    "'The policy does not cover this.' Mention the section names you used. "
    "Do not use outside knowledge about the policy."
)

DEFAULT_LLM = os.environ.get("POLICYLENS_LLM", "llama3.2")
DEFAULT_EMBEDDER = "all-MiniLM-L6-v2"


class PolicyRAG:
    def __init__(self, chunks, model_name=DEFAULT_EMBEDDER, llm=DEFAULT_LLM, k=4):
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_ollama import ChatOllama

        if not chunks:
            raise ValueError("No policy chunks to index.")

        embeddings = HuggingFaceEmbeddings(
            model_name=f"sentence-transformers/{model_name}",
            encode_kwargs={"normalize_embeddings": True},
        )
        docs = [
            Document(page_content=c["text"], metadata={"section": c["section"]})
            for c in chunks
        ]
        store = Chroma.from_documents(
            docs, embeddings, collection_name=f"policy_{uuid4().hex[:8]}"
        )
        self.retriever = store.as_retriever(search_kwargs={"k": k})

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )
        self.chain = prompt | ChatOllama(model=llm, temperature=0) | StrOutputParser()

    def retrieve(self, question):
        docs = self.retriever.invoke(question)
        return [{"section": d.metadata["section"], "text": d.page_content} for d in docs]

    def ask(self, question):
        """Return (answer, sources). sources = [{"section", "text"}, ...]."""
        sources = self.retrieve(question)
        context = "\n\n".join(f"[{s['section']}]\n{s['text']}" for s in sources)
        try:
            answer = self.chain.invoke({"context": context, "question": question})
        except Exception as exc:  # LLM server down, model not pulled, etc.
            answer = (
                "Could not reach the LLM "
                f"({type(exc).__name__}). Is Ollama running and the model pulled? "
                "Showing the retrieved policy sections below."
            )
        return answer, sources
