"""Cấu hình log tối thiểu cho Server và Client."""

import logging


def create_logger(name: str) -> logging.Logger:
    """Tạo logger in thông tin ra terminal."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,  
            format="%(asctime)s %(levelname)s %(message)s", 
        )
    return logger