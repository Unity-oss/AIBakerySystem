"""
Order Processing Agent for Tastyz Bakery.

LangGraph graph:
  validate_input → call_llm → parse_response → export_excel → END

The agent:
  1. Renders the order_agent.j2 Jinja2 prompt with order details
  2. Calls the LLM to produce a JSON confirmation + internal note
  3. Parses the JSON response
  4. Appends the order to the Excel spreadsheet
"""

import json
import logging
from datetime import date
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


class OrderState(TypedDict):
    customer_name: str
    product: str
    size: str
    delivery_date: str
    delivery_address: str
    notes: str
    payment_method: str
    llm_response_raw: str
    status: str
    issues: list[str]
    customer_message: str
    internal_note: str
    excel_saved: bool


# ──────────────────────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────────────────────


def validate_input(state: OrderState) -> dict[str, Any]:
    """Basic validation before calling the LLM."""
    issues = []
    if not state.get("customer_name", "").strip():
        issues.append("Missing customer name.")
    if not state.get("product", "").strip():
        issues.append("Missing product selection.")
    if not state.get("delivery_date", "").strip():
        issues.append("Missing delivery date.")
    logger.debug("Order validation issues: %s", issues)
    return {"issues": issues}


def make_llm_node(llm: ChatOpenAI):
    def call_llm(state: OrderState) -> dict[str, Any]:
        prompt_text = render_prompt(
            "order_agent.j2",
            customer_name=state.get("customer_name", ""),
            product=state.get("product", ""),
            size=state.get("size", ""),
            delivery_date=state.get("delivery_date", ""),
            delivery_address=state.get("delivery_address", ""),
            notes=state.get("notes", ""),
            payment_method=state.get("payment_method", ""),
        )
        logger.debug("Order agent calling LLM")
        response = llm.invoke([HumanMessage(content=prompt_text)])
        return {"llm_response_raw": response.content.strip()}

    return call_llm


def parse_response(state: OrderState) -> dict[str, Any]:
    """Parse LLM JSON response into state fields."""
    raw = state.get("llm_response_raw", "{}")
    # Strip markdown code fences if present
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        return {
            "status": data.get("status", "confirmed"),
            "issues": data.get("issues", []),
            "customer_message": data.get("customer_message", ""),
            "internal_note": data.get("internal_note", ""),
        }
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse order agent JSON: %s | raw=%s", exc, raw)
        return {
            "status": "confirmed",
            "customer_message": (
                f"Thank you {state['customer_name']}! "
                "Your order has been received and our team will confirm it shortly."
            ),
            "internal_note": f"New order from {state['customer_name']} — {state['product']}.",
        }


def make_excel_export_node(excel_path: Path):
    def export_excel(state: OrderState) -> dict[str, Any]:
        """Append order to Excel file."""
        try:
            import pandas as pd

            order_row = {
                "Customer Name": state.get("customer_name", ""),
                "Product": state.get("product", ""),
                "Size": state.get("size", ""),
                "Delivery Date": state.get("delivery_date", ""),
                "Delivery Address": state.get("delivery_address", ""),
                "Notes": state.get("notes", ""),
                "Payment Method": state.get("payment_method", ""),
                "Order Date": str(date.today()),
                "Status": state.get("status", "confirmed"),
            }

            if excel_path.exists():
                df = pd.read_excel(excel_path)
                df = pd.concat([df, pd.DataFrame([order_row])], ignore_index=True)
            else:
                df = pd.DataFrame([order_row])

            df.to_excel(excel_path, index=False)
            logger.info("Order saved to Excel: %s", excel_path)
            return {"excel_saved": True}

        except Exception as exc:
            logger.error("Excel export failed: %s", exc)
            return {"excel_saved": False}

    return export_excel


# ──────────────────────────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────────────────────────


def build_order_agent(
    openai_api_key: str,
    excel_path: Path,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
):
    llm = ChatOpenAI(api_key=openai_api_key, model=model, temperature=temperature)

    builder = StateGraph(OrderState)
    builder.add_node("validate_input", validate_input)
    builder.add_node("call_llm", make_llm_node(llm))
    builder.add_node("parse_response", parse_response)
    builder.add_node("export_excel", make_excel_export_node(excel_path))

    builder.set_entry_point("validate_input")
    builder.add_edge("validate_input", "call_llm")
    builder.add_edge("call_llm", "parse_response")
    builder.add_edge("parse_response", "export_excel")
    builder.add_edge("export_excel", END)

    graph = builder.compile()
    logger.info("Order agent graph compiled")
    return graph


def process_order(graph, order_data: dict) -> dict:
    """
    Run the order agent and return the result dict.

    Args:
        graph: compiled order agent graph
        order_data: dict with order fields

    Returns:
        Final state dict with status, customer_message, internal_note, excel_saved
    """
    initial_state: OrderState = {
        "customer_name": order_data.get("customer_name", ""),
        "product": order_data.get("product", ""),
        "size": order_data.get("size", ""),
        "delivery_date": order_data.get("delivery_date", ""),
        "delivery_address": order_data.get("delivery_address", ""),
        "notes": order_data.get("notes", ""),
        "payment_method": order_data.get("payment_method", ""),
        "llm_response_raw": "",
        "status": "",
        "issues": [],
        "customer_message": "",
        "internal_note": "",
        "excel_saved": False,
    }
    result = graph.invoke(initial_state)
    return result
