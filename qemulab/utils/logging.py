"""Configures a robust, asynchronous logging system for the application.

This module sets up logging with two primary handlers:
1. A `RichHandler` for beautifully formatted, colored console output.
2. A `RotatingFileHandler` that writes structured JSON logs to a file.

Logging is handled asynchronously using a `QueueListener` to prevent I/O
operations from blocking the main application thread.
"""

import atexit
import copy
import json
import logging
import logging.config
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from typing import Any

from rich.text import Text

# A dedicated logger for this module.
_logger = logging.getLogger(__name__)

# Type alias for the logging configuration dictionary.
LogConfig = dict[str, Any]


class RichConsoleFormatter(logging.Formatter):
    """A simple formatter that passes the pre-formatted message directly."""

    def format(self, record: logging.LogRecord) -> str:
        """Returns the message as is, expecting it to contain Rich markup."""
        return record.getMessage()


class JSONFormatter(logging.Formatter):
    """Formats log records into a clean, structured JSON string."""

    def format(self, record: logging.LogRecord) -> str:
        """Converts a log record into a JSON string."""
        # Get the basic message, handling potential arguments
        plain_message = record.getMessage()

        # Strip any Rich markup to ensure the message is clean for JSON
        try:
            clean_message = Text.from_markup(plain_message).plain
        except Exception:
            clean_message = plain_message

        log_object: LogConfig = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": clean_message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        optional_fields = [
            "process",
            "processName",
            "thread",
            "threadName",
            "taskName",
        ]

        # Iterate and add them to the log object only if they have a value.
        for field in optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                log_object[field] = value

        # Add extra context from the user if it exists
        if hasattr(record, "extra_data") and record.extra_data:
            log_object.update(record.extra_data)

        # Add formatted exception information if present
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object)


class ConsoleOnlyFilter(logging.Filter):
    """A custom filter to exclude logs marked as 'console_only'."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "console_only", False)


# Default configuration defines formatters and handlers for console and file.
DEFAULT_LOGGING_CONFIG: LogConfig = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"exclude_console_only": {"()": ConsoleOnlyFilter}},
    "formatters": {
        "rich_console": {"()": RichConsoleFormatter},
        "json_file": {"()": JSONFormatter, "datefmt": "%Y-%m-%dT%H:%M:%S%z"},
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "level": "INFO",
            "formatter": "rich_console",
            "rich_tracebacks": True,
            "show_path": False,
            "show_time": False,
            "show_level": False,
            "markup": True,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": "logs/qemulab.log.jsonl",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "filters": ["exclude_console_only"],
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console", "file"]},
}


def setup_logging(
    config_path: str | Path | None = None,
    default_level: str = "INFO",
) -> None:
    """Configures logging from a file or uses a robust default configuration."""
    config = copy.deepcopy(DEFAULT_LOGGING_CONFIG)

    if config_path:
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with config_file.open() as f:
                    config = json.load(f)
                _logger.info("Loaded logging configuration from '%s'.", config_file)
        except Exception as e:
            _logger.warning(
                "Failed to load config '%s': %s. Using default logging config.", config_path, e
            )

    # Dynamically set the console log level for verbosity control.
    if "console" in config.get("handlers", {}):
        config["handlers"]["console"]["level"] = default_level.upper()

    # Ensure the log file's parent directory exists.
    if "file" in config.get("handlers", {}):
        log_filename = config["handlers"]["file"].get("filename", "logs/qemulab.log.jsonl")
        try:
            Path(log_filename).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create log directory: {e}")

    # Configure logging using the prepared dictionary.
    logging.config.dictConfig(config)

    # Set up asynchronous logging to avoid blocking the main thread on I/O.
    log_queue: Queue[logging.LogRecord] = Queue(-1)
    root_logger = logging.getLogger()

    # The QueueListener will manage the original handlers.
    listener_handlers = list(root_logger.handlers)
    for handler in listener_handlers:
        root_logger.removeHandler(handler)

    root_logger.addHandler(QueueHandler(log_queue))

    listener = QueueListener(log_queue, *listener_handlers, respect_handler_level=True)
    listener.start()
    atexit.register(listener.stop)
