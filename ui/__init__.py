"""
MediaMTX VMS Client v2.0 - UI Package
"""

from .main_window import MainWindow
from .video_widget import VideoWidget
from .grid_widget import GridWidget
from .camera_dialog import CameraDialog
from .settings_dialog import SettingsDialog
from .discovery_dialog import DiscoveryDialog
from .resource_tree import ResourceTree
from .ptz_widget import PTZWidget
from .event_log import EventLog
from .onvif_nvr_dialog import ONVIFNVRDialog
from .fullscreen_dialog import FullscreenVideoDialog
from .playback_widget import PlaybackWidget
from .emap_widget import EMapWidget

__all__ = [
    'MainWindow',
    'VideoWidget',
    'GridWidget',
    'CameraDialog',
    'SettingsDialog',
    'DiscoveryDialog',
    'ResourceTree',
    'PTZWidget',
    'EventLog',
    'ONVIFNVRDialog',
    'FullscreenVideoDialog',
    'PlaybackWidget',
    'EMapWidget'
]
