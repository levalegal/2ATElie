"""Application logging."""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "atelier", level=logging.INFO) -> logging.Logger:
    """Configure and return application logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


log = setup_logger()
