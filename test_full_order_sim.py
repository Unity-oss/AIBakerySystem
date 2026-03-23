#!/usr/bin/env python
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tastyz_project.settings')
django.setup()

from bakery.models import Product, Order, Invoice, Payment
from bakery.invoice_generator import generate_invoice_for_order
from bakery.payment_gateway import MobileMoneyGateway

print("=" * 70)
print("FULL ORDER SIMULATION WITH PAYMENT")
print("=" * 70)

# Get first product
product = Product.objects.first()
if not product:
    print("ERROR: No products!")
    exit(1)

print(f"\n1. Creating order...")
order = Order.objects.create(
    customer_name="Full Sim Test User",
    customer_phone="0701234567",
    customer_email="test@test.com",
    product=product,
    size="small",
    quantity=1,
    delivery_date=(timezone.now() + timedelta(days=2)).date(),
    payment_method="mobile_money"
)
print(f"   Order created: #{order.pk}")

print(f"\n2. Generating invoice...")
invoice = generate_invoice_for_order(order)
print(f"   Invoice created: {invoice.invoice_number}, Total: {invoice.total_amount} UGX")

print(f"\n3. Initiating payment via Flutterwave...")
gateway = MobileMoneyGateway()
result = gateway.initiate_payment(
    invoice,
    phone_number=order.customer_phone,
    success_url=f"/order/success/{order.pk}/",
    cancel_url="/order/",
)

print(f"\n4. Payment Result:")
print(f"   success      = {result.success}")
print(f"   transaction_id = {result.transaction_id}")
print(f"   message       = {result.message}")
print(f"   data type    = {type(result.data)}")
print(f"   data is empty = {not result.data}")

if result.data:
    print(f"\n5. Redirect URL Extraction:")
    redirect_url = result.data.get("meta", {}).get("authorization", {}).get("redirect")
    print(f"   extracted redirect = {bool(redirect_url)}")
    if redirect_url:
        print(f"   redirect URL = {redirect_url[:100]}...")

print(f"\n6. View Logic Simulation:")
print(f"   if payment_result.success and payment_result.data and order.payment_method in ['mobile_money']:")
print(f"   ->  {result.success} and {bool(result.data)} and {order.payment_method == 'mobile_money'}")
print(f"   ->  WOULD REDIRECT: {result.success and bool(result.data) and order.payment_method == 'mobile_money'}")

# Check what was stored in database
print(f"\n7. Database Payment Record:")
payment = Payment.objects.filter(invoice=invoice).first()
if payment:
    print(f"   Payment ID: {payment.id}")
    print(f"   Gateway: {payment.gateway}")
    print(f"   Status: {payment.status}")
    print(f"   gateway_response has redirect: {bool(payment.gateway_response.get('meta', {}).get('authorization', {}).get('redirect'))}")

print("\n" + "=" * 70)
