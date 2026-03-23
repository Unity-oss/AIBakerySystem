"""
Product Recommendation Agent for Tastyz Bakery.

LangGraph graph: build_catalog → call_llm → END

The agent renders the recommendation.j2 Jinja2 prompt with the full
product catalog and the customer's request, then returns AI suggestions.
"""

import logging
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .prompt_loader import render_prompt

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Full product catalog (matches knowledge_base/price_list.txt)
# ──────────────────────────────────────────────────────────────

PRODUCT_CATALOG = """
=== CAKES (1KG / 2KG) ===
- Vanilla Sponge Cake   — 65,000 / 85,000 UGX
- Banana Cake           — 60,000 / 80,000 UGX
- Chocolate Cake        — 75,000 / 95,000 UGX
- Marble Cake           — 70,000 / 90,000 UGX
- Fruity Cake           — 85,000 / 100,000 UGX
- Lemon Cake            — 55,000 / 70,000 UGX
- Strawberry Cake       — 70,000 / 100,000 UGX
- Red Velvet Cake       — 90,000 / 120,000 UGX
- Black Forest Cake     — 100,000 / 150,000 UGX
- Carrot Cake           — 70,000 / 100,000 UGX

=== COOKIES (Small / Medium / Big Tin) ===
- Ginger Cookies        — 10,000 / 20,000 / 35,000 UGX
- Chocolate Cookies     — 15,000 / 25,000 / 30,000 UGX
- Coconut Cookies       — 10,000 / 20,000 / 30,000 UGX
- Butter Cookies        — 10,000 / 20,000 / 25,000 UGX
- Black & White Cookies — 10,000 / 20,000 / 25,000 UGX

=== FRESH PASTRIES (Small / Big) ===
- Country Loaf          — 5,000 / 10,000 UGX
- Burger Buns           — 1,000 / 2,000 UGX
- Donuts                — 2,000 / 3,000 UGX
- Chocolate Brownies    — 20,000 / 35,000 UGX
- Bread                 — 3,000 / 5,000 UGX
- Muffins               — 2,000 / 3,000 UGX
- Pizza                 — 35,000 / 40,000 UGX
- Cupcakes              — 20,000 / 30,000 UGX
- Cinnamon Rolls        — 2,000 / 5,000 UGX
"""


# ──────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────


class RecommendState(TypedDict):
    customer_request: str
    product_catalog: str
    recommendation: str


# ──────────────────────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────────────────────


def build_catalog(state: RecommendState) -> dict[str, Any]:
    return {"product_catalog": PRODUCT_CATALOG}


def make_recommend_node(llm: ChatOpenAI):
    def recommend(state: RecommendState) -> dict[str, Any]:
        prompt_text = render_prompt(
            "recommendation.j2",
            product_catalog=state["product_catalog"],
            customer_request=state["customer_request"],
        )
        logger.debug("Recommendation agent calling LLM")
        response = llm.invoke([HumanMessage(content=prompt_text)])
        return {"recommendation": response.content.strip()}

    return recommend


# ──────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────


def build_recommendation_agent(
    openai_api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.5,
):
    llm = ChatOpenAI(api_key=openai_api_key, model=model, temperature=temperature)

    builder = StateGraph(RecommendState)
    builder.add_node("build_catalog", build_catalog)
    builder.add_node("recommend", make_recommend_node(llm))

    builder.set_entry_point("build_catalog")
    builder.add_edge("build_catalog", "recommend")
    builder.add_edge("recommend", END)

    graph = builder.compile()
    logger.info("Recommendation agent graph compiled")
    return graph


def get_recommendation(graph, customer_request: str) -> str:
    """Run the recommendation agent and return the recommendation string."""
    state: RecommendState = {
        "customer_request": customer_request,
        "product_catalog": "",
        "recommendation": "",
    }
    result = graph.invoke(state)
    return result["recommendation"]
