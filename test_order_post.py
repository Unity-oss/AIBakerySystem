#!/usr/bin/env python
import os
import django
from django.test import Client
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tastyz_project.settings')
django.setup()

from bakery.models import Product

# Get the first product
product = Product.objects.first()
if not product:
    print("ERROR: No products found!")
    exit(1)

# Prepare form data
delivery_date = (timezone.now() + timedelta(days=2)).date()
form_data = {
    'customer_name': 'Test Mobile Money User',
    'customer_phone': '0701234567',
    'customer_email': 'test@test.com',
    'product': product.id,
    'size': 'small',
    'quantity': 1,
    'delivery_date': delivery_date.isoformat(),
    'payment_method': 'mobile_money',
}

# Create a test client and POST
client = Client()
print(f"\nPOSTING order form with payment_method='{form_data['payment_method']}'")
print(f"Delivery date: {delivery_date}")
response = client.post('/order/', form_data, follow=False)

print(f"\nResponse status: {response.status_code}")
print(f"Response URL: {response.url if hasattr(response, 'url') else 'N/A'}")
print(f"Response headers Location: {response.get('Location', 'N/A')}")

if response.status_code in [301, 302, 303, 307, 308]:
    print(f"\n>>> Redirect detected!")
    print(f">>> Redirecting to: {response['Location']}")
elif response.status_code == 200:
    print(f"\n>>> No redirect (200 OK)")
    print(f">>> Content length: {len(response.content)}")
