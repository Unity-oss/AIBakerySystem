"""
Sales Analysis Agent for Tastyz Bakery.

LangGraph graph: load_orders → analyse → generate_report → END

Reads the orders Excel file, computes summary stats,
renders the sales_report.j2 Jinja2 prompt, and calls the LLM
to produce a human-readable daily sales report.
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .prompt_loader import render_prompt

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────


class SalesState(TypedDict):
    excel_path: str
    orders_json: str
    total_orders: int
    date_range: str
    report_date: str
    report: str


# ──────────────────────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────────────────────


def load_orders(state: SalesState) -> dict[str, Any]:
    """Load today's orders from the Excel file."""
    try:
        import pandas as pd

        path = Path(state["excel_path"])
        if not path.exists():
            logger.warning("Orders file not found: %s", path)
            return {
                "orders_json": "[]",
                "total_orders": 0,
                "date_range": str(date.today()),
            }

        df = pd.read_excel(path)
        # Filter to today's orders if Order Date column exists
        if "Order Date" in df.columns:
            today_str = str(date.today())
            today_df = df[df["Order Date"].astype(str) == today_str]
        else:
            today_df = df

        orders_json = today_df.to_json(orient="records", default_handler=str)
        logger.info("Loaded %d orders for today", len(today_df))
        return {
            "orders_json": orders_json,
            "total_orders": len(today_df),
            "date_range": str(date.today()),
        }

    except Exception as exc:
        logger.error("Failed to load orders: %s", exc)
        return {"orders_json": "[]", "total_orders": 0, "date_range": str(date.today())}


def make_report_node(llm: ChatOpenAI):
    def generate_report(state: SalesState) -> dict[str, Any]:
        prompt_text = render_prompt(
            "sales_report.j2",
            orders_json=state["orders_json"],
            total_orders=state["total_orders"],
            date_range=state["date_range"],
            report_date=state["report_date"],
        )
        logger.debug("Sales agent calling LLM")
        response = llm.invoke([HumanMessage(content=prompt_text)])
        report = response.content.strip()
        logger.info("Sales report generated | length=%d chars", len(report))
        return {"report": report}

    return generate_report


# ──────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────


def build_sales_agent(
    openai_api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
):
    llm = ChatOpenAI(api_key=openai_api_key, model=model, temperature=temperature)

    builder = StateGraph(SalesState)
    builder.add_node("load_orders", load_orders)
    builder.add_node("generate_report", make_report_node(llm))

    builder.set_entry_point("load_orders")
    builder.add_edge("load_orders", "generate_report")
    builder.add_edge("generate_report", END)

    graph = builder.compile()
    logger.info("Sales agent graph compiled")
    return graph


def run_sales_report(graph, excel_path: str) -> str:
    """Run the sales agent and return the report string."""
    state: SalesState = {
        "excel_path": excel_path,
        "orders_json": "",
        "total_orders": 0,
        "date_range": "",
        "report_date": str(date.today()),
        "report": "",
    }
    result = graph.invoke(state)
    return result["report"]
