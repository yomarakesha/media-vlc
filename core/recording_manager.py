"""
MediaMTX VMS Client v2.0 - Advanced Recording Manager
Manages video recording with pre-buffer, scheduling, and continuous modes.
"""

import cv2
import os
import json
from collections import deque
from datetime import datetime, time as dt_time
from typing import Optional, List, Deque, Tuple
from dataclasses import dataclass, field, asdict
import threading

from models.camera import Camera
from utils.logger import logger


@dataclass
class RecordingSchedule:
    """
    Recording schedule configuration.
    
    Attributes:
        days: List of day names ("Monday", "Tuesday", etc.)
        start_time: Start time "HH:MM"
        end_time: End time "HH:MM"
        enabled: Whether schedule is active
    """
    days: List[str]
    start_time: str
    end_time: str
    enabled: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RecordingSchedule':
        """Create from dictionary."""
        return cls(**data)
    
    def is_active_now(self) -> bool:
        """
        Check if schedule is currently active.
        
        Returns:
            True if recording should be active now
        """
        if not self.enabled:
            return False
        
        now = datetime.now()
        current_day = now.strftime("%A")
        current_time = now.time()
        
        # Check day
        if current_day not in self.days:
            return False
        
        # Parse times
        start_h, start_m = map(int, self.start_time.split(":"))
        end_h, end_m = map(int, self.end_time.split(":"))
        
        start_time = dt_time(start_h, start_m)
        end_time = dt_time(end_h, end_m)
        
        # Check time range
        if start_time <= end_time:
            # Same-day range
            return start_time <= current_time <= end_time
        else:
            # Overnight range
            return current_time >= start_time or current_time <= end_time


class RecordingManager:
    """
    Advanced recording manager with pre-buffer, scheduling, and continuous modes.
    
    Recording Modes:
    - motion: Record when motion detected (with pre/post buffer)
    - continuous: Record continuously
    - scheduled: Record based on time schedule
    """
    
    def __init__(
        self,
        camera: Camera,
        mode: str = "motion",
        pre_buffer_seconds: int = 5,
        post_buffer_seconds: int = 10,
        recording_path: str = "recordings",
        fps: int = 15
    ):
        """
        Initialize recording manager.
        
        Args:
            camera: Camera instance
            mode: Recording mode ("motion", "continuous", "scheduled")
            pre_buffer_seconds: Seconds to buffer before motion
            post_buffer_seconds: Seconds to continue after motion stops
            recording_path: Directory for recordings
            fps: Frames per second
        """
        self._camera = camera
        self._mode = mode
        self._pre_buffer_seconds = pre_buffer_seconds
        self._post_buffer_seconds = post_buffer_seconds
        self._recording_path = recording_path
        self._fps = fps
        
        # Pre-buffer (circular deque)
        buffer_size = pre_buffer_seconds * fps
        self._frame_buffer: Deque[Tuple[object, float]] = deque(maxlen=buffer_size)
        
        # Recording state
        self._recording = False
        self._recorder: Optional[cv2.VideoWriter] = None
        self._current_file: Optional[str] = None
        self._recording_start_time: Optional[float] = None
        self._frames_written = 0
        
        # Motion tracking
        self._motion_active = False
        self._last_motion_time: Optional[float] = None
        
        # Scheduling
        self._schedules: List[RecordingSchedule] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Ensure recording directory exists
        os.makedirs(recording_path, exist_ok=True)
        
        logger.info(f"RecordingManager initialized for {camera.name} (mode={mode})")
    
    def on_frame(self, frame: object, timestamp: float) -> None:
        """
        Process new frame.
        
        Args:
            frame: Video frame (numpy array)
            timestamp: Frame timestamp
        """
        with self._lock:
            # Add to pre-buffer
            self._frame_buffer.append((frame, timestamp))
            
            # Determine if should be recording
            should_record = self._should_record_now()
            
            if should_record and not self._recording:
                self._start_recording(frame)
            elif not should_record and self._recording:
                # Check post-buffer timeout
                if self._mode == "motion" and self._last_motion_time:
                    time_since_motion = timestamp - self._last_motion_time
                    if time_since_motion > self._post_buffer_seconds:
                        self._stop_recording()
                elif self._mode == "scheduled":
                    self._stop_recording()
            
    # Write frame if recording
            if self._recording and self._recorder:
                self._recorder.write(frame)
                self._frames_written += 1
    
    def on_motion(self, detected: bool, timestamp: float) -> None:
        """
        Handle motion detection event.
        
        Args:
            detected: True if motion detected
            timestamp: Event timestamp
        """
        with self._lock:
            self._motion_active = detected
            
            if detected:
                self._last_motion_time = timestamp
                
                # Start recording if in motion mode
                if self._mode == "motion" and not self._recording:
                    # Trigger will be handled in next on_frame call
                    pass
    
    def set_mode(self, mode: str) -> None:
        """
        Set recording mode.
        
        Args:
            mode: New mode ("motion", "continuous", "scheduled")
        """
        with self._lock:
            if mode not in ["motion", "continuous", "scheduled"]:
                logger.error(f"Invalid recording mode: {mode}")
                return
            
            old_mode = self._mode
            self._mode = mode
            logger.info(f"Recording mode changed: {old_mode} → {mode}")
            
            # Stop current recording if mode changed
            if self._recording:
                self._stop_recording()
    
    def set_schedules(self, schedules: List[RecordingSchedule]) -> None:
        """
        Set recording schedules.
        
        Args:
            schedules: List of RecordingSchedule objects
        """
        with self._lock:
            self._schedules = schedules.copy()
            logger.info(f"Recording schedules updated: {len(schedules)} schedule(s)")
    
    def get_schedules(self) -> List[RecordingSchedule]:
        """Get current schedules."""
        with self._lock:
            return self._schedules.copy()
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
            return self._recording
    
    def get_current_file(self) -> Optional[str]:
        """Get current recording file path."""
        with self._lock:
            return self._current_file
    
    def get_statistics(self) -> dict:
        """
        Get recording statistics.
        
        Returns:
            Dictionary with recording stats
        """
        with self._lock:
            duration = 0.0
            if self._recording and self._recording_start_time:
                import time
                duration = time.time() - self._recording_start_time
            
            return {
                'recording': self._recording,
                'mode': self._mode,
                'current_file': self._current_file,
                'frames_written': self._frames_written,
                'duration': duration,
                'schedules_count': len(self._schedules)
            }
    
    def force_start(self) -> bool:
        """
        Force start recording (manual override).
        
        Returns:
            True if started successfully
        """
        with self._lock:
            if self._recording:
                return False
            
            # Get last frame from buffer
            if not self._frame_buffer:
                logger.warning("Cannot start recording: no frames in buffer")
                return False
            
            last_frame, _ = self._frame_buffer[-1]
            self._start_recording(last_frame)
            return True
    
    def force_stop(self) -> bool:
        """
        Force stop recording (manual override).
        
        Returns:
            True if stopped successfully
        """
        with self._lock:
            if not self._recording:
                return False
            
            self._stop_recording()
            return True
    
    def cleanup(self) -> None:
        """Clean up resources."""
        with self._lock:
            if self._recording:
                self._stop_recording()
            
            self._frame_buffer.clear()
            logger.info(f"RecordingManager cleaned up for {self._camera.name}")
    
    def _should_record_now(self) -> bool:
        """
        Determine if should be recording now based on mode.
        
        Returns:
            True if should record
        """
        if self._mode == "continuous":
            return True
        
        elif self._mode == "motion":
            return self._motion_active
        
        elif self._mode == "scheduled":
            # Check if any schedule is active
            for schedule in self._schedules:
                if schedule.is_active_now():
                    return True
            return False
        
        return False
    
    def _start_recording(self, frame: object) -> None:
        """
        Start recording video file.
        
        Args:
            frame: First frame (for video properties)
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self._camera.name}_{timestamp}.mp4"
            filepath = os.path.join(self._recording_path, filename)
            
            # Video properties
            height, width = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Create writer
            self._recorder = cv2.VideoWriter(filepath, fourcc, self._fps, (width, height))
            
            if not self._recorder.isOpened():
                logger.error(f"Failed to create video writer: {filepath}")
                self._recorder = None
                return
            
            # Write pre-buffered frames
            for buffered_frame, _ in self._frame_buffer:
                self._recorder.write(buffered_frame)
                self._frames_written += 1
            
            self._recording = True
            self._current_file = filepath
            import time
            self._recording_start_time = time.time()
            self._frames_written = len(self._frame_buffer)
            
            logger.info(f"Started recording: {filepath} (pre-buffered {len(self._frame_buffer)} frames)")
            
            # Save recording metadata
            self._save_metadata(filepath)
        
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._recorder = None
    
    def _stop_recording(self) -> None:
        """Stop recording video file."""
        if not self._recording or not self._recorder:
            return
        
        try:
            self._recorder.release()
            
            import time
            duration = time.time() - self._recording_start_time if self._recording_start_time else 0
            
            logger.info(f"Stopped recording: {self._current_file} "
                       f"(duration={duration:.1f}s, frames={self._frames_written})")
            
            # Update metadata
            self._save_metadata(self._current_file, final=True)
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
        
        finally:
            self._recorder = None
            self._current_file = None
            self._recording = False
            self._recording_start_time = None
            self._frames_written = 0
    
    def _save_metadata(self, video_path: str, final: bool = False) -> None:
        """
        Save recording metadata to JSON file.
        
        Args:
            video_path: Path to video file
            final: True if recording completed
        """
        try:
            metadata_path = video_path.replace('.mp4', '.json')
            
            import time
            duration = time.time() - self._recording_start_time if self._recording_start_time else 0
            
            metadata = {
                'camera_name': self._camera.name,
                'camera_id': self._camera.id,
                'start_time': datetime.fromtimestamp(self._recording_start_time).isoformat() if self._recording_start_time else None,
                'duration': duration,
                'frames': self._frames_written,
                'fps': self._fps,
                'mode': self._mode,
                'completed': final
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")
