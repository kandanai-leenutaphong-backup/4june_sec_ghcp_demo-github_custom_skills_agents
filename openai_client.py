import os
import time
from typing import Any, Callable

from openai_logging import get_correlation_id, get_logger, log_openai_request


RETRYABLE_STATUS_CODES = {429}


def _extract_status_code(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    if status_code is not None:
        return int(status_code)

    response = getattr(error, "response", None)
    if response is not None:
        response_status_code = getattr(response, "status_code", None)
        if response_status_code is not None:
            return int(response_status_code)

    return None


def _is_retryable(status_code: int | None) -> bool:
    if status_code is None:
        return False
    return status_code in RETRYABLE_STATUS_CODES or 500 <= status_code < 600


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer value for {name}: {value!r}") from error


def _read_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Invalid float value for {name}: {value!r}") from error


def call_azure_openai_with_retry(
    request_fn: Callable[[], Any],
    *,
    correlation_id: str | None = None,
    max_retries: int | None = None,
    base_backoff_seconds: float | None = None,
    max_backoff_seconds: float | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    time_fn: Callable[[], float] = time.perf_counter,
) -> Any:
    """
    Run an Azure OpenAI request with retry/backoff and structured logs.
    """
    request_id = get_correlation_id(correlation_id)
    logger = get_logger()
    retries = max_retries if max_retries is not None else _read_int_env("AZURE_OPENAI_MAX_RETRIES", 3)
    base_backoff = (
        base_backoff_seconds
        if base_backoff_seconds is not None
        else _read_float_env("AZURE_OPENAI_RETRY_BASE_SECONDS", 1.0)
    )
    max_backoff = (
        max_backoff_seconds
        if max_backoff_seconds is not None
        else _read_float_env("AZURE_OPENAI_RETRY_MAX_SECONDS", 8.0)
    )

    total_attempts = retries + 1
    for attempt in range(1, total_attempts + 1):
        start = time_fn()
        try:
            response = request_fn()
            latency_ms = round((time_fn() - start) * 1000, 2)
            status_code = getattr(response, "status_code", 200)
            log_openai_request(
                logger,
                event="azure_openai_request",
                correlation_id=request_id,
                success=True,
                attempt=attempt,
                max_attempts=total_attempts,
                status_code=status_code,
                latency_ms=latency_ms,
            )
            return response
        except Exception as error:
            latency_ms = round((time_fn() - start) * 1000, 2)
            status_code = _extract_status_code(error)
            retryable = _is_retryable(status_code)
            log_openai_request(
                logger,
                event="azure_openai_request",
                correlation_id=request_id,
                success=False,
                attempt=attempt,
                max_attempts=total_attempts,
                status_code=status_code,
                retryable=retryable,
                latency_ms=latency_ms,
                error=str(error),
            )
            if not retryable or attempt == total_attempts:
                raise

            backoff_seconds = min(base_backoff * (2 ** (attempt - 1)), max_backoff)
            sleep_fn(backoff_seconds)
