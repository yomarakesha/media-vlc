"""
MediaMTX VMS Client v2.0 - Utilities Package
"""

from .logger import logger, setup_logger
from .config import config, ConfigManager

__all__ = ['logger', 'setup_logger', 'config', 'ConfigManager']
