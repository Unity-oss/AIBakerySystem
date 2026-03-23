"""
Initial migration for Tastyz Bakery models.
Generated for Django 4.2
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[("cake", "Cake"), ("cookies", "Cookies"), ("pastries", "Fresh Pastries")],
                        default="cake",
                        max_length=20,
                    ),
                ),
                ("price_small", models.IntegerField(help_text="Price in UGX (1KG / Small / per piece)")),
                ("price_large", models.IntegerField(blank=True, help_text="Price in UGX (2KG / Large)", null=True)),
                ("is_available", models.BooleanField(default=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="products/")),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("customer_name", models.CharField(max_length=200)),
                ("customer_phone", models.CharField(max_length=20)),
                ("customer_email", models.EmailField(blank=True, max_length=254)),
                ("product_name_snapshot", models.CharField(blank=True, max_length=200)),
                ("size", models.CharField(blank=True, help_text="1KG/2KG or Small/Big", max_length=50)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("delivery_date", models.DateField()),
                ("delivery_address", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True, help_text="Cake message or special instructions")),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("mobile_money", "Mobile Money"),
                            ("bank_transfer", "Bank Transfer"),
                        ],
                        default="mobile_money",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("processing", "Processing"),
                            ("ready", "Ready"),
                            ("delivered", "Delivered"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("ai_confirmation_message", models.TextField(blank=True)),
                ("ai_internal_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="bakery.product",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
