"""
MediaMTX VMS Client v2.0 - PTZ Controller
ONVIF PTZ Control implementation.
"""

import threading
from urllib.parse import urlparse
from typing import Optional, Dict

# Check for onvif support
try:
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except ImportError:
    ONVIF_AVAILABLE = False

from models.camera import Camera
from utils.logger import logger


class PTZController:
    """
    Controller for ONVIF PTZ cameras.
    Handles connection, movement, and presets.
    """
    
    def __init__(self):
        """Initialize PTZ controller."""
        self.camera: Optional[Camera] = None
        self.ptz = None
        self.token = None
        self.active = False
        self._lock = threading.Lock()
    
    def connect(self, camera: Camera) -> bool:
        """
        Connect to camera PTZ service.
        This blocking call should be run in a thread.
        
        Args:
            camera: Camera to connect to
            
        Returns:
            True if successful
        """
        if not ONVIF_AVAILABLE:
            logger.error("python-onvif-zeep not installed. PTZ disabled.")
            return False
            
        with self._lock:
            self.camera = camera
            self.active = False
            self.ptz = None
            self.token = None
            
            if not camera.url:
                return False
                
            try:
                # Extract host and port
                parsed = urlparse(camera.url)
                host = parsed.hostname
                if not host:
                    # Fallback for simple IPs
                    if "://" not in camera.url:
                        host = camera.url.split("/")[0].split(":")[0]
                    else:
                        host = camera.url
                
                # Assume default ONVIF port 80 if not specified
                # Note: models/camera.py doesn't store management port separate from RTSP URL
                # We try 80 first.
                port = 80
                
                logger.info(f"Connecting to PTZ service on {host}:{port}...")
                
                mycam = ONVIFCamera(
                    host, port, 
                    camera.username, camera.password
                )
                
                # Create media service to get profile
                media = mycam.create_media_service()
                profiles = media.GetProfiles()
                
                if not profiles:
                    logger.error(f"No profiles found for {camera.name}")
                    return False
                
                self.token = profiles[0].token
                
                # Create PTZ service
                self.ptz = mycam.create_ptz_service()
                
                # Get configuration options (optional check)
                # request = self.ptz.create_type('GetConfigurationOptions')
                # request.ConfigurationToken = self.token
                # self.ptz.GetConfigurationOptions(request)
                
                self.active = True
                logger.info(f"PTZ connected for {camera.name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect PTZ for {camera.name}: {e}")
                return False

    def move_continuous(self, pan: float, tilt: float, zoom: float) -> None:
        """
        Start continuous movement.
        
        Args:
            pan: Pan speed (-1.0 to 1.0)
            tilt: Tilt speed (-1.0 to 1.0)
            zoom: Zoom speed (-1.0 to 1.0)
        """
        if not self.active or not self.ptz:
            return

        try:
            status = self.ptz.create_type('ContinuousMove')
            status.ProfileToken = self.token
            
            status.Velocity = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }
            
            self.ptz.ContinuousMove(status)
            
        except Exception as e:
            logger.error(f"PTZ Move error: {e}")

    def stop(self) -> None:
        """Stop all movement."""
        if not self.active or not self.ptz:
            return

        try:
            status = self.ptz.create_type('Stop')
            status.ProfileToken = self.token
            status.PanTilt = True
            status.Zoom = True
            
            self.ptz.Stop(status)
            
        except Exception as e:
            logger.error(f"PTZ Stop error: {e}")

    def goto_preset(self, preset_index: int) -> None:
        """
        Go to preset index.
        Note: Simple impl assumes presets are named or indexed 1..N.
        ONVIF uses string tokens.
        
        Args:
            preset_index: 1-based index
        """
        if not self.active or not self.ptz:
            return

        try:
            # First get available presets
            presets = self.ptz.GetPresets({'ProfileToken': self.token})
            
            target_token = None
            
            # Simple matching strategy
            if 0 < preset_index <= len(presets):
                target_token = presets[preset_index - 1].token
            else:
                # Try to find by name "PresetN"
                name_key = str(preset_index)
                for p in presets:
                    if name_key in p.Name or name_key in p.token:
                        target_token = p.token
                        break
            
            if target_token:
                self.ptz.GotoPreset({'ProfileToken': self.token, 'PresetToken': target_token, 'Speed': {'PanTilt': {'x': 1, 'y': 1}, 'Zoom': {'x': 1}}})
                logger.info(f"Going to preset {preset_index} (token: {target_token})")
            else:
                logger.warning(f"Preset {preset_index} not found")
                
        except Exception as e:
            logger.error(f"PTZ GotoPreset error: {e}")

    def save_preset(self, preset_index: int) -> None:
        """
        Save current position as preset.
        
        Args:
            preset_index: 1-based index
        """
        if not self.active or not self.ptz:
            return

        try:
            # Name it "Preset X"
            name = f"Preset {preset_index}"
            
            # Note: SetPreset creates or updates
            self.ptz.SetPreset({'ProfileToken': self.token, 'PresetName': name})
            logger.info(f"Saved preset {name}")
            
        except Exception as e:
            logger.error(f"PTZ SavePreset error: {e}")
