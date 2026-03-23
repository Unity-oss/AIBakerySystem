#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tastyz_project.settings')
django.setup()

from bakery.models import Order, Payment

print('=== RECENT ORDERS ===')
for o in Order.objects.order_by('-created_at')[:5]:
    print(f'Order {o.id}: method="{o.payment_method}", Invoice: {o.invoice is not None}')
    payments = Payment.objects.filter(invoice__order=o)
    for p in payments:
        has_redirect = bool(p.gateway_response.get('meta', {}).get('authorization', {}).get('redirect'))
        print(f'  Payment {p.id}: tx_id={p.transaction_id}, has_redirect={has_redirect}')

print('\n=== DEBUG PAYMENT DICT ===')
p = Payment.objects.order_by('-created_at').first()
if p:
    print(f'payment_result.data structure:')
    print(f'  meta exists: {"meta" in p.gateway_response}')
    print(f'  meta.authorization exists: {" authorization" in p.gateway_response.get("meta", {})}')
    redirect = p.gateway_response.get('meta', {}).get('authorization', {}).get('redirect')
    print(f'  redirect extracted: {bool(redirect)}')
    print(f'  redirect value: {redirect[:80] if redirect else None}...')
