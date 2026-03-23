"""
Django forms for Tastyz Bakery.
"""

from django import forms
from django.utils import timezone

from .models import Order, Product


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "customer_name",
            "customer_phone",
            "customer_email",
            "product",
            "size",
            "quantity",
            "delivery_date",
            "delivery_address",
            "notes",
            "payment_method",
        ]
        widgets = {
            "customer_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Your full name"}
            ),
            "customer_phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+256 7XX XXX XXX"}
            ),
            "customer_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "email@example.com (optional)"}
            ),
            "product": forms.Select(attrs={"class": "form-control"}),
            "size": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    ("", "— Select size —"),
                    ("1KG", "1KG (Cakes)"),
                    ("2KG", "2KG (Cakes)"),
                    ("Small", "Small"),
                    ("Big", "Big"),
                    ("Small Tin", "Small Tin (Cookies)"),
                    ("Medium Tin", "Medium Tin (Cookies)"),
                    ("Big Tin", "Big Tin (Cookies)"),
                ],
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "delivery_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "delivery_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "Delivery address"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Cake message or special instructions",
                }
            ),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get("delivery_date")
        today = timezone.now().date()
        if delivery_date and delivery_date < today:
            raise forms.ValidationError("Delivery date cannot be in the past.")
        return delivery_date


class ChatForm(forms.Form):
    question = forms.CharField(
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ask me anything about Tastyz Bakery…",
                "autocomplete": "off",
            }
        ),
        label="",
    )


class RecommendForm(forms.Form):
    customer_request = forms.CharField(
        max_length=300,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Suggest a cake for a birthday party under 100k",
            }
        ),
        label="What are you looking for?",
    )
