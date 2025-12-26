"""
MediaMTX VMS Client v2.0 - Camera Manager
Manages camera CRUD operations with thread-safe access.
"""

import threading
from typing import List, Optional, Dict
from models.camera import Camera
from utils.config import config
from utils.logger import logger


class CameraManager:
    """
    Manages camera devices with thread-safe CRUD operations.
    Integrates with ConfigManager for persistence.
    """
    
    def __init__(self):
        """Initialize camera manager."""
        self._cameras: Dict[str, Camera] = {}
        self._lock = threading.Lock()
        self._load_from_config()
    
    def _load_from_config(self) -> None:
        """Load cameras from configuration."""
        cameras_data = config.get_cameras()
        logger.info(f"Loading {len(cameras_data)} cameras from config")
        
        for cam_data in cameras_data:
            try:
                camera = Camera.from_dict(cam_data)
                self._cameras[camera.id] = camera
            except Exception as e:
                logger.error(f"Failed to load camera: {e}")
    
    def add_camera(self, camera: Camera) -> bool:
        """
        Add a new camera.
        
        Args:
            camera: Camera object to add
            
        Returns:
            True if successful, False otherwise
        """
        # Validate camera
        is_valid, error_msg = camera.validate()
        if not is_valid:
            logger.error(f"Invalid camera: {error_msg}")
            return False
        
        with self._lock:
            # Check for duplicates (by ID or URL)
            if camera.id in self._cameras:
                logger.warning(f"Camera with ID {camera.id} already exists")
                return False
            
            # Check for duplicate URLs
            for existing_camera in self._cameras.values():
                if existing_camera.url == camera.url:
                    logger.warning(f"Camera with URL {camera.url} already exists")
                    return False
            
            # Add to memory
            self._cameras[camera.id] = camera
            
            # Save to config
            config.add_camera(camera.to_dict())
            
            logger.info(f"Added camera: {camera.name} ({camera.id})")
            return True
    
    def update_camera(self, camera: Camera) -> bool:
        """
        Update existing camera.
        
        Args:
            camera: Updated camera object
            
        Returns:
            True if successful, False otherwise
        """
        is_valid, error_msg = camera.validate()
        if not is_valid:
            logger.error(f"Invalid camera: {error_msg}")
            return False
        
        with self._lock:
            if camera.id not in self._cameras:
                logger.error(f"Camera {camera.id} not found")
                return False
            
            # Update in memory
            self._cameras[camera.id] = camera
            
            # Update in config
            config.update_camera(camera.id, camera.to_dict())
            
            logger.info(f"Updated camera: {camera.name} ({camera.id})")
            return True
    
    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove camera by ID.
        
        Args:
            camera_id: Camera ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if camera_id not in self._cameras:
                logger.warning(f"Camera {camera_id} not found")
                return False
            
            camera = self._cameras[camera_id]
            del self._cameras[camera_id]
            
            # Remove from config
            config.remove_camera(camera_id)
            
            logger.info(f"Removed camera: {camera.name} ({camera_id})")
            return True
    
    def get_camera(self, camera_id: str) -> Optional[Camera]:
        """
        Get camera by ID.
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Camera object or None if not found
        """
        with self._lock:
            return self._cameras.get(camera_id)
    
    def get_all_cameras(self) -> List[Camera]:
        """
        Get all cameras.
        
        Returns:
            List of all cameras
        """
        with self._lock:
            return list(self._cameras.values())
    
    def get_cameras_by_group(self, group: str) -> List[Camera]:
        """
        Get cameras filtered by group.
        
        Args:
            group: Group name
            
        Returns:
            List of cameras in the specified group
        """
        with self._lock:
            return [cam for cam in self._cameras.values() if cam.group == group]
    
    def get_cameras_by_nvr(self, nvr_id: str) -> List[Camera]:
        """
        Get cameras belonging to a specific NVR.
        
        Args:
            nvr_id: NVR ID
            
        Returns:
            List of cameras from the NVR
        """
        with self._lock:
            return [cam for cam in self._cameras.values() if cam.nvr_id == nvr_id]
    
    def get_groups(self) -> List[str]:
        """
        Get all unique groups.
        
        Returns:
            List of group names
        """
        groups = config.get("groups", ["Default"])
        return groups
    
    def add_group(self, group_name: str) -> bool:
        """
        Add a new group.
        
        Args:
            group_name: Name of the group
            
        Returns:
            True if successful
        """
        groups = self.get_groups()
        if group_name not in groups:
            groups.append(group_name)
            config.set("groups", groups)
            logger.info(f"Added group: {group_name}")
            return True
        return False
    
    def count(self) -> int:
        """Get total number of cameras."""
        with self._lock:
            return len(self._cameras)
    
    def clear(self) -> None:
        """Remove all cameras (use with caution)."""
        with self._lock:
            self._cameras.clear()
            config.set("cameras", [])
            logger.warning("All cameras cleared")


# Global camera manager instance
camera_manager = CameraManager()
