"""
RAG Customer Support Agent for Tastyz Bakery.

Uses LangGraph to orchestrate:
  1. Retrieve relevant context from ChromaDB (FAQ + price list)
  2. Render the Jinja2 chatbot prompt with the context
  3. Call OpenAI to generate a grounded response

Graph: retrieve → generate
"""

import logging
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .prompt_loader import render_prompt

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# State schema
# ──────────────────────────────────────────────────────────────


class RAGState(TypedDict):
    question: str
    history: list[dict]
    context: str
    answer: str


# ──────────────────────────────────────────────────────────────
# Agent nodes
# ──────────────────────────────────────────────────────────────


def make_retrieve_node(retriever):
    """Return a node function that retrieves context from ChromaDB."""

    def retrieve(state: RAGState) -> dict[str, Any]:
        logger.debug("RAG retrieve | question=%s", state["question"])
        docs = retriever.invoke(state["question"])
        context = "\n\n".join(doc.page_content for doc in docs)
        logger.debug("Retrieved %d docs", len(docs))
        return {"context": context}

    return retrieve


def make_generate_node(llm: ChatOpenAI):
    """Return a node function that calls the LLM with the rendered Jinja2 prompt."""

    def generate(state: RAGState) -> dict[str, Any]:
        prompt_text = render_prompt(
            "chatbot_system.j2",
            context=state["context"],
            history=state.get("history", []),
            question=state["question"],
        )
        logger.debug("RAG generate | sending prompt to LLM")
        messages = [SystemMessage(content=prompt_text)]
        response = llm.invoke(messages)
        answer = response.content.strip()
        logger.info("RAG answer generated | length=%d chars", len(answer))
        return {"answer": answer}

    return generate


# ──────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────


def build_rag_agent(
    retriever,
    openai_api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
):
    """
    Build and compile the RAG LangGraph agent.

    Returns a compiled graph that accepts RAGState and returns updated state.
    """
    llm = ChatOpenAI(
        api_key=openai_api_key,
        model=model,
        temperature=temperature,
    )

    builder = StateGraph(RAGState)
    builder.add_node("retrieve", make_retrieve_node(retriever))
    builder.add_node("generate", make_generate_node(llm))

    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    graph = builder.compile()
    logger.info("RAG agent graph compiled successfully")
    return graph


# ──────────────────────────────────────────────────────────────
# Public helper
# ──────────────────────────────────────────────────────────────


def ask_rag_agent(
    graph,
    question: str,
    history: list[dict] | None = None,
) -> str:
    """
    Run the RAG agent and return the answer string.

    Args:
        graph: compiled LangGraph RAG agent
        question: customer's question
        history: list of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        Answer string
    """
    state: RAGState = {
        "question": question,
        "history": history or [],
        "context": "",
        "answer": "",
    }
    result = graph.invoke(state)
    return result["answer"]
