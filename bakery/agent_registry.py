"""
Agent registry for Tastyz Bakery.

Initialises all LangGraph agents once on first use (lazy init)
so Django can start without requiring all AI deps to be ready.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_rag_agent = None
_order_agent = None
_recommendation_agent = None
_sales_agent = None
_orchestrator_graph = None


def _get_settings():
    from django.conf import settings

    return settings


def get_rag_agent():
    global _rag_agent
    if _rag_agent is None:
        from agents.rag_agent import build_rag_agent
        from knowledge_base.loader import get_retriever

        s = _get_settings()
        retriever = get_retriever(
            persist_dir=s.CHROMA_PERSIST_DIR,
            api_key=s.OPENAI_API_KEY,
            embedding_model=s.OPENAI_EMBEDDING_MODEL,
        )
        _rag_agent = build_rag_agent(
            retriever=retriever,
            openai_api_key=s.OPENAI_API_KEY,
            model=s.OPENAI_MODEL,
        )
        logger.info("RAG agent initialised")
    return _rag_agent


def get_order_agent():
    global _order_agent
    if _order_agent is None:
        from agents.order_agent import build_order_agent

        s = _get_settings()
        _order_agent = build_order_agent(
            openai_api_key=s.OPENAI_API_KEY,
            excel_path=Path(s.ORDERS_EXCEL_PATH),
            model=s.OPENAI_MODEL,
        )
        logger.info("Order agent initialised")
    return _order_agent


def get_recommendation_agent():
    global _recommendation_agent
    if _recommendation_agent is None:
        from agents.recommendation_agent import build_recommendation_agent

        s = _get_settings()
        _recommendation_agent = build_recommendation_agent(
            openai_api_key=s.OPENAI_API_KEY,
            model=s.OPENAI_MODEL,
        )
        logger.info("Recommendation agent initialised")
    return _recommendation_agent


def get_sales_agent():
    global _sales_agent
    if _sales_agent is None:
        from agents.sales_agent import build_sales_agent

        s = _get_settings()
        _sales_agent = build_sales_agent(
            openai_api_key=s.OPENAI_API_KEY,
            model=s.OPENAI_MODEL,
        )
        logger.info("Sales agent initialised")
    return _sales_agent


def get_orchestrator():
    """Initialize and return the main agent orchestrator (LangGraph)."""
    global _orchestrator_graph
    if _orchestrator_graph is None:
        from agents.agent_orchestrator import build_agent_orchestrator

        s = _get_settings()
        _orchestrator_graph = build_agent_orchestrator(
            openai_api_key=s.OPENAI_API_KEY,
        )
        logger.info("Agent orchestrator initialised")
    return _orchestrator_graph
