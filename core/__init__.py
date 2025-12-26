"""
MediaMTX VMS Client v2.0 - Core Package
"""

from .camera_manager import camera_manager, CameraManager
from .nvr_manager import nvr_manager, NVRManager
from .discovery import ONVIFDiscovery, MediaMTXDiscovery, DiscoveryThread, DiscoveredDevice

__all__ = [
    'camera_manager', 'CameraManager',
    'nvr_manager', 'NVRManager',
    'ONVIFDiscovery', 'MediaMTXDiscovery', 'DiscoveryThread', 'DiscoveredDevice'
]
