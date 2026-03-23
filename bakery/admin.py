"""Admin configuration for Tastyz Bakery."""

from django.contrib import admin

from .models import (
    Feedback,
    FineTuneJob,
    Invoice,
    LLMSettings,
    ObservabilityLog,
    Order,
    Payment,
    Product,
    ResponseCache,
    TokenUsageLog,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price_display", "is_available"]
    list_filter = ["category", "is_available"]
    search_fields = ["name"]
    list_editable = ["is_available"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "customer_name",
        "product_name_snapshot",
        "size",
        "delivery_date",
        "status",
        "created_at",
    ]
    list_filter = ["status", "payment_method", "delivery_date"]
    search_fields = ["customer_name", "customer_phone", "product_name_snapshot"]
    readonly_fields = ["ai_confirmation_message", "ai_internal_note", "created_at", "updated_at"]
    list_editable = ["status"]
    ordering = ["-created_at"]


@admin.register(LLMSettings)
class LLMSettingsAdmin(admin.ModelAdmin):
    list_display = ["session_key", "provider", "model_name", "temperature", "updated_at"]


@admin.register(TokenUsageLog)
class TokenUsageLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "agent", "model", "input_tokens", "output_tokens", "cost_usd", "success"]
    list_filter = ["agent", "model", "success"]


@admin.register(ResponseCache)
class ResponseCacheAdmin(admin.ModelAdmin):
    list_display = ["query_text", "agent", "hit_count", "created_at", "expires_at"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["created_at", "agent", "rating", "query", "comment"]
    list_filter = ["rating", "agent"]


@admin.register(FineTuneJob)
class FineTuneJobAdmin(admin.ModelAdmin):
    list_display = ["openai_job_id", "base_model", "status", "num_examples", "created_at"]
    list_filter = ["status"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "order", "amount", "total_amount", "status", "created_at"]
    list_filter = ["status"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "invoice", "gateway", "amount", "status", "created_at"]
    list_filter = ["gateway", "status"]


@admin.register(ObservabilityLog)
class ObservabilityLogAdmin(admin.ModelAdmin):
    list_display = ["trace_id", "agent", "step", "latency_ms", "success", "timestamp"]
    list_filter = ["agent", "success"]
