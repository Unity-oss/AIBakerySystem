"""
Utility tools for agents to call. Keep tools small, testable, and side-effect free where possible.

Tools implemented:
- get_products: return simple product list from DB
- find_product: lookup product by name
- search_price: lookup price info from knowledge base files
- notify_team: stub to notify team (logs to file)
"""

import logging
from typing import List, Optional, Dict
from pathlib import Path

from django.conf import settings

from bakery.models import Product

logger = logging.getLogger(__name__)


def get_products(category: Optional[str] = None) -> List[Dict]:
    """Return list of products (id, name, category, price_display).
    Category is optional and filters by product category.
    """
    qs = Product.objects.filter(is_available=True)
    if category:
        qs = qs.filter(category=category)
    return [
        {"id": p.id, "name": p.name, "category": p.category, "price": p.price_display}
        for p in qs
    ]


def find_product(name: str) -> Optional[Dict]:
    """Find a product by exact or partial name (case-insensitive)."""
    p = Product.objects.filter(name__icontains=name).first()
    if not p:
        return None
    return {"id": p.id, "name": p.name, "price": p.price_display, "available": p.is_available}


def search_price(query: str) -> Optional[str]:
    """Simple price lookup from knowledge_base/price_list.txt by keyword."""
    kb = Path(settings.BASE_DIR) / "KnowledgeBase" / "Price-list.docx"
    # Fallback: the project also includes knowledge_base/price_list.txt
    txt_kb = Path(settings.BASE_DIR) / "knowledge_base" / "price_list.txt"
    try:
        if txt_kb.exists():
            text = txt_kb.read_text(encoding="utf-8")
        elif kb.exists():
            # If docx, return a placeholder telling admin to rebuild KB
            return "Price list exists as a .docx file. Please run build_knowledge_base to index it."
        else:
            return None

        for line in text.splitlines():
            if query.lower() in line.lower():
                return line.strip()
    except Exception as exc:
        logger.exception("search_price failed: %s", exc)
    return None


def notify_team(subject: str, message: str) -> bool:
    """Stub tool that 'notifies' the team by writing to the agent log.

    In production this could send an email, Slack message, or webhook.
    """
    try:
        logger.info("NOTIFY TEAM | %s | %s", subject, message)
        return True
    except Exception as exc:
        logger.exception("notify_team failed: %s", exc)
        return False
