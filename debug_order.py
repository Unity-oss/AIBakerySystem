#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tastyz_project.settings')
django.setup()

from bakery.models import Order
from bakery.payment_gateway import initiate_payment_for_invoice

o = Order.objects.order_by('-created_at').first()
print("Last order:")
print("  payment_method:", repr(o.payment_method))
print("  Type:", type(o.payment_method))
print("  Equals 'mobile_money':", o.payment_method == 'mobile_money')
print("  In list:", o.payment_method in ['mobile_money'])

# Test payment initiation
if o.invoice:
    print("\nInitiating payment for order...")
    result = initiate_payment_for_invoice(
        o.invoice,
        method=o.payment_method,
        phone_number=o.customer_phone,
        success_url=f"/order/success/{o.pk}/",
        cancel_url="/order/",
    )
    print("  success:", result.success)
    print("  transaction_id:", result.transaction_id)
    print("  data type:", type(result.data))
    print("  has redirect:", bool(result.data.get('meta', {}).get('authorization', {}).get('redirect') if result.data else None))
