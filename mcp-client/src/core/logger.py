import os
import sys

from loguru import logger

LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Remove default logger
logger.remove()

# Console logger (pretty + colored)
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>",
)

# File logger (rotating logs)
logger.add(
    f"{LOG_DIR}/app.log",
    rotation="10 MB",  # Rotate after 10MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip",  # Compress old logs
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line}-{message}",
)

# Optional: separate error log file
logger.add(
    f"{LOG_DIR}/error.log",
    level="ERROR",
    rotation="5 MB",
    retention="15 days",
    compression="zip",
)

__all__ = ["logger"]
