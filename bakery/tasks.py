"""
Celery background tasks for Tastyz Bakery.

These tasks run on a schedule (via Celery beat) to automate
the bakery's backend operations.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="bakery.tasks.run_daily_sales_report", bind=True, max_retries=3)
def run_daily_sales_report(self):
    """
    Daily sales analysis task.
    Reads orders.xlsx, generates an AI report, and emails it to the baker.
    Scheduled: 8 PM daily (see settings.py CELERY_BEAT_SCHEDULE)
    """
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        from bakery.agent_registry import get_sales_agent
        from agents.sales_agent import run_sales_report

        logger.info("Starting daily sales report task")
        agent = get_sales_agent()
        report = run_sales_report(agent, str(settings.ORDERS_EXCEL_PATH))

        logger.info("Sales report generated, sending email to baker")

        # Email the report
        send_mail(
            subject="Tastyz Bakery — Daily Sales Report",
            message=report,
            from_email=settings.EMAIL_HOST_USER or "noreply@tastyzbakery.com",
            recipient_list=[settings.BAKER_EMAIL],
            fail_silently=True,
        )

        logger.info("Daily sales report sent successfully")
        return {"status": "success", "report_length": len(report)}

    except Exception as exc:
        logger.error("Daily sales report task failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)  # retry after 5 min


@shared_task(name="bakery.tasks.export_orders_excel")
def export_orders_excel():
    """
    Export all current orders to the Excel file.
    Can be called manually or triggered after bulk operations.
    """
    try:
        import pandas as pd
        from django.conf import settings

        from bakery.models import Order

        orders = Order.objects.select_related("product").values(
            "id",
            "customer_name",
            "customer_phone",
            "product_name_snapshot",
            "size",
            "quantity",
            "delivery_date",
            "delivery_address",
            "notes",
            "payment_method",
            "status",
            "created_at",
        )

        df = pd.DataFrame(list(orders))
        df.to_excel(settings.ORDERS_EXCEL_PATH, index=False)
        logger.info("Orders exported to Excel: %d rows", len(df))
        return {"status": "success", "rows": len(df)}

    except Exception as exc:
        logger.error("Excel export task failed: %s", exc)
        return {"status": "error", "message": str(exc)}
