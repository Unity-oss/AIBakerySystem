"""
LLM Response Cache Manager for Tastyz Bakery.

Uses SHA-256 hashing of queries to cache and retrieve LLM responses.
Cache entries have a configurable TTL. Stale entries are cleaned periodically.
"""

import hashlib
import logging
from datetime import timedelta

from django.utils import timezone

from .models import ResponseCache

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_HOURS = 24


def _hash_query(query: str) -> str:
    """Generate a SHA-256 hash of the query text (lowered + stripped)."""
    normalised = query.strip().lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def get_cached_response(query: str, agent: str = "") -> str | None:
    """
    Look up a cached response for the given query.

    Returns the cached response text if found and not expired, else None.
    """
    query_hash = _hash_query(query)
    try:
        entry = ResponseCache.objects.filter(query_hash=query_hash).first()
        if entry and not entry.is_expired:
            entry.hit_count += 1
            entry.save(update_fields=["hit_count"])
            logger.info("Cache HIT for query hash %s (hits=%d)", query_hash[:12], entry.hit_count)
            return entry.response_text
        elif entry and entry.is_expired:
            entry.delete()
            logger.debug("Cache EXPIRED for query hash %s", query_hash[:12])
    except Exception as exc:
        logger.warning("Cache lookup error: %s", exc)
    return None


def set_cached_response(
    query: str,
    response: str,
    agent: str = "",
    model: str = "",
    ttl_hours: int = DEFAULT_CACHE_TTL_HOURS,
) -> None:
    """Store a response in the cache with the given TTL."""
    query_hash = _hash_query(query)
    expires_at = timezone.now() + timedelta(hours=ttl_hours)
    try:
        ResponseCache.objects.update_or_create(
            query_hash=query_hash,
            defaults={
                "query_text": query,
                "response_text": response,
                "agent": agent,
                "model": model,
                "expires_at": expires_at,
                "hit_count": 0,
            },
        )
        logger.info("Cache SET for query hash %s (ttl=%dh)", query_hash[:12], ttl_hours)
    except Exception as exc:
        logger.warning("Cache write error: %s", exc)


def clear_expired_cache() -> int:
    """Delete all expired cache entries. Returns count deleted."""
    count, _ = ResponseCache.objects.filter(expires_at__lt=timezone.now()).delete()
    if count:
        logger.info("Cleared %d expired cache entries", count)
    return count


def clear_all_cache() -> int:
    """Delete all cache entries. Returns count deleted."""
    count, _ = ResponseCache.objects.all().delete()
    logger.info("Cleared all %d cache entries", count)
    return count


def get_cache_stats() -> dict:
    """Return cache statistics for the dashboard."""
    total = ResponseCache.objects.count()
    expired = ResponseCache.objects.filter(expires_at__lt=timezone.now()).count()
    active = total - expired
    total_hits = sum(
        ResponseCache.objects.filter(expires_at__gte=timezone.now()).values_list("hit_count", flat=True)
    )
    return {
        "total_entries": total,
        "active_entries": active,
        "expired_entries": expired,
        "total_hits": total_hits,
    }
