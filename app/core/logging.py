import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs log records as structured JSON lines.
    Provides consistent timestamping, severity levels, contextual attributes, and exception tracebacks.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request context fields if attached to log record
        for key in ("request_id", "method", "path", "status_code", "execution_time_ms", "user_id"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Attach exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Attach any extra custom fields passed via extra={...}
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def setup_structured_logging(log_level: str = "INFO"):
    """
    Configures root logger with StructuredJSONFormatter for stdout output.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("sentriq.core")
