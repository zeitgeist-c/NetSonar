"""
AgTara — Merkezi Loglama Yapılandırması
Tüm modüller için ortak loglama ayarları.
Loglar hem konsola hem de dosyaya yazılır.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

LOG_DIR = Path("agtara_data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "agtara.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3


def setup_logging(name: str = "AgTara") -> logging.Logger:
    """Merkezi loglama kurulumu. Tekrarlanmaz."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler (INFO ve üstü)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (DEBUG ve üstü, rotation ile)
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
    """Alt modüller için logger oluştur."""
    return logging.getLogger(f"AgTara.{name}")
