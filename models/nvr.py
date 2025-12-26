"""
MediaMTX VMS Client v2.0 - NVR Model
Dataclass representing a Network Video Recorder (NVR/DVR).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import uuid


@dataclass
class NVR:
    """
    Represents a Network Video Recorder (NVR/DVR) device.
    """
    
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "NVR"
    
    # Connection
    host: str = ""  # IP address or hostname
    port: int = 80  # ONVIF port (usually 80)
    username: str = ""
    password: str = ""
    
    # Protocol
    onvif_enabled: bool = True
    rtsp_port: int = 554
    
    # Cameras (camera IDs)
    cameras: List[str] = field(default_factory=list)
    
    # Optional metadata
    description: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    
    # Proxy configuration (e.g., MediaMTX)
    use_proxy: bool = False
    proxy_url: str = ""
    
    # Zero Channel / Preview Stream
    zero_stream_enabled: bool = False
    zero_stream_url: str = ""
    
    def to_dict(self) -> dict:
        """Convert NVR to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NVR':
        """Create NVR from dictionary."""
        # Ensure cameras is a list
        if 'cameras' in data and not isinstance(data['cameras'], list):
            data['cameras'] = []
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def add_camera(self, camera_id: str) -> None:
        """Add camera to NVR."""
        if camera_id not in self.cameras:
            self.cameras.append(camera_id)
    
    def remove_camera(self, camera_id: str) -> None:
        """Remove camera from NVR."""
        if camera_id in self.cameras:
            self.cameras.remove(camera_id)
    
    def get_onvif_url(self) -> str:
        """Get ONVIF device management URL."""
        return f"http://{self.host}:{self.port}/onvif/device_service"
    
    def get_rtsp_base_url(self) -> str:
        """Get base RTSP URL for cameras."""
        return f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}"
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate NVR configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.name:
            return False, "NVR name is required"
        
        if not self.host:
            return False, "NVR host/IP is required"
        
        if not 1 <= self.port <= 65535:
            return False, "NVR port must be between 1 and 65535"
        
        if not 1 <= self.rtsp_port <= 65535:
            return False, "RTSP port must be between 1 and 65535"
        
        return True, ""
    
    def __repr__(self) -> str:
        """String representation."""
        return f"NVR(id={self.id[:8]}..., name={self.name}, host={self.host}, cameras={len(self.cameras)})"
