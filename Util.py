import logging
from logging import getLogger, StreamHandler


def setup_logger():
    logger = getLogger(__name__)
    if not logger.hasHandlers():  # Check if handlers already exist
        handler = StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


