"""
MediaMTX VMS Client v2.0 - Logging Utilities
Provides centralized logging configuration with file and console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(name: str = "MediaMTX_VMS", log_dir: str = "logs") -> logging.Logger:
    """
    Set up and configure application logger.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with rotation (10MB max, 5 backups)
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("=" * 80)
    logger.info(f"MediaMTX VMS Client v2.0 - Logger initialized")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    
    return logger


# Global logger instance
logger = setup_logger()
