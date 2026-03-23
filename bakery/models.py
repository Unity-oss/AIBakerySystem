"""
Django models for Tastyz Bakery.
"""

import uuid

from django.db import models
from django.utils import timezone


class Category(models.TextChoices):
    CAKE = "cake", "Cake"
    COOKIES = "cookies", "Cookies"
    PASTRIES = "pastries", "Fresh Pastries"


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.CAKE)
    price_small = models.IntegerField(help_text="Price in UGX (1KG / Small / per piece)")
    price_large = models.IntegerField(
        null=True, blank=True, help_text="Price in UGX (2KG / Large)"
    )
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

    @property
    def price_display(self):
        if self.price_large:
            return f"{self.price_small:,} / {self.price_large:,} UGX"
        return f"{self.price_small:,} UGX"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name_snapshot = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=50, blank=True, help_text="1KG/2KG or Small/Big")
    quantity = models.PositiveIntegerField(default=1)
    delivery_date = models.DateField()
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Cake message or special instructions")
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.MOBILE_MONEY
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    ai_confirmation_message = models.TextField(blank=True)
    ai_internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.customer_name} ({self.product_name_snapshot})"

    def save(self, *args, **kwargs):
        # Snapshot the product name so it's preserved if product is deleted
        if self.product and not self.product_name_snapshot:
            self.product_name_snapshot = self.product.name
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        """Calculate total price based on size and quantity."""
        if self.product:
            base = self.product.price_large if self.size in ("2KG", "Big", "Big Tin") else self.product.price_small
            return (base or 0) * self.quantity
        return 0


# ──────────────────────────────────────────────────────────────
# LLM Settings (session-based, stored in DB for persistence)
# ──────────────────────────────────────────────────────────────


class LLMSettings(models.Model):
    """User-configurable LLM settings."""

    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        GOOGLE = "google", "Google Gemini"
        ANTHROPIC = "anthropic", "Anthropic Claude"
        GROK = "grok", "Grok (xAI)"
        OLLAMA = "ollama", "Ollama (Local)"

    session_key = models.CharField(max_length=64, unique=True, help_text="Django session key")
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.OPENAI)
    model_name = models.CharField(max_length=100, default="gpt-4o-mini")
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    frequency_penalty = models.FloatField(default=0.0)
    presence_penalty = models.FloatField(default=0.0)
    max_tokens = models.IntegerField(default=1024)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LLM Settings"
        verbose_name_plural = "LLM Settings"

    def __str__(self):
        return f"LLM Settings ({self.provider}/{self.model_name})"

    # Available models per provider
    PROVIDER_MODELS = {
        "openai": [
            ("gpt-4o-mini", "GPT-4o Mini (Fast, Cheap)"),
            ("gpt-4o", "GPT-4o (Powerful)"),
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo (Fastest)"),
        ],
        "google": [
            ("gemini-pro", "Gemini Pro"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash"),
            ("gemini-1.5-pro", "Gemini 1.5 Pro"),
        ],
        "anthropic": [
            ("claude-3-haiku-20240307", "Claude 3 Haiku (Fast)"),
            ("claude-3-sonnet-20240229", "Claude 3 Sonnet"),
            ("claude-3-opus-20240229", "Claude 3 Opus (Powerful)"),
        ],
        "grok": [
            ("grok-2", "Grok 2"),
            ("grok-2-mini", "Grok 2 Mini (Fast)"),
        ],
        "ollama": [
            ("mistral", "Mistral 7B"),
            ("llama3", "Llama 3"),
            ("codellama", "Code Llama"),
            ("phi3", "Phi-3"),
            ("gemma2", "Gemma 2"),
        ],
    }


# ──────────────────────────────────────────────────────────────
# Token Usage Log (persistent, for the settings dashboard)
# ──────────────────────────────────────────────────────────────


class TokenUsageLog(models.Model):
    """Persistent log of every LLM call for the token usage dashboard."""

    timestamp = models.DateTimeField(default=timezone.now)
    session_key = models.CharField(max_length=64, blank=True)
    agent = models.CharField(max_length=50)
    provider = models.CharField(max_length=20, default="openai")
    model = models.CharField(max_length=100)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)
    latency_ms = models.IntegerField(default=0, help_text="Response time in milliseconds")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.agent} | {self.model} | {self.input_tokens}+{self.output_tokens} tokens"


# ──────────────────────────────────────────────────────────────
# Response Cache
# ──────────────────────────────────────────────────────────────


class ResponseCache(models.Model):
    """Cache for frequently asked questions to reduce LLM calls."""

    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    query_text = models.TextField()
    response_text = models.TextField()
    agent = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    hit_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-hit_count"]

    def __str__(self):
        return f"Cache: {self.query_text[:60]}… ({self.hit_count} hits)"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


# ──────────────────────────────────────────────────────────────
# Feedback (agent learning)
# ──────────────────────────────────────────────────────────────


class Feedback(models.Model):
    """User feedback on AI responses — used for agent learning."""

    class Rating(models.IntegerChoices):
        TERRIBLE = 1, "Terrible"
        BAD = 2, "Bad"
        OK = 3, "OK"
        GOOD = 4, "Good"
        EXCELLENT = 5, "Excellent"

    session_key = models.CharField(max_length=64, blank=True)
    query = models.TextField()
    response = models.TextField()
    agent = models.CharField(max_length=50)
    rating = models.IntegerField(choices=Rating.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback #{self.pk}: {self.rating}★ — {self.query[:50]}"


# ──────────────────────────────────────────────────────────────
# Fine-tune Jobs
# ──────────────────────────────────────────────────────────────


class FineTuneJob(models.Model):
    """Track fine-tuning jobs submitted to OpenAI."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    openai_job_id = models.CharField(max_length=100, blank=True)
    base_model = models.CharField(max_length=100, default="gpt-4o-mini-2024-07-18")
    fine_tuned_model = models.CharField(max_length=200, blank=True)
    training_file_id = models.CharField(max_length=100, blank=True)
    num_examples = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"FineTune #{self.pk} ({self.status}) — {self.base_model}"


# ──────────────────────────────────────────────────────────────
# Invoice
# ──────────────────────────────────────────────────────────────


class Invoice(models.Model):
    """Auto-generated invoice for an order."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    amount = models.IntegerField(help_text="Amount in UGX")
    tax_amount = models.IntegerField(default=0, help_text="VAT in UGX (5%)")
    total_amount = models.IntegerField(help_text="Total incl tax in UGX")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.order.customer_name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.tax_amount:
            self.tax_amount = int(self.amount * 0.05)
        if not self.total_amount:
            self.total_amount = self.amount + self.tax_amount
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────────────────


class Payment(models.Model):
    """Payment record linked to an invoice."""

    class Gateway(models.TextChoices):
        MOBILE_MONEY = "mobile_money", "Mobile Money (MTN/Airtel)"
        STRIPE = "stripe", "Stripe (Card)"
        FLUTTERWAVE = "flutterwave", "Flutterwave"
        MANUAL = "manual", "Manual / Cash"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    transaction_id = models.CharField(max_length=200, blank=True)
    amount = models.IntegerField(help_text="Amount in UGX")
    phone_number = models.CharField(max_length=20, blank=True, help_text="For Mobile Money")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.transaction_id or self.pk} — {self.get_gateway_display()}"


# ──────────────────────────────────────────────────────────────
# Observability Log
# ──────────────────────────────────────────────────────────────


class ObservabilityLog(models.Model):
    """LLM observability trace for debugging and monitoring."""

    trace_id = models.CharField(max_length=64, default="", db_index=True)
    session_key = models.CharField(max_length=64, blank=True)
    agent = models.CharField(max_length=50)
    step = models.CharField(max_length=50, help_text="e.g., route_intent, retrieve, generate")
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    model = models.CharField(max_length=100, blank=True)
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    error = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Trace {self.trace_id[:8]} | {self.agent}.{self.step}"
