"""
MediaMTX VMS Client v2.0 - Stream Status Model
Enum representing video stream connection states.
"""

from enum import Enum, auto


class StreamStatus(Enum):
    """Video stream connection status."""
    
    DISCONNECTED = auto()  # Not connected
    CONNECTING = auto()    # Attempting to connect
    CONNECTED = auto()     # Successfully connected and streaming
    ERROR = auto()         # Connection error
    RECORDING = auto()     # Connected and recording
    RECONNECTING = auto()  # Reconnection attempt in progress
    
    def __str__(self) -> str:
        """String representation."""
        return self.name.capitalize()
    
    def is_active(self) -> bool:
        """Check if stream is actively connected."""
        return self in (StreamStatus.CONNECTED, StreamStatus.RECORDING)
    
    def is_trying(self) -> bool:
        """Check if stream is attempting connection."""
        return self in (StreamStatus.CONNECTING, StreamStatus.RECONNECTING)
    
    def get_color(self) -> str:
        """Get color for UI display."""
        colors = {
            StreamStatus.DISCONNECTED: "#6A6A6A",    # Gray
            StreamStatus.CONNECTING: "#CE9178",      # Orange
            StreamStatus.CONNECTED: "#4EC9B0",       # Green
            StreamStatus.ERROR: "#F48771",           # Red
            StreamStatus.RECORDING: "#F48771",       # Red (recording indicator)
            StreamStatus.RECONNECTING: "#CE9178",    # Orange
        }
        return colors.get(self, "#6A6A6A")
    
    def get_display_text(self) -> str:
        """Get display text for UI."""
        texts = {
            StreamStatus.DISCONNECTED: "Disconnected",
            StreamStatus.CONNECTING: "Connecting...",
            StreamStatus.CONNECTED: "Live",
            StreamStatus.ERROR: "Error",
            StreamStatus.RECORDING: "Recording",
            StreamStatus.RECONNECTING: "Reconnecting...",
        }
        return texts.get(self, "Unknown")
