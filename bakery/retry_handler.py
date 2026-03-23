"""
Retry handler for LLM agent calls.

Provides exponential backoff retry logic with configurable
max retries, delays, and jitter. Integrates with observability logging.
"""

import logging
import random
import time
from functools import wraps

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable_exceptions: tuple = RETRYABLE_EXCEPTIONS,
):
    """
    Decorator that adds exponential-backoff retry logic to a function.

    Usage:
        @with_retry(max_retries=3)
        def call_llm(...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            "Retry exhausted for %s after %d attempts: %s",
                            func.__name__,
                            max_retries,
                            exc,
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.3)
                    total_delay = delay + jitter
                    logger.warning(
                        "Retry %d/%d for %s (delay=%.1fs): %s",
                        attempt,
                        max_retries,
                        func.__name__,
                        total_delay,
                        exc,
                    )
                    time.sleep(total_delay)
            raise last_exception

        return wrapper

    return decorator


def retry_llm_call(func, *args, max_retries=DEFAULT_MAX_RETRIES, **kwargs):
    """
    Functional retry wrapper for one-off LLM calls.

    Usage:
        result = retry_llm_call(my_llm_function, query, max_retries=3)
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if attempt == max_retries:
                logger.error(
                    "LLM call %s failed after %d retries: %s",
                    func.__name__,
                    max_retries,
                    exc,
                )
                raise
            delay = min(DEFAULT_BASE_DELAY * (2 ** (attempt - 1)), DEFAULT_MAX_DELAY)
            jitter = random.uniform(0, delay * 0.3)
            logger.warning(
                "LLM retry %d/%d for %s: %s",
                attempt,
                max_retries,
                func.__name__,
                exc,
            )
            time.sleep(delay + jitter)
    raise last_exception
