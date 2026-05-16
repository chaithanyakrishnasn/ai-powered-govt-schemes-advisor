import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    logger.remove()
    if settings.is_production or settings.LOG_JSON:
        logger.add(sys.stdout, format="{message}", serialize=True, level=settings.LOG_LEVEL)
    else:
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
        )


__all__ = ["logger", "setup_logging"]
