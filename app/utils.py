import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logger():
    """

    :return:
    """
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        settings.LOG_FILE,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=settings.LOG_LEVEL
    )
    return logger


log = setup_logger()
