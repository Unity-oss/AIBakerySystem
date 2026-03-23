"""
Agent Learning from Feedback for Tastyz Bakery.

Collects user feedback (1-5 star ratings + comments) on AI responses,
analyses patterns, and generates a dynamic system prompt supplement
that steers the agent toward higher-quality responses.
"""

import logging

from django.db.models import Avg, Count, Q

from .models import Feedback

logger = logging.getLogger(__name__)


def record_feedback(
    query: str,
    response: str,
    agent: str,
    rating: int,
    comment: str = "",
    session_key: str = "",
) -> Feedback:
    """Record a single feedback entry."""
    fb = Feedback.objects.create(
        session_key=session_key,
        query=query,
        response=response,
        agent=agent,
        rating=rating,
        comment=comment,
    )
    logger.info("Feedback recorded: %d★ for agent=%s", rating, agent)
    return fb


def get_feedback_stats(agent: str = "") -> dict:
    """Aggregate feedback statistics, optionally filtered by agent."""
    qs = Feedback.objects.all()
    if agent:
        qs = qs.filter(agent=agent)

    stats = qs.aggregate(
        total=Count("id"),
        avg_rating=Avg("rating"),
        positive=Count("id", filter=Q(rating__gte=4)),
        negative=Count("id", filter=Q(rating__lte=2)),
    )
    return {
        "total_feedback": stats["total"] or 0,
        "avg_rating": round(stats["avg_rating"] or 0, 2),
        "positive_count": stats["positive"] or 0,
        "negative_count": stats["negative"] or 0,
        "neutral_count": (stats["total"] or 0) - (stats["positive"] or 0) - (stats["negative"] or 0),
    }


def generate_learning_prompt_supplement(agent: str = "", limit: int = 20) -> str:
    """
    Analyse recent feedback to generate a system prompt supplement.

    This teaches the agent from past mistakes:
    - Low-rated responses become 'avoid' patterns
    - High-rated responses become 'prefer' patterns
    """
    negative = (
        Feedback.objects.filter(rating__lte=2)
        .order_by("-created_at")[:limit]
    )
    positive = (
        Feedback.objects.filter(rating__gte=4)
        .order_by("-created_at")[:limit]
    )

    if agent:
        negative = negative.filter(agent=agent)
        positive = positive.filter(agent=agent)

    if not negative.exists() and not positive.exists():
        return ""

    lines = ["\n--- LEARNING FROM USER FEEDBACK ---"]

    if negative.exists():
        lines.append("\nUsers DISLIKED these types of responses (avoid similar patterns):")
        for fb in negative[:5]:
            lines.append(f'- Query: "{fb.query[:80]}" → Response was rated {fb.rating}★')
            if fb.comment:
                lines.append(f'  User said: "{fb.comment[:100]}"')

    if positive.exists():
        lines.append("\nUsers LIKED these types of responses (prefer similar patterns):")
        for fb in positive[:5]:
            lines.append(f'- Query: "{fb.query[:80]}" → Response was rated {fb.rating}★')
            if fb.comment:
                lines.append(f'  User said: "{fb.comment[:100]}"')

    lines.append("\n--- END FEEDBACK LEARNING ---")
    return "\n".join(lines)
