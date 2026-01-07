"""
MediaMTX VMS Client v2.0 - Camera Model
Dataclass representing a camera/IP camera device.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid


@dataclass
class Camera:
    """
    Represents a camera device (IP camera, RTSP stream, etc.)
    """
    
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Camera"
    
    # Connection
    url: str = ""  # RTSP or HLS URL (Main/High quality stream)
    sub_stream_url: str = ""  # Optional sub-stream URL (Low quality/bandwidth)
    username: str = ""
    password: str = ""
    
    # Type and grouping
    type: str = "RTSP"  # RTSP or HLS
    group: str = "Default"
    
    # Stream quality preference
    stream_quality: str = "auto"  # auto, high, low
    
    # Features
    motion_detection: bool = False
    recording_enabled: bool = False
    
    # Optional metadata
    description: str = ""
    location: str = ""
    manufacturer: str = ""
    model: str = ""
    
    # Parent NVR (if camera belongs to NVR)
    nvr_id: Optional[str] = None
    channel: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert camera to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Camera':
        """Create camera from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def get_display_name(self) -> str:
        """Get display name with location if available."""
        if self.location:
            return f"{self.name} ({self.location})"
        return self.name
    
    def get_stream_url(self, quality: str = "auto", widget_size: Optional[tuple] = None) -> str:
        """
        Get appropriate stream URL based on quality preference.
        
        Args:
            quality: Stream quality preference ("auto", "high", "low")
            widget_size: Optional (width, height) tuple for auto-detection
            
        Returns:
            Stream URL (main or sub-stream)
        """
        # Explicit quality preference
        if quality == "high":
            return self.url
        elif quality == "low" and self.sub_stream_url:
            return self.sub_stream_url
        
        # Auto-detect based on widget size
        if quality == "auto" and widget_size and self.sub_stream_url:
            width, height = widget_size
            # Use sub-stream for small widgets (< 300px)
            if width < 300 or height < 300:
                return self.sub_stream_url
        
        # Default to main stream
        return self.url
    
    def has_sub_stream(self) -> bool:
        """
        Check if camera has a configured sub-stream.
        
        Returns:
            True if sub-stream URL is configured
        """
        return bool(self.sub_stream_url)
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate camera configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.name:
            return False, "Camera name is required"
        
        if not self.url:
            return False, "Camera URL is required"
        
        if self.type not in ["RTSP", "HLS"]:
            return False, "Camera type must be RTSP or HLS"
        
        # Basic URL validation
        if self.type == "RTSP" and not self.url.startswith("rtsp://"):
            return False, "RTSP URL must start with rtsp://"
        
        if self.type == "HLS" and not self.url.startswith("http"):
            return False, "HLS URL must start with http:// or https://"
        
        # Validate sub-stream URL if provided
        if self.sub_stream_url:
            if self.type == "RTSP" and not self.sub_stream_url.startswith("rtsp://"):
                return False, "Sub-stream RTSP URL must start with rtsp://"
            if self.type == "HLS" and not self.sub_stream_url.startswith("http"):
                return False, "Sub-stream HLS URL must start with http:// or https://"
        
        # Validate stream quality
        if self.stream_quality not in ["auto", "high", "low"]:
            return False, "Stream quality must be 'auto', 'high', or 'low'"
        
        return True, ""
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Camera(id={self.id[:8]}..., name={self.name}, type={self.type}, url={self.url})"
