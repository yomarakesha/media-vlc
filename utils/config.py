"""
MediaMTX VMS Client v2.0 - Configuration Manager
Thread-safe configuration management with JSON persistence.
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional
from utils.logger import logger


class ConfigManager:
    """
    Manages application configuration with thread-safe access.
    Handles loading, saving, and default configuration generation.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Load or create configuration
        self.load()
    
    def load(self) -> None:
        """Load configuration from file or create default if not exists."""
        with self._lock:
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                    logger.info(f"Configuration loaded from {self.config_path}")
                    
                    # Migrate old versions if needed
                    self._migrate()
                except Exception as e:
                    logger.error(f"Failed to load config: {e}")
                    logger.info("Creating default configuration")
                    self._create_default()
            else:
                logger.info(f"Config file not found, creating default at {self.config_path}")
                self._create_default()
    
    def save(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                logger.debug("Configuration saved")
                return True
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'settings.fps_limit')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            save: Whether to save immediately
        """
        with self._lock:
            keys = key.split('.')
            config = self.config
            
            # Navigate to the parent
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            logger.debug(f"Config set: {key} = {value}")
        
        if save:
            self.save()
    
    def add_camera(self, camera: Dict[str, Any]) -> None:
        """Add camera to configuration (encrypts password)."""
        from utils.crypto import encrypt_password
        
        # Encrypt password before saving
        if camera.get("password"):
            camera["password"] = encrypt_password(camera["password"])
        
        with self._lock:
            if "cameras" not in self.config:
                self.config["cameras"] = []
            self.config["cameras"].append(camera)
        self.save()
    
    def update_camera(self, camera_id: str, camera: Dict[str, Any]) -> bool:
        """Update existing camera."""
        with self._lock:
            cameras = self.config.get("cameras", [])
            for i, cam in enumerate(cameras):
                if cam.get("id") == camera_id:
                    cameras[i] = camera
                    self.save()
                    return True
        return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove camera from configuration."""
        with self._lock:
            cameras = self.config.get("cameras", [])
            for i, cam in enumerate(cameras):
                if cam.get("id") == camera_id:
                    cameras.pop(i)
                    self.save()
                    return True
        return False
    
    def get_cameras(self) -> List[Dict[str, Any]]:
        """Get all cameras (decrypts passwords)."""
        from utils.crypto import decrypt_password
        
        cameras = self.get("cameras", [])
        result = []
        for cam in cameras:
            cam_copy = cam.copy()
            if cam_copy.get("password"):
                cam_copy["password"] = decrypt_password(cam_copy["password"])
            result.append(cam_copy)
        return result
    
    def add_nvr(self, nvr: Dict[str, Any]) -> None:
        """Add NVR to configuration (encrypts password)."""
        from utils.crypto import encrypt_password
        
        # Encrypt password before saving
        if nvr.get("password"):
            nvr["password"] = encrypt_password(nvr["password"])
        
        with self._lock:
            if "nvrs" not in self.config:
                self.config["nvrs"] = []
            self.config["nvrs"].append(nvr)
        self.save()
    
    def remove_nvr(self, nvr_id: str) -> bool:
        """Remove NVR from configuration."""
        with self._lock:
            nvrs = self.config.get("nvrs", [])
            for i, nvr in enumerate(nvrs):
                if nvr.get("id") == nvr_id:
                    nvrs.pop(i)
                    self.save()
                    return True
        return False
    
    def get_nvrs(self) -> List[Dict[str, Any]]:
        """Get all NVRs (decrypts passwords)."""
        from utils.crypto import decrypt_password
        
        nvrs = self.get("nvrs", [])
        result = []
        for nvr in nvrs:
            nvr_copy = nvr.copy()
            if nvr_copy.get("password"):
                nvr_copy["password"] = decrypt_password(nvr_copy["password"])
            result.append(nvr_copy)
        return result
    
    def _create_default(self) -> None:
        """Create default configuration."""
        self.config = {
            "version": "2.0.0",
            "cameras": [],
            "nvrs": [],
            "groups": [
                "Default",
                "Indoor",
                "Outdoor",
                "Entrance"
            ],
            "settings": {
                "fps_limit": 15,
                "reconnect_interval": 5,
                "recording_path": "./recordings",
                "screenshot_path": "./screenshots",
                "motion_detection_sensitivity": 30,
                "theme": "dark",
                "default_layout": "2x2",
                "auto_start_streams": True,
                "show_overlay": True,
                "show_timestamp": True
            },
            "layout": {
                "current": "2x2",
                "grid_assignments": {}
            },
            "emap": {
                "background_image": "",
                "camera_positions": {}
            }
        }
        self.save()
    
    def _migrate(self) -> None:
        """Migrate configuration from older versions."""
        version = self.config.get("version", "1.0.0")
        
        if version < "2.0.0":
            logger.info(f"Migrating config from {version} to 2.0.0")
            
            # Add missing keys with defaults
            if "groups" not in self.config:
                self.config["groups"] = ["Default", "Indoor", "Outdoor", "Entrance"]
            
            if "layout" not in self.config:
                self.config["layout"] = {
                    "current": "2x2",
                    "grid_assignments": {}
                }
            
            if "emap" not in self.config:
                self.config["emap"] = {
                    "background_image": "",
                    "camera_positions": {}
                }
            
            self.config["version"] = "2.0.0"
            self.save()


# Global config instance
config = ConfigManager()
