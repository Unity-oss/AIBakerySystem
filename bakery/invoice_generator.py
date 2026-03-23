"""
Automated Invoice Generator for Tastyz Bakery.

Generates invoices as PDF-style HTML and plain-text summaries.
Integrates with the Order model to auto-create invoices.
"""

import logging

from django.template.loader import render_to_string
from django.utils import timezone

from .models import Invoice, Order

logger = logging.getLogger(__name__)


def generate_invoice_for_order(order: Order) -> Invoice:
    """
    Create an Invoice for the given Order.
    If one already exists, return the existing one.
    """
    if hasattr(order, "invoice"):
        logger.info("Invoice already exists for Order #%s", order.pk)
        return order.invoice

    amount = order.total_price
    if amount <= 0:
        # Fallback: use product price_small * quantity
        if order.product:
            amount = order.product.price_small * order.quantity
        else:
            amount = 0

    invoice = Invoice(
        order=order,
        amount=amount,
    )
    invoice.save()
    logger.info("Invoice %s generated for Order #%s (amount=%d UGX)", invoice.invoice_number, order.pk, amount)
    return invoice


def generate_invoice_html(invoice: Invoice) -> str:
    """Render an invoice as an HTML string for display/download."""
    return render_to_string("bakery/invoice_detail.html", {"invoice": invoice})


def mark_invoice_paid(invoice: Invoice) -> Invoice:
    """Mark an invoice as paid."""
    invoice.status = Invoice.Status.PAID
    invoice.paid_at = timezone.now()
    invoice.save(update_fields=["status", "paid_at"])
    logger.info("Invoice %s marked as PAID", invoice.invoice_number)
    return invoice


def get_invoice_summary(invoice: Invoice) -> dict:
    """Return a JSON-serializable invoice summary."""
    return {
        "invoice_number": invoice.invoice_number,
        "customer": invoice.order.customer_name,
        "product": invoice.order.product_name_snapshot,
        "quantity": invoice.order.quantity,
        "size": invoice.order.size,
        "subtotal": invoice.amount,
        "tax": invoice.tax_amount,
        "total": invoice.total_amount,
        "status": invoice.get_status_display(),
        "created_at": invoice.created_at.isoformat() if invoice.created_at else "",
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }
