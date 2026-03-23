"""
Views for Tastyz Bakery AI System.
"""

import json
import logging
import time
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ChatForm, OrderForm, RecommendForm
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

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _get_session_settings(request) -> LLMSettings:
    """Get or create LLM settings for the current session."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    llm_settings, _ = LLMSettings.objects.get_or_create(
        session_key=session_key,
        defaults={"provider": "openai", "model_name": "gpt-4o-mini"},
    )
    return llm_settings


# ──────────────────────────────────────────────────────────────
# Home
# ──────────────────────────────────────────────────────────────


def home(request):
    featured_products = list(Product.objects.filter(is_available=True)[:6])
    
    # Gather images from home_images media folder
    media_home_images_path = Path(settings.MEDIA_ROOT) / "home_images"
    home_images = []
    
    if media_home_images_path.exists():
        image_files = sorted([f for f in media_home_images_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
        home_images = [f"/media/home_images/{f.name}" for f in image_files[:len(featured_products)]]
    
    # Pair products with home images
    featured_with_images = []
    for idx, product in enumerate(featured_products):
        home_image = home_images[idx] if idx < len(home_images) else None
        featured_with_images.append({
            'product': product,
            'home_image': home_image
        })
    
    return render(request, "bakery/home.html", {
        "featured_with_images": featured_with_images
    })


# ──────────────────────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────────────────────


def products(request):
    cakes = Product.objects.filter(category="cake", is_available=True)
    cookies = Product.objects.filter(category="cookies", is_available=True)
    pastries = Product.objects.filter(category="pastries", is_available=True)
    return render(
        request,
        "bakery/products.html",
        {"cakes": cakes, "cookies": cookies, "pastries": pastries},
    )


# ──────────────────────────────────────────────────────────────
# Order
# ──────────────────────────────────────────────────────────────


def place_order(request):
    if request.method == "POST":
        logger.info("━" * 60)
        logger.info("ORDER PLACEMENT STARTED")
        logger.info(f"POST data keys: {list(request.POST.keys())}")
        form = OrderForm(request.POST)
        logger.info(f"Form valid: {form.is_valid()}")
        if not form.is_valid():
            logger.error(f"Form errors: {form.errors}")
        if form.is_valid():
            order = form.save(commit=False)
            order.product_name_snapshot = (
                order.product.name if order.product else form.cleaned_data.get("product", "")
            )

            # Run AI order agent
            try:
                from .agent_registry import get_order_agent
                from agents.order_agent import process_order

                agent = get_order_agent()
                result = process_order(
                    agent,
                    {
                        "customer_name": order.customer_name,
                        "product": order.product_name_snapshot,
                        "size": order.size,
                        "delivery_date": str(order.delivery_date),
                        "delivery_address": order.delivery_address,
                        "notes": order.notes,
                        "payment_method": order.get_payment_method_display(),
                    },
                )
                order.status = result.get("status", "confirmed")
                order.ai_confirmation_message = result.get("customer_message", "")
                order.ai_internal_note = result.get("internal_note", "")
                logger.info(
                    "Order processed by AI agent | customer=%s status=%s",
                    order.customer_name,
                    order.status,
                )
            except Exception as exc:
                logger.error("Order agent failed: %s", exc)
                order.status = "pending"
                order.ai_confirmation_message = (
                    f"Thank you {order.customer_name}! Your order has been received. "
                    "Our team will contact you shortly to confirm."
                )

            order.save()

            # Auto-generate invoice
            try:
                from .invoice_generator import generate_invoice_for_order
                invoice = generate_invoice_for_order(order)

                # Initiate payment
                from .payment_gateway import initiate_payment_for_invoice
                logger.info(f">>> About to initiate payment | method={order.payment_method}, invoice_total={invoice.total_amount}")
                payment_result = initiate_payment_for_invoice(
                    invoice,
                    method=order.payment_method,
                    phone_number=order.customer_phone,
                    success_url=f"/order/success/{order.pk}/",
                    cancel_url="/order/",
                )
                
                logger.info(f">>> Payment result: success={payment_result.success}, tx_id={payment_result.transaction_id}")
                logger.info(f">>> Payment data type: {type(payment_result.data).__name__}")
                
                # Store transaction_id in session for polling on success page
                if payment_result.success:
                    request.session['payment_transaction_id'] = payment_result.transaction_id
                    logger.info(f">>> Stored transaction_id in session: {payment_result.transaction_id}")
                
                # Handle payment redirect for Mobile Money
                logger.info(f">>> Checking redirect conditions:")
                logger.info(f"    - payment_result.success = {payment_result.success}")
                logger.info(f"    - payment_result.data is not None = {payment_result.data is not None}")
                logger.info(f"    - order.payment_method = '{order.payment_method}'")
                logger.info(f"    - order.payment_method in ['mobile_money'] = {order.payment_method in ['mobile_money']}")
                
                if payment_result.success and payment_result.data and order.payment_method in ["mobile_money"]:
                    # Try multiple possible locations for redirect URL
                    redirect_url = (
                        payment_result.data.get("meta", {}).get("authorization", {}).get("redirect") or
                        payment_result.data.get("authorization", {}).get("redirect") or
                        payment_result.data.get("redirect")
                    )
                    logger.info(f">>> Redirect extraction: found={redirect_url is not None}")
                    if redirect_url:
                        logger.info(f">>> ✓ REDIRECTING TO FLUTTERWAVE: {redirect_url[:100]}...")
                        logger.info("━" * 60)
                        messages.info(request, "You will be redirected to complete your payment. Please approve the transaction.")
                        return redirect(redirect_url)
                    else:
                        logger.warning(f">>> No redirect URL found in response data")
                        logger.warning(f">>> Response data keys: {list(payment_result.data.keys())}")
                        if 'meta' in payment_result.data:
                            logger.warning(f">>> meta keys: {list(payment_result.data['meta'].keys())}") 
                
                logger.info(f">>> Not redirecting to Flutterwave, continuing to order success page...")
                if payment_result.message:
                    messages.info(request, payment_result.message)
            except Exception as exc:
                logger.error(f"Invoice/payment generation failed: {exc}", exc_info=True)

            # Schedule delivery on Google Calendar
            try:
                from .calendar_service import create_delivery_event
                cal_event = create_delivery_event(order)
                if cal_event:
                    logger.info("Calendar event created for order %d", order.pk)
            except Exception as exc:
                logger.error("Calendar event creation failed: %s", exc)

            messages.success(request, order.ai_confirmation_message)
            logger.info(f">>> Final: redirecting to order_success page for order {order.pk}")
            logger.info("━" * 60)
            return redirect("order_success", pk=order.pk)
    else:
        form = OrderForm()

    return render(request, "bakery/order.html", {"form": form})


def order_success(request, pk):
    order = Order.objects.get(pk=pk)
    context = {"order": order}
    # Get transaction_id from session if available (for polling widget)
    if 'payment_transaction_id' in request.session:
        transaction_id = request.session.pop('payment_transaction_id')
        context['transaction_id'] = transaction_id
        logger.info(f"Order {pk} success page loaded with transaction_id {transaction_id}")
    return render(request, "bakery/order_success.html", context)


def check_payment_status(request, transaction_id):
    """
    API endpoint to check payment status.
    Called by client-side JavaScript polling to detect webhook updates.
    """
    try:
        payment = Payment.objects.get(transaction_id=transaction_id)
        order_id = payment.invoice.order.pk if payment.invoice else None
        return JsonResponse({
            "status": payment.get_status_display(),
            "transaction_id": transaction_id,
            "order_id": order_id,
        })
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)
    except Exception as exc:
        logger.error(f"Error checking payment status: {exc}")
        return JsonResponse({"error": str(exc)}, status=500)
        return JsonResponse({"error": str(exc)}, status=500)


# ──────────────────────────────────────────────────────────────
# AI Chat (RAG)
# ──────────────────────────────────────────────────────────────


def chat(request):
    """Main chat page — renders the chat UI."""
    return render(request, "bakery/chat.html", {"form": ChatForm()})


@require_POST
def chat_api(request):
    """AJAX endpoint that returns AI response as JSON. Includes caching, retry, and observability."""
    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()
        history = data.get("history", [])

        if not question:
            return JsonResponse({"error": "No question provided"}, status=400)

        if len(question) > 500:
            return JsonResponse({"error": "Question too long (max 500 chars)"}, status=400)

        # Check cache first
        from .cache_manager import get_cached_response, set_cached_response

        cached = get_cached_response(question, agent="rag_agent")
        if cached:
            return JsonResponse({"answer": cached, "tokens_used": 0, "cost": 0.0, "cached": True})

        from .agent_registry import get_rag_agent
        from agents.rag_agent import ask_rag_agent
        from .token_tracker import track_usage
        from .retry_handler import retry_llm_call
        from .observability import Tracer

        session_key = request.session.session_key or ""
        tracer = Tracer(agent="rag_agent", session_key=session_key)

        agent = get_rag_agent()

        start_time = time.time()
        with tracer.span("rag_query", model="gpt-4o-mini", input_data={"question": question[:100]}):
            answer = retry_llm_call(ask_rag_agent, agent, question, history, max_retries=3)
        latency_ms = int((time.time() - start_time) * 1000)

        usage = track_usage("rag_agent", "gpt-4o-mini", question, answer)

        # Log to DB
        TokenUsageLog.objects.create(
            session_key=session_key,
            agent="rag_agent",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.cost_usd,
            latency_ms=latency_ms,
        )

        # Cache the response
        set_cached_response(question, answer, agent="rag_agent", model="gpt-4o-mini")

        logger.info("Chat answered | question_len=%d answer_len=%d tokens=%d", len(question), len(answer), usage.input_tokens + usage.output_tokens)

        return JsonResponse({
            "answer": answer,
            "tokens_used": usage.input_tokens + usage.output_tokens,
            "cost": usage.cost_usd,
            "cached": False,
        })

    except Exception as exc:
        logger.error("Chat API error: %s", exc)
        return JsonResponse(
            {
                "answer": (
                    "I'm sorry, I'm having trouble connecting right now. "
                    "Please call us on +256776318065 for immediate help."
                )
            }
        )


# ──────────────────────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────────────────────


def recommend(request):
    recommendation = None
    form = RecommendForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        customer_request = form.cleaned_data["customer_request"]
        try:
            from .agent_registry import get_recommendation_agent
            from agents.recommendation_agent import get_recommendation

            agent = get_recommendation_agent()
            recommendation = get_recommendation(agent, customer_request)
            logger.info("Recommendation generated for: %s", customer_request)
        except Exception as exc:
            logger.error("Recommendation agent failed: %s", exc)
            recommendation = (
                "Sorry, I couldn't generate recommendations right now. "
                "Please browse our Products page or call +256776318065."
            )

    return render(
        request,
        "bakery/recommend.html",
        {"form": form, "recommendation": recommendation},
    )


# ──────────────────────────────────────────────────────────────
# Agent Orchestrator Chat API
# ──────────────────────────────────────────────────────────────


@require_POST
def chat_orchestrator_api(request):
    """
    AJAX endpoint using LangGraph agent orchestrator.
    Intelligently routes to appropriate agent (RAG, recommendation, etc.)
    """
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        history = data.get("history", [])
        user_id = data.get("user_id") or getattr(request.user, 'id', 'anonymous')

        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)

        if len(user_message) > 1000:
            return JsonResponse({"error": "Message too long (max 1000 chars)"}, status=400)

        from .agent_registry import get_orchestrator
        from agents.agent_orchestrator import process_user_query
        from .token_tracker import track_usage

        result = process_user_query(
            graph=get_orchestrator(),
            user_id=str(user_id),
            user_message=user_message,
            conversation_history=history,
        )

        # Track token usage
        usage = track_usage(
            result.get("agent_type", "unknown"),
            "gpt-4o-mini",
            user_message,
            result.get("response", ""),
        )
        result["tokens_used"] = usage.input_tokens + usage.output_tokens
        result["cost"] = usage.cost_usd

        logger.info(
            "Orchestrator processed | user=%s agent=%s tokens=%d cost=$%.6f",
            user_id,
            result.get("agent_type"),
            result.get("tokens_used", 0),
            result.get("cost", 0.0),
        )

        return JsonResponse(
            {
                "response": result["response"],
                "agent_type": result.get("agent_type", "unknown"),
                "tokens_used": result.get("tokens_used", 0),
                "cost": result.get("cost", 0.0),
                "error": result.get("error"),
            }
        )

    except Exception as exc:
        logger.error("Orchestrator API error: %s", exc, exc_info=True)
        return JsonResponse(
            {
                "response": (
                    "I'm sorry, I encountered an error. "
                    "Please try again or contact us at +256776318065."
                ),
                "agent_type": "error",
                "error": str(exc),
            },
            status=500,
        )


# ──────────────────────────────────────────────────────────────
# Media Files
# ──────────────────────────────────────────────────────────────


def serve_media(request, path):
    """Serve media files (images, etc.) from the media directory."""
    try:
        file_path = Path(settings.MEDIA_ROOT) / path
        
        # Ensure the file is within MEDIA_ROOT (security check)
        if not str(file_path.resolve()).startswith(str(Path(settings.MEDIA_ROOT).resolve())):
            raise Http404("File not found")
        
        if not file_path.exists():
            logger.warning("Media file not found: %s", str(file_path))
            raise Http404("File not found")
        
        # Serve the file (FileResponse handles closing)
        return FileResponse(file_path.open('rb'), content_type='image/jpeg')
    except Exception as exc:
        logger.error("Media file error: %s - %s", path, exc)
        raise Http404("File not found")


# ──────────────────────────────────────────────────────────────
# Settings Page
# ──────────────────────────────────────────────────────────────


def settings_page(request):
    """Main settings dashboard with all tabs."""
    from .llm_provider import get_available_providers
    from .cache_manager import get_cache_stats
    from .observability import get_recent_traces, get_observability_stats
    from .feedback_learner import get_feedback_stats
    from .fine_tuner import get_fine_tune_stats
    from .token_tracker import _tracker
    from .calendar_service import is_calendar_configured

    llm_settings = _get_session_settings(request)
    providers = get_available_providers()

    # Check external integration statuses
    langsmith_configured = bool(getattr(settings, "LANGSMITH_API_KEY", ""))
    pinecone_configured = bool(getattr(settings, "PINECONE_API_KEY", ""))
    calendar_configured = is_calendar_configured()

    # Models for the currently selected provider
    current_models = LLMSettings.PROVIDER_MODELS.get(llm_settings.provider, [])

    # Token usage from in-memory tracker + DB
    token_summary = _tracker.get_summary()
    usage_logs = TokenUsageLog.objects.all()[:50]

    # Payment stats
    payment_stats = {
        "total": Payment.objects.count(),
        "completed": Payment.objects.filter(status="completed").count(),
        "pending": Payment.objects.filter(status="pending").count(),
    }

    return render(request, "bakery/settings.html", {
        "current_settings": llm_settings,
        "providers": providers,
        "models": current_models,
        "token_stats": token_summary,
        "usage_logs": usage_logs,
        "cache_stats": get_cache_stats(),
        "obs_stats": get_observability_stats(),
        "recent_traces": get_recent_traces(30),
        "finetune_stats": get_fine_tune_stats(),
        "finetune_jobs": FineTuneJob.objects.all()[:10],
        "feedback_stats": get_feedback_stats(),
        "recent_feedback": Feedback.objects.all()[:20],
        "invoices": Invoice.objects.select_related("order").all()[:20],
        "payments": Payment.objects.select_related("invoice").all()[:20],
        "payment_stats": payment_stats,
        "langsmith_configured": langsmith_configured,
        "pinecone_configured": pinecone_configured,
        "calendar_configured": calendar_configured,
    })


# ──────────────────────────────────────────────────────────────
# Settings API endpoints
# ──────────────────────────────────────────────────────────────


def settings_get_models(request):
    """Return available models for a provider."""
    provider = request.GET.get("provider", "openai")
    models = LLMSettings.PROVIDER_MODELS.get(provider, [])
    return JsonResponse({"models": models})


@require_POST
def settings_save(request):
    """Save LLM settings (provider, model, parameters)."""
    try:
        data = json.loads(request.body)
        llm_settings = _get_session_settings(request)

        if "provider" in data:
            llm_settings.provider = data["provider"]
        if "model_name" in data:
            llm_settings.model_name = data["model_name"]
        if "temperature" in data:
            llm_settings.temperature = max(0, min(2, float(data["temperature"])))
        if "top_p" in data:
            llm_settings.top_p = max(0, min(1, float(data["top_p"])))
        if "frequency_penalty" in data:
            llm_settings.frequency_penalty = max(0, min(2, float(data["frequency_penalty"])))
        if "presence_penalty" in data:
            llm_settings.presence_penalty = max(0, min(2, float(data["presence_penalty"])))
        if "max_tokens" in data:
            llm_settings.max_tokens = max(64, min(4096, int(data["max_tokens"])))

        llm_settings.save()
        logger.info("LLM settings saved: provider=%s model=%s", llm_settings.provider, llm_settings.model_name)
        return JsonResponse({"status": "ok"})
    except Exception as exc:
        logger.error("Settings save error: %s", exc)
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
def settings_clear_expired_cache(request):
    """Clear expired cache entries."""
    from .cache_manager import clear_expired_cache
    deleted = clear_expired_cache()
    return JsonResponse({"deleted": deleted})


@require_POST
def settings_clear_all_cache(request):
    """Clear all cache entries."""
    from .cache_manager import clear_all_cache
    deleted = clear_all_cache()
    return JsonResponse({"deleted": deleted})


@require_POST
def settings_start_finetune(request):
    """Start a fine-tuning job."""
    try:
        from .fine_tuner import submit_fine_tune_job
        job = submit_fine_tune_job()
        return JsonResponse({"status": "ok", "job_id": job.openai_job_id})
    except Exception as exc:
        logger.error("Fine-tune start error: %s", exc)
        return JsonResponse({"error": str(exc)}, status=400)


@require_POST
def settings_export_training(request):
    """Export training data as JSONL."""
    try:
        from .fine_tuner import collect_training_data, export_training_jsonl
        data = collect_training_data()
        path = export_training_jsonl(data)
        return JsonResponse({"status": "ok", "count": len(data), "path": path})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)


# ──────────────────────────────────────────────────────────────
# Feedback API
# ──────────────────────────────────────────────────────────────


@require_POST
def submit_feedback(request):
    """Submit feedback on an AI response."""
    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        response_text = data.get("response", "").strip()
        agent = data.get("agent", "unknown")
        rating = int(data.get("rating", 3))
        comment = data.get("comment", "").strip()

        if not query or not response_text:
            return JsonResponse({"error": "Query and response required"}, status=400)
        if rating < 1 or rating > 5:
            return JsonResponse({"error": "Rating must be 1-5"}, status=400)

        from .feedback_learner import record_feedback
        session_key = request.session.session_key or ""
        fb = record_feedback(query, response_text, agent, rating, comment, session_key)

        return JsonResponse({"status": "ok", "feedback_id": fb.pk})
    except Exception as exc:
        logger.error("Feedback error: %s", exc)
        return JsonResponse({"error": str(exc)}, status=400)


# ──────────────────────────────────────────────────────────────
# Invoice View
# ──────────────────────────────────────────────────────────────


def invoice_detail(request, pk):
    """View a single invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, "bakery/invoice_detail.html", {"invoice": invoice})


# ──────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────


@require_POST
def flutterwave_webhook(request):
    """Handle Flutterwave payment webhook callbacks."""
    try:
        payload = json.loads(request.body)
        transaction_id = payload.get("data", {}).get("tx_ref", "")
        status = payload.get("data", {}).get("status", "")
        
        if not transaction_id:
            logger.warning("Flutterwave webhook: No tx_ref in payload")
            return JsonResponse({"status": "error", "message": "No tx_ref"}, status=400)
        
        # Find and update payment
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            
            if status == "successful":
                payment.status = Payment.Status.COMPLETED
                payment.gateway_response = payload
                payment.save()
                logger.info("Flutterwave webhook: Payment %s marked as completed", transaction_id)
            elif status == "failed":
                payment.status = Payment.Status.FAILED
                payment.gateway_response = payload
                payment.save()
                logger.warning("Flutterwave webhook: Payment %s marked as failed", transaction_id)
            
            return JsonResponse({"status": "success", "message": "Webhook processed"})
        except Payment.DoesNotExist:
            logger.warning("Flutterwave webhook: No payment found for tx_ref %s", transaction_id)
            return JsonResponse({"status": "error", "message": "Payment not found"}, status=404)
    
    except json.JSONDecodeError:
        logger.error("Flutterwave webhook: Invalid JSON payload")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as exc:
        logger.error("Flutterwave webhook error: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)
