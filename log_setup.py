"""
Reusable logging setup for Azure Functions Python apps.

Usage:
    # In function_app.py (must be the FIRST import):
    from log_setup import setup_logging
    logger = setup_logging("my_app")

    # In any other module:
    import logging
    logger = logging.getLogger(__name__)
    # That's it — the formatter and levels are already configured globally.

Configuration:
    Environment variables (all optional):
        LOG_LEVEL       – root log level for YOUR code (default: INFO)
        LOG_FORMAT      – override the format string (default: see below)
        LOG_DATE_FORMAT – override the date format (default: %H:%M:%S)

    The default format is:
        %(asctime)s [%(levelname).1s] %(name)s: %(message)s
        → 14:05:32 [I] uploads: Processing message abc-123

    To see debug output from your code only:
        LOG_LEVEL=DEBUG

    To silence a specific noisy library at runtime:
        import logging; logging.getLogger("urllib3").setLevel(logging.WARNING)

    Per-logger level overrides via environment variables:
        Prefix with LOGLEVEL_ , then the logger name (underscores → dots).
        The VALUE is the log level.  Everything is case-insensitive.

        Examples:
            LOGLEVEL_AZURE_CORE=WARNING         → sets "azure.core" to WARNING
            LOGLEVEL_URLLIB3=debug               → sets "urllib3" to DEBUG
            LOGLEVEL_MY_APP_UTILS=error          → sets "my_app.utils" to ERROR
            LOGLEVEL_AZURE_STORAGE_BLOB=Info     → sets "azure.storage.blob" to INFO

        Invalid values (not a valid Python log level) emit a warning and
        are skipped.
"""

import logging
import os
import warnings

# Libraries whose log chatter we suppress by default.
# Add entries here as you discover noisy dependencies.
_NOISY_LOGGERS: dict[str, int] = {
    # Azure SDK
    "azure": logging.WARNING,
    "azure.core": logging.WARNING,
    "azure.identity": logging.WARNING,
    "azure.storage": logging.WARNING,
    "azure.monitor": logging.WARNING,
    # HTTP / network
    "urllib3": logging.WARNING,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "requests": logging.WARNING,
    "aiohttp": logging.WARNING,
    # gRPC (used by Functions worker internals)
    "grpc": logging.WARNING,
    # OpenTelemetry
    "opentelemetry": logging.WARNING,
    # General
    "chardet": logging.WARNING,
    "charset_normalizer": logging.WARNING,
}

_DEFAULT_FORMAT = "%(asctime)s [%(levelname).1s] %(name)s: %(message)s"
_DEFAULT_DATE_FORMAT = "%H:%M:%S"

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

_LOGLEVEL_PREFIX = "LOGLEVEL_"


def _apply_env_log_overrides() -> None:
    """Scan env vars for per-logger level overrides.

    Convention (case-insensitive):
        LOGLEVEL_<LOGGER_NAME>=<LEVEL>
        Underscores after the prefix become dots in the logger name.

    Examples:
        LOGLEVEL_AZURE_CORE=WARNING  →  logging.getLogger("azure.core").setLevel(WARNING)
        LOGLEVEL_URLLIB3=debug        →  logging.getLogger("urllib3").setLevel(DEBUG)

    Invalid values emit a warning and are skipped.
    """
    for key, value in os.environ.items():
        if not key.upper().startswith(_LOGLEVEL_PREFIX):
            continue

        # Strip prefix, convert underscores → dots, lowercase
        raw_name = key[len(_LOGLEVEL_PREFIX):]
        if not raw_name:
            warnings.warn(
                f"Env var '{key}' has the LOGLEVEL_ prefix but no logger name.",
                stacklevel=2,
            )
            continue

        logger_name = raw_name.replace("_", ".").lower()
        level_name = value.strip().upper()

        if level_name not in _VALID_LEVELS:
            warnings.warn(
                f"Env var '{key}={value}': '{value}' is not a valid log level. "
                f"Valid levels: {', '.join(sorted(_VALID_LEVELS))}",
                stacklevel=2,
            )
            continue

        numeric_level = getattr(logging, level_name)
        logging.getLogger(logger_name).setLevel(numeric_level)
        logging.getLogger(__name__).debug(
            "ENV override: %s=%s → logger '%s' set to %s",
            key, value, logger_name, level_name,
        )


def setup_logging(
    app_name: str = "app",
    *,
    level: int | str | None = None,
    fmt: str | None = None,
    datefmt: str | None = None,
    noisy_loggers: dict[str, int] | None = None,
) -> logging.Logger:
    """Configure logging globally and return a ready-to-use logger for *app_name*.

    Call this **once**, as early as possible (top of function_app.py).

    Args:
        app_name:  Name for your application logger (appears in log lines).
        level:     Log level for your code. Reads LOG_LEVEL env var as fallback.
        fmt:       Format string. Reads LOG_FORMAT env var as fallback.
        datefmt:   Date format string. Reads LOG_DATE_FORMAT env var as fallback.
        noisy_loggers:  Extra library→level overrides merged on top of defaults.

    Returns:
        A ``logging.Logger`` instance named *app_name*, ready to use.
    """
    # --- resolve settings -------------------------------------------------
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    fmt = fmt or os.getenv("LOG_FORMAT", _DEFAULT_FORMAT)
    datefmt = datefmt or os.getenv("LOG_DATE_FORMAT", _DEFAULT_DATE_FORMAT)

    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # --- configure root logger --------------------------------------------
    root = logging.getLogger()
    root.setLevel(level)

    # Patch any handlers already installed (e.g. by the Azure Functions worker)
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    else:
        # No handlers yet — add a sensible default
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # --- quiet down noisy libraries ---------------------------------------
    merged = {**_NOISY_LOGGERS, **(noisy_loggers or {})}
    for name, lib_level in merged.items():
        logging.getLogger(name).setLevel(lib_level)

    # --- apply per-logger ENV overrides (highest priority) ----------------
    _apply_env_log_overrides()

    # --- return a logger for the caller -----------------------------------
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(level)
    return app_logger
