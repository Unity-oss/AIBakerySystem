"""
LLM Observability for Tastyz Bakery.

Provides tracing, logging, and monitoring of LLM calls.
- Stores traces in the ObservabilityLog model for dashboard viewing.
- Sends traces to LangSmith (if LANGSMITH_API_KEY is configured) for
  external monitoring and debugging.
"""

import logging
import os
import time
import uuid
from contextlib import contextmanager
from functools import wraps

from django.utils import timezone

logger = logging.getLogger(__name__)

_langsmith_configured = False


def configure_langsmith():
    """
    Set the LangSmith environment variables so that LangChain
    auto-traces all LLM calls to the LangSmith dashboard.
    Call this once at startup.
    """
    global _langsmith_configured
    if _langsmith_configured:
        return

    try:
        from django.conf import settings

        api_key = getattr(settings, "LANGSMITH_API_KEY", "")
        if api_key:
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
            os.environ.setdefault("LANGCHAIN_PROJECT", "tastyz-bakery")
            _langsmith_configured = True
            logger.info("LangSmith tracing enabled (project=tastyz-bakery)")
        else:
            logger.debug("LangSmith not configured — LANGSMITH_API_KEY is empty")
    except Exception as exc:
        logger.warning("Failed to configure LangSmith: %s", exc)


def _generate_trace_id() -> str:
    return uuid.uuid4().hex


def _send_to_langsmith(span_data: dict):
    """Send a completed span to LangSmith as a run."""
    try:
        from langsmith import Client

        api_key = os.environ.get("LANGCHAIN_API_KEY", "")
        if not api_key:
            return

        client = Client()
        client.create_run(
            name=f"{span_data['agent']}/{span_data['step']}",
            run_type="chain",
            inputs=span_data.get("input_data", {}),
            outputs=span_data.get("output_data", {}),
            error=span_data.get("error") or None,
            start_time=timezone.now() - timezone.timedelta(milliseconds=span_data["latency_ms"]),
            end_time=timezone.now(),
            extra={
                "trace_id": span_data["trace_id"],
                "model": span_data.get("model", ""),
                "tokens_used": span_data.get("tokens_used", 0),
                "session_key": span_data.get("session_key", ""),
            },
            project_name="tastyz-bakery",
        )
    except Exception as exc:
        logger.debug("LangSmith send failed (non-critical): %s", exc)


class Tracer:
    """
    Context-based tracer for LLM observability.

    Usage:
        tracer = Tracer(agent="rag_agent", session_key="abc123")
        with tracer.span("retrieve") as span:
            docs = retriever.invoke(query)
            span.set_output({"doc_count": len(docs)})
    """

    def __init__(self, agent: str, session_key: str = "", trace_id: str = ""):
        self.agent = agent
        self.session_key = session_key
        self.trace_id = trace_id or _generate_trace_id()
        self.spans = []
        # Ensure LangSmith is configured
        configure_langsmith()

    @contextmanager
    def span(self, step: str, model: str = "", input_data: dict | None = None):
        """Create a timed span for a single step."""
        span_data = {
            "trace_id": self.trace_id,
            "session_key": self.session_key,
            "agent": self.agent,
            "step": step,
            "model": model,
            "input_data": input_data or {},
            "output_data": {},
            "tokens_used": 0,
            "latency_ms": 0,
            "success": True,
            "error": "",
        }
        start = time.perf_counter()
        try:
            yield span_data
        except Exception as exc:
            span_data["success"] = False
            span_data["error"] = str(exc)
            raise
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            span_data["latency_ms"] = elapsed_ms
            self.spans.append(span_data)
            self._persist_span(span_data)
            # Also send to LangSmith
            _send_to_langsmith(span_data)

    def _persist_span(self, span_data: dict):
        """Save span to the database."""
        try:
            from .models import ObservabilityLog

            ObservabilityLog.objects.create(
                trace_id=span_data["trace_id"],
                session_key=span_data["session_key"],
                agent=span_data["agent"],
                step=span_data["step"],
                input_data=span_data["input_data"],
                output_data=span_data["output_data"],
                model=span_data["model"],
                tokens_used=span_data.get("tokens_used", 0),
                latency_ms=span_data["latency_ms"],
                success=span_data["success"],
                error=span_data["error"],
            )
        except Exception as exc:
            logger.warning("Failed to persist observability span: %s", exc)

    def summary(self) -> dict:
        """Return a summary of all spans in this trace."""
        total_latency = sum(s["latency_ms"] for s in self.spans)
        errors = [s for s in self.spans if not s["success"]]
        return {
            "trace_id": self.trace_id,
            "agent": self.agent,
            "total_spans": len(self.spans),
            "total_latency_ms": total_latency,
            "error_count": len(errors),
            "spans": [
                {
                    "step": s["step"],
                    "latency_ms": s["latency_ms"],
                    "success": s["success"],
                }
                for s in self.spans
            ],
        }


def get_recent_traces(limit: int = 50) -> list[dict]:
    """Get recent observability traces for the dashboard."""
    from .models import ObservabilityLog

    logs = ObservabilityLog.objects.order_by("-timestamp")[:limit]
    return [
        {
            "trace_id": log.trace_id,
            "agent": log.agent,
            "step": log.step,
            "model": log.model,
            "latency_ms": log.latency_ms,
            "success": log.success,
            "error": log.error,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]


def get_observability_stats() -> dict:
    """Aggregate observability stats for the dashboard."""
    from django.db.models import Avg, Count, Sum

    from .models import ObservabilityLog

    qs = ObservabilityLog.objects.all()
    stats = qs.aggregate(
        total_traces=Count("id"),
        avg_latency=Avg("latency_ms"),
        total_tokens=Sum("tokens_used"),
        error_count=Count("id", filter=models_Q(success=False)),
    )
    return {
        "total_traces": stats["total_traces"] or 0,
        "avg_latency_ms": round(stats["avg_latency"] or 0, 1),
        "total_tokens": stats["total_tokens"] or 0,
        "error_count": stats["error_count"] or 0,
        "success_rate": (
            round(
                (1 - (stats["error_count"] or 0) / max(stats["total_traces"] or 1, 1)) * 100, 1
            )
        ),
    }


def models_Q(**kwargs):
    """Helper to create Django Q objects."""
    from django.db.models import Q

    return Q(**kwargs)
