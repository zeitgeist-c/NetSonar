"""
NetSonar - Central logging configuration
Shared logging settings for all modules.
Logs go to both the console and a file.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from config import user_data_path

LOG_DIR = Path(user_data_path("netsonar_data", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "netsonar.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3


def setup_logging(name: str = "NetSonar") -> logging.Logger:
    """Merkezi loglama kurulumu. Tekrarlanmaz."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler (INFO and above)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (DEBUG and above, with rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Create a logger for a submodule."""
    return logging.getLogger(f"NetSonar.{name}")
