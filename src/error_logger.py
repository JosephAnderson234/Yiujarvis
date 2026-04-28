import logging
from pathlib import Path


ERROR_LOG_FILE = Path("erros.log")
_CONFIGURED = False


def ensure_error_logging():
    global _CONFIGURED

    if _CONFIGURED:
        return logging.getLogger("yiujarvis")

    logger = logging.getLogger("yiujarvis")
    logger.setLevel(logging.INFO)
    logger.propagate = True

    root_logger = logging.getLogger()
    already_configured = any(
        isinstance(handler, logging.FileHandler)
        and Path(getattr(handler, "baseFilename", "")).name == ERROR_LOG_FILE.name
        for handler in root_logger.handlers
    )

    if not already_configured:
        file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root_logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger


def log_exception(message):
    logger = ensure_error_logging()
    logger.exception(message)


def log_error(message):
    logger = ensure_error_logging()
    logger.error(message)