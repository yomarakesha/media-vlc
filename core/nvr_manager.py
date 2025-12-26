"""
MediaMTX VMS Client v2.0 - NVR Manager
Manages NVR/DVR devices with thread-safe CRUD operations.
"""

import threading
from typing import List, Optional, Dict
from models.nvr import NVR
from utils.config import config
from utils.logger import logger


class NVRManager:
    """
    Manages NVR/DVR devices with thread-safe CRUD operations.
    Integrates with ConfigManager for persistence.
    """
    
    def __init__(self):
        """Initialize NVR manager."""
        self._nvrs: Dict[str, NVR] = {}
        self._lock = threading.Lock()
        self._load_from_config()
    
    def _load_from_config(self) -> None:
        """Load NVRs from configuration."""
        nvrs_data = config.get_nvrs()
        logger.info(f"Loading {len(nvrs_data)} NVRs from config")
        
        for nvr_data in nvrs_data:
            try:
                nvr = NVR.from_dict(nvr_data)
                self._nvrs[nvr.id] = nvr
            except Exception as e:
                logger.error(f"Failed to load NVR: {e}")
    
    def add_nvr(self, nvr: NVR) -> bool:
        """
        Add a new NVR.
        
        Args:
            nvr: NVR object to add
            
        Returns:
            True if successful, False otherwise
        """
        # Validate NVR
        is_valid, error_msg = nvr.validate()
        if not is_valid:
            logger.error(f"Invalid NVR: {error_msg}")
            return False
        
        with self._lock:
            # Check for duplicates
            if nvr.id in self._nvrs:
                logger.warning(f"NVR with ID {nvr.id} already exists")
                return False
            
            # Check for duplicate host
            for existing_nvr in self._nvrs.values():
                if existing_nvr.host == nvr.host and existing_nvr.port == nvr.port:
                    logger.warning(f"NVR at {nvr.host}:{nvr.port} already exists")
                    return False
            
            # Add to memory
            self._nvrs[nvr.id] = nvr
            
            # Save to config
            config.add_nvr(nvr.to_dict())
            
            logger.info(f"Added NVR: {nvr.name} ({nvr.id})")
            return True
    
    def update_nvr(self, nvr: NVR) -> bool:
        """
        Update existing NVR.
        
        Args:
            nvr: Updated NVR object
            
        Returns:
            True if successful, False otherwise
        """
        is_valid, error_msg = nvr.validate()
        if not is_valid:
            logger.error(f"Invalid NVR: {error_msg}")
            return False
        
        with self._lock:
            if nvr.id not in self._nvrs:
                logger.error(f"NVR {nvr.id} not found")
                return False
            
            # Update in memory
            self._nvrs[nvr.id] = nvr
            
            # Update in config (remove and re-add)
            config.remove_nvr(nvr.id)
            config.add_nvr(nvr.to_dict())
            
            logger.info(f"Updated NVR: {nvr.name} ({nvr.id})")
            return True
    
    def remove_nvr(self, nvr_id: str, remove_cameras: bool = False) -> bool:
        """
        Remove NVR by ID.
        
        Args:
            nvr_id: NVR ID to remove
            remove_cameras: Whether to also remove associated cameras
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if nvr_id not in self._nvrs:
                logger.warning(f"NVR {nvr_id} not found")
                return False
            
            nvr = self._nvrs[nvr_id]
            
            # Handle associated cameras
            if remove_cameras and nvr.cameras:
                from core.camera_manager import camera_manager
                for camera_id in nvr.cameras:
                    camera_manager.remove_camera(camera_id)
                logger.info(f"Removed {len(nvr.cameras)} cameras from NVR {nvr.name}")
            
            del self._nvrs[nvr_id]
            
            # Remove from config
            config.remove_nvr(nvr_id)
            
            logger.info(f"Removed NVR: {nvr.name} ({nvr_id})")
            return True
    
    def get_nvr(self, nvr_id: str) -> Optional[NVR]:
        """
        Get NVR by ID.
        
        Args:
            nvr_id: NVR ID
            
        Returns:
            NVR object or None if not found
        """
        with self._lock:
            return self._nvrs.get(nvr_id)
    
    def get_all_nvrs(self) -> List[NVR]:
        """
        Get all NVRs.
        
        Returns:
            List of all NVRs
        """
        with self._lock:
            return list(self._nvrs.values())
    
    def count(self) -> int:
        """Get total number of NVRs."""
        with self._lock:
            return len(self._nvrs)
    
    def clear(self) -> None:
        """Remove all NVRs (use with caution)."""
        with self._lock:
            self._nvrs.clear()
            config.set("nvrs", [])
            logger.warning("All NVRs cleared")


# Global NVR manager instance
nvr_manager = NVRManager()
