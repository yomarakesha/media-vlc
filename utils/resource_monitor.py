"""
MediaMTX VMS Client v2.0 - Resource Monitor
System resource usage monitoring (CPU, RAM).
"""

import threading
import time
from typing import Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from utils.logger import logger

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not found. Resource monitoring disabled.")

class ResourceMonitor(QObject):
    """
    Worker to monitor system resources.
    Emits signals with CPU and RAM usage.
    """
    
    # Signals
    # cpu_percent, ram_percent, ram_used_gb, ram_total_gb
    usage_updated = pyqtSignal(float, float, float, float)
    
    def __init__(self, interval: float = 2.0):
        super().__init__()
        self._interval = interval
        self._running = False
        self._thread = None
        
    def start(self):
        """Start monitoring thread."""
        if not PSUTIL_AVAILABLE:
            return
            
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.debug("Resource monitoring started")
        
    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _monitor_loop(self):
        """Monitoring loop."""
        while self._running:
            try:
                # CPU
                cpu = psutil.cpu_percent(interval=None)
                
                # RAM
                ram = psutil.virtual_memory()
                ram_pct = ram.percent
                ram_used = ram.used / (1024**3) # GB
                ram_total = ram.total / (1024**3) # GB
                
                self.usage_updated.emit(cpu, ram_pct, ram_used, ram_total)
                
                # Sleep
                time.sleep(self._interval)
                
            except Exception as e:
                logger.error(f"Resource monitor error: {e}")
                time.sleep(self._interval * 2)

# Global instance
resource_monitor = ResourceMonitor()
