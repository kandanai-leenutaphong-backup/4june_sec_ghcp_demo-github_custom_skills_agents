import json
import logging
import uuid
from typing import Any


LOGGER_NAME = "azure_openai"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def get_correlation_id(correlation_id: str | None = None) -> str:
    return correlation_id or str(uuid.uuid4())


def log_openai_request(logger: logging.Logger | None = None, **fields: Any) -> None:
    active_logger = logger or get_logger()
    active_logger.info(json.dumps(fields, default=str, sort_keys=True))
