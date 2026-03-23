"""
Agent Orchestrator for Tastyz Bakery AI System

Central coordination hub using LangGraph to:
1. Route user queries to appropriate agents
2. Manage conversation context and state
3. Handle tool calls and external integrations
4. Track tokens and costs

Graph Flow:
  route_intent → [rag_agent | recommendation_agent | order_agent] → response
"""

import json
import logging
from typing import Any, Literal, TypedDict

from django.conf import settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from knowledge_base.loader import get_retriever
from .prompt_loader import render_prompt
from .rag_agent import build_rag_agent, ask_rag_agent
from .recommendation_agent import build_recommendation_agent, get_recommendation

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Orchestrator State
# ──────────────────────────────────────────────────────────────


class OrchestratorState(TypedDict):
    """Central state managed by the orchestrator."""

    user_id: str
    user_message: str
    conversation_history: list[dict]
    intent: Literal["faq", "recommendation", "order", "unknown"]
    agent_type: str
    response: str
    tokens_used: int
    cost: float
    error: str | None


# ──────────────────────────────────────────────────────────────
# Intent Router Node
# ──────────────────────────────────────────────────────────────


def make_intent_router(openai_api_key: str):
    """
    Create a stateless intent classification node.
    Routes user queries to appropriate agent.
    """

    def route_intent(state: OrchestratorState) -> dict[str, Any]:
        """Classify user intent and route to appropriate agent."""
        logger.info("Routing query for user %s", state["user_id"])

        llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.0,
        )

        routing_prompt = render_prompt(
            "routing.j2",
            user_message=state["user_message"],
            history=state.get("conversation_history", [])[-5:],  # Last 5 messages
        )

        messages = [SystemMessage(content=routing_prompt)]
        response = llm.invoke(messages)

        try:
            intent_data = json.loads(response.content)
            intent = intent_data.get("intent", "unknown")
            logger.info("Intent classified: %s", intent)
            return {
                "intent": intent,
                "agent_type": intent,
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse intent response, defaulting to FAQ")
            return {
                "intent": "faq",
                "agent_type": "rag_agent",
            }

    return route_intent


# ──────────────────────────────────────────────────────────────
# Agent Wrapper Nodes
# ──────────────────────────────────────────────────────────────


def make_rag_agent_node(retriever, openai_api_key: str):
    """Wrapper for RAG agent."""
    rag_graph = build_rag_agent(
        retriever=retriever,
        openai_api_key=openai_api_key,
        model="gpt-4o-mini",
        temperature=0.3,
    )

    def rag_node(state: OrchestratorState) -> dict[str, Any]:
        logger.info("Executing RAG agent for query: %s", state["user_message"][:50])
        try:
            answer = ask_rag_agent(
                rag_graph,
                question=state["user_message"],
                history=state.get("conversation_history", [])[-5:],
            )
            return {
                "response": answer,
                "agent_type": "rag_agent",
                "tokens_used": 0,  # TODO: track actual token usage
                "cost": 0.0,
            }
        except Exception as e:
            logger.error("RAG agent error: %s", str(e))
            return {
                "response": "I encountered an error while searching the knowledge base. Please try again.",
                "agent_type": "rag_agent",
                "error": str(e),
            }

    return rag_node


def make_recommendation_node(openai_api_key: str):
    """Wrapper for recommendation agent."""
    rec_graph = build_recommendation_agent(
        openai_api_key=openai_api_key,
        model="gpt-4o-mini",
        temperature=0.5,
    )

    def rec_node(state: OrchestratorState) -> dict[str, Any]:
        logger.info("Executing recommendation agent")
        try:
            recommendation = get_recommendation(rec_graph, state["user_message"])
            return {
                "response": recommendation,
                "agent_type": "recommendation_agent",
                "tokens_used": 0,
                "cost": 0.0,
            }
        except Exception as e:
            logger.error("Recommendation agent error: %s", str(e))
            return {
                "response": "I couldn't generate recommendations at this time. Please try again.",
                "agent_type": "recommendation_agent",
                "error": str(e),
            }

    return rec_node


def fallback_node(state: OrchestratorState) -> dict[str, Any]:
    """Fallback for unknown intents."""
    logger.warning("Unknown intent, using fallback response")
    return {
        "response": (
            "I'm not sure how to help with that. Try asking me about our products, "
            "getting recommendations, or placing an order."
        ),
        "agent_type": "fallback",
    }


# ──────────────────────────────────────────────────────────────
# Conditional Routing
# ──────────────────────────────────────────────────────────────


def should_use_rag(state: OrchestratorState) -> str:
    """Route FAQ queries to RAG agent."""
    return "rag" if state["intent"] == "faq" else END


def should_use_recommendation(state: OrchestratorState) -> str:
    """Route recommendation queries."""
    return "recommendation" if state["intent"] == "recommendation" else END


def should_use_order(state: OrchestratorState) -> str:
    """Route order queries."""
    # TODO: Uncomment when order agent is ready
    # return "order" if state["intent"] == "order" else END
    return END


# ──────────────────────────────────────────────────────────────
# Build and Compile Orchestrator
# ──────────────────────────────────────────────────────────────


def build_agent_orchestrator(openai_api_key: str):
    """
    Build the main agent orchestrator graph.

    Returns:
        Compiled LangGraph that orchestrates all agents.
    """
    logger.info("Building agent orchestrator")

    # Initialize retriever
    retriever = get_retriever(
        persist_dir=settings.CHROMA_PERSIST_DIR,
        api_key=openai_api_key,
        embedding_model=settings.OPENAI_EMBEDDING_MODEL,
        k=4,
    )

    builder = StateGraph(OrchestratorState)

    # Add nodes
    builder.add_node("route_intent", make_intent_router(openai_api_key))
    builder.add_node("rag", make_rag_agent_node(retriever, openai_api_key))
    builder.add_node("recommendation", make_recommendation_node(openai_api_key))
    builder.add_node("fallback", fallback_node)

    # Set entry
    builder.set_entry_point("route_intent")

    # Add conditional edges from router
    builder.add_conditional_edges(
        "route_intent",
        lambda state: (
            "rag"
            if state["intent"] == "faq"
            else (
                "recommendation"
                if state["intent"] == "recommendation"
                else "fallback"
            )
        ),
    )

    # All agents route to END
    builder.add_edge("rag", END)
    builder.add_edge("recommendation", END)
    builder.add_edge("fallback", END)

    graph = builder.compile()
    logger.info("Agent orchestrator compiled successfully")
    return graph


# ──────────────────────────────────────────────────────────────
# Public Interface
# ──────────────────────────────────────────────────────────────


def process_user_query(
    graph,
    user_id: str,
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Process a user query through the agent orchestrator.

    Args:
        graph: Compiled orchestrator graph
        user_id: Unique user identifier
        user_message: The user's message/query
        conversation_history: Previous messages (default: empty list)

    Returns:
        {
            "response": str,           # Agent's response
            "agent_type": str,         # Which agent handled it
            "tokens_used": int,        # Approximate token count
            "cost": float,             # Estimated cost in USD
            "error": str | None,       # Error message if any
        }
    """
    state: OrchestratorState = {
        "user_id": user_id,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "intent": "unknown",
        "agent_type": "unknown",
        "response": "",
        "tokens_used": 0,
        "cost": 0.0,
        "error": None,
    }

    try:
        result = graph.invoke(state)
        logger.info(
            "Query processed | user=%s | agent=%s | tokens=%d",
            user_id,
            result.get("agent_type"),
            result.get("tokens_used", 0),
        )
        return {
            "response": result.get("response", ""),
            "agent_type": result.get("agent_type", "unknown"),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost", 0.0),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error("Orchestrator error: %s", str(e), exc_info=True)
        return {
            "response": "An unexpected error occurred. Please try again later.",
            "agent_type": "error",
            "tokens_used": 0,
            "cost": 0.0,
            "error": str(e),
        }
