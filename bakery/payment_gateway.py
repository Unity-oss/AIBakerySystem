"""
Payment Gateway Integration for Tastyz Bakery.

Supports:
- Mobile Money (MTN/Airtel Uganda) via Flutterwave
- Card payments via Stripe
- Manual/Cash payments

Uses a strategy pattern: each gateway implements initiate_payment() and verify_payment().
"""

import logging
import uuid

from django.conf import settings
from django.utils import timezone

from .models import Invoice, Payment

logger = logging.getLogger(__name__)


class PaymentResult:
    """Standardised result from any payment gateway."""

    def __init__(self, success: bool, transaction_id: str = "", message: str = "", data: dict = None):
        self.success = success
        self.transaction_id = transaction_id
        self.message = message
        self.data = data or {}


# ──────────────────────────────────────────────────────────────
# Mobile Money Gateway (Flutterwave)
# ──────────────────────────────────────────────────────────────


class MobileMoneyGateway:
    """Mobile Money payments via Flutterwave API."""

    def initiate_payment(self, invoice: Invoice, phone_number: str, success_url: str = None, cancel_url: str = None) -> PaymentResult:
        """Initiate a Mobile Money payment via Flutterwave."""
        flw_secret = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        flw_encryption_key = getattr(settings, "FLUTTERWAVE_ENCRYPTION_KEY", "")
        if not flw_secret:
            logger.warning("Flutterwave not configured — creating manual payment record")
            return self._create_manual_record(invoice, phone_number)

        try:
            import requests

            # Format phone number with Uganda country code (256)
            formatted_phone = phone_number.strip()
            if formatted_phone.startswith("0"):
                formatted_phone = "256" + formatted_phone[1:]
            elif not formatted_phone.startswith("256"):
                formatted_phone = "256" + formatted_phone

            tx_ref = f"TASTYZ-{uuid.uuid4().hex[:10].upper()}"
            payload = {
                "tx_ref": tx_ref,
                "amount": invoice.total_amount,
                "currency": "UGX",
                "payment_type": "mobilemoneyuganda",
                "phone_number": formatted_phone,
                "email": invoice.order.customer_email or "customer@tastyzbakery.com",
                "fullname": invoice.order.customer_name,
                "meta": {
                    "invoice_number": invoice.invoice_number,
                    "order_id": invoice.order.pk,
                },
            }
            
            # Add redirect URLs if provided
            if success_url:
                payload["redirect_url"] = success_url
            if cancel_url:
                payload["redirect_cancel_url"] = cancel_url
            
            headers = {"Authorization": f"Bearer {flw_secret}"}

            resp = requests.post(
                "https://api.flutterwave.com/v3/charges?type=mobile_money_uganda",
                json=payload,
                headers=headers,
                timeout=30,
            )
            data = resp.json()

            if data.get("status") == "success":
                payment = Payment.objects.create(
                    invoice=invoice,
                    gateway=Payment.Gateway.FLUTTERWAVE,
                    transaction_id=tx_ref,
                    amount=invoice.total_amount,
                    phone_number=phone_number,
                    status=Payment.Status.PROCESSING,
                    gateway_response=data,
                )
                logger.info("Mobile Money payment initiated: %s", tx_ref)
                return PaymentResult(
                    success=True,
                    transaction_id=tx_ref,
                    message="Payment initiated. Please approve on your phone.",
                    data=data,
                )
            else:
                logger.error("Flutterwave error: %s", data.get("message"))
                return PaymentResult(success=False, message=data.get("message", "Payment failed"))

        except Exception as exc:
            logger.error("Mobile Money payment error: %s", exc)
            return PaymentResult(success=False, message=str(exc))

    def verify_payment(self, transaction_id: str) -> PaymentResult:
        """Verify a Flutterwave transaction status."""
        flw_secret = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        if not flw_secret:
            return PaymentResult(success=False, message="Flutterwave not configured")
        try:
            import requests

            resp = requests.get(
                f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
                headers={"Authorization": f"Bearer {flw_secret}"},
                timeout=30,
            )
            data = resp.json()
            if data.get("status") == "success" and data.get("data", {}).get("status") == "successful":
                # Update payment record
                Payment.objects.filter(transaction_id=transaction_id).update(
                    status=Payment.Status.COMPLETED,
                    gateway_response=data,
                )
                return PaymentResult(success=True, transaction_id=transaction_id, message="Payment verified", data=data)
            return PaymentResult(success=False, transaction_id=transaction_id, message=data.get("message", "Verification failed"))
        except Exception as exc:
            logger.error("Flutterwave verify error: %s", exc)
            return PaymentResult(success=False, message=str(exc))

    def _create_manual_record(self, invoice: Invoice, phone_number: str) -> PaymentResult:
        """Create a pending payment record when gateway is not configured."""
        tx_ref = f"TASTYZ-MM-{uuid.uuid4().hex[:8].upper()}"
        Payment.objects.create(
            invoice=invoice,
            gateway=Payment.Gateway.MOBILE_MONEY,
            transaction_id=tx_ref,
            amount=invoice.total_amount,
            phone_number=phone_number,
            status=Payment.Status.PENDING,
        )
        return PaymentResult(
            success=True,
            transaction_id=tx_ref,
            message="Payment recorded. Our team will confirm your Mobile Money payment shortly.",
        )


# ──────────────────────────────────────────────────────────────
# Stripe Gateway
# ──────────────────────────────────────────────────────────────


class StripeGateway:
    """Card payments via Stripe."""

    def create_checkout_session(self, invoice: Invoice, success_url: str, cancel_url: str) -> PaymentResult:
        """Create a Stripe Checkout session."""
        stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        if not stripe_key:
            logger.warning("Stripe not configured — creating manual payment record")
            return self._create_manual_record(invoice)

        try:
            import stripe

            stripe.api_key = stripe_key
            # Convert UGX to the smallest currency unit
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "ugx",
                            "product_data": {
                                "name": f"Invoice {invoice.invoice_number}",
                                "description": f"Order: {invoice.order.product_name_snapshot}",
                            },
                            "unit_amount": invoice.total_amount,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "invoice_number": invoice.invoice_number,
                    "order_id": str(invoice.order.pk),
                },
            )

            Payment.objects.create(
                invoice=invoice,
                gateway=Payment.Gateway.STRIPE,
                transaction_id=session.id,
                amount=invoice.total_amount,
                status=Payment.Status.PROCESSING,
                gateway_response={"session_id": session.id, "url": session.url},
            )
            logger.info("Stripe checkout session created: %s", session.id)
            return PaymentResult(
                success=True,
                transaction_id=session.id,
                message="Redirecting to payment page...",
                data={"checkout_url": session.url},
            )

        except Exception as exc:
            logger.error("Stripe error: %s", exc)
            return PaymentResult(success=False, message=str(exc))

    def _create_manual_record(self, invoice: Invoice) -> PaymentResult:
        """Fallback when Stripe is not configured."""
        tx_ref = f"TASTYZ-CARD-{uuid.uuid4().hex[:8].upper()}"
        Payment.objects.create(
            invoice=invoice,
            gateway=Payment.Gateway.STRIPE,
            transaction_id=tx_ref,
            amount=invoice.total_amount,
            status=Payment.Status.PENDING,
        )
        return PaymentResult(
            success=True,
            transaction_id=tx_ref,
            message="Card payment recorded. Our team will process it shortly.",
        )


# ──────────────────────────────────────────────────────────────
# Manual / Cash Gateway
# ──────────────────────────────────────────────────────────────


class ManualGateway:
    """Record manual or cash payments."""

    def record_payment(self, invoice: Invoice) -> PaymentResult:
        tx_ref = f"TASTYZ-CASH-{uuid.uuid4().hex[:8].upper()}"
        Payment.objects.create(
            invoice=invoice,
            gateway=Payment.Gateway.MANUAL,
            transaction_id=tx_ref,
            amount=invoice.total_amount,
            status=Payment.Status.PENDING,
        )
        return PaymentResult(
            success=True,
            transaction_id=tx_ref,
            message="Cash/manual payment recorded. Pay on delivery.",
        )


# ──────────────────────────────────────────────────────────────
# Gateway Factory
# ──────────────────────────────────────────────────────────────


def get_gateway(method: str):
    """Return the appropriate payment gateway instance."""
    gateways = {
        "mobile_money": MobileMoneyGateway(),
        "stripe": StripeGateway(),
        "manual": ManualGateway(),
        "cash": ManualGateway(),
        "bank_transfer": ManualGateway(),
    }
    return gateways.get(method, ManualGateway())


def initiate_payment_for_invoice(invoice: Invoice, method: str, **kwargs) -> PaymentResult:
    """
    High-level function to initiate a payment for an invoice.
    Dispatches to the correct gateway.
    """
    gateway = get_gateway(method)

    if method == "mobile_money":
        phone = kwargs.get("phone_number", invoice.order.customer_phone)
        success_url = kwargs.get("success_url", "/")
        cancel_url = kwargs.get("cancel_url", "/")
        return gateway.initiate_payment(invoice, phone, success_url=success_url, cancel_url=cancel_url)
    elif method == "stripe":
        return gateway.create_checkout_session(
            invoice,
            success_url=kwargs.get("success_url", "/"),
            cancel_url=kwargs.get("cancel_url", "/"),
        )
    else:
        return gateway.record_payment(invoice)
