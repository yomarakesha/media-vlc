"""
MediaMTX VMS Client v2.0 - Video Stream Manager
Handles video streaming, motion detection, and recording.
"""

import cv2
import numpy as np
import time
import os
from datetime import datetime
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QImage

from models.stream import StreamStatus
from models.camera import Camera
from core.motion_detector import MotionDetector
from utils.logger import logger


class VideoStreamThread(QThread):
    """
    Qt Thread for video streaming from RTSP/HLS sources.
    Handles frame capture, motion detection, recording, and auto-reconnection.
    """
    
    # Qt Signals
    frame_ready = pyqtSignal(QImage)  # Emits pre-converted QImage (performance optimization)
    frame_raw = pyqtSignal(np.ndarray)  # Emits raw BGR frame for recording/motion
    status_changed = pyqtSignal(StreamStatus)  # Emits status updates
    motion_detected = pyqtSignal(bool)  # Emits motion detection state
    error_occurred = pyqtSignal(str)  # Emits error messages
    
    def __init__(self, camera: Camera, fps_limit: int = 15):
        """
        Initialize video stream thread.
        
        Args:
            camera: Camera object with connection details
            fps_limit: Maximum frames per second to process
        """
        super().__init__()
        
        self.camera = camera
        self.fps_limit = fps_limit
        self.frame_interval = 1.0 / fps_limit
        
        # Thread control
        self._running = False
        self._mutex = QMutex()
        
        # Video capture
        self._cap: Optional[cv2.VideoCapture] = None
        self._status = StreamStatus.DISCONNECTED
        
        # Motion detection (MOG2-based)
        self._motion_detector = MotionDetector(
            sensitivity=30,
            min_area=500
        )
        self._last_motion_time: Optional[float] = None
        self._motion_cooldown = 5.0  # Seconds to continue recording after motion stops
        self._motion_regions = []  # Current motion bounding boxes
        
        # Recording
        self._recording = False
        self._recording_start_time: Optional[float] = None
        self._video_writer: Optional[cv2.VideoWriter] = None
        
        # Reconnection
        self._reconnect_interval = 2  # Seconds (reduced for faster polling)
        self._max_reconnect_attempts = 3  # Limit retries (was -1 for infinite)
        self._reconnect_attempt = 0
        
        # Auto-delete when finished
        self.finished.connect(self.deleteLater)
        
        logger.debug(f"VideoStreamThread created for camera: {camera.name}")
    
    def run(self) -> None:
        """Main thread execution loop."""
        self._running = True
        self._set_status(StreamStatus.CONNECTING)
        
        while self._running:
            try:
                # Connect to stream
                if not self._connect():
                    self._handle_reconnection()
                    continue
                
                # Main streaming loop
                last_frame_time = time.time()
                
                while self._running and self._cap and self._cap.isOpened():
                    # Respect FPS limit
                    current_time = time.time()
                    elapsed = current_time - last_frame_time
                    
                    if elapsed < self.frame_interval:
                        time.sleep(self.frame_interval - elapsed)
                        continue
                    
                    # Read frame
                    ret, frame = self._cap.read()
                    
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from {self.camera.name}")
                        self._set_status(StreamStatus.ERROR)
                        break
                    
                    last_frame_time = current_time
                    
                    # Process frame (motion detection, recording)
                    self._process_frame(frame)
                    
                    # Convert to QImage in worker thread (key optimization!)
                    qimage = self._frame_to_qimage(frame)
                    if qimage:
                        self.frame_ready.emit(qimage)
                
                # Connection lost
                if self._running:
                    logger.warning(f"Stream lost for {self.camera.name}")
                    self._cleanup()
                    self._handle_reconnection()
            
            except Exception as e:
                logger.error(f"Error in stream thread for {self.camera.name}: {e}")
                self.error_occurred.emit(str(e))
                self._set_status(StreamStatus.ERROR)
                self._cleanup()
                
                if self._running:
                    self._handle_reconnection()
        
        # Thread stopping
        self._cleanup()
        self._set_status(StreamStatus.DISCONNECTED)
        logger.info(f"VideoStreamThread stopped for {self.camera.name}")
    
    def stop(self) -> None:
        """Stop the streaming thread (handling both flag and wait)."""
        logger.debug(f"Stopping stream for {self.camera.name}")
        self.stop_async()
        self.wait_until_finished()

    def stop_async(self) -> None:
        """Signal the thread to stop without waiting."""
        self._running = False
        
    def wait_until_finished(self, timeout: int = 2000) -> None:
        """Wait for the thread to finish."""
        self.wait(timeout)
    
    def _connect(self) -> bool:
        """
        Connect to video stream.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.camera.name} at {self.camera.url}")
            
            # Construct URL with credentials if present
            url = self.camera.url
            if self.camera.username and self.camera.password:
                if url.startswith("rtsp://"):
                    # Insert credentials after rtsp://
                    url = f"rtsp://{self.camera.username}:{self.camera.password}@{url[7:]}"
                elif url.startswith("http"):
                    # For HLS/HTTP, use request auth or embedded (simple embedding for now)
                    # Note: HLS usually handles auth differently, but this covers basic cases
                    pass
            
            # Create VideoCapture
            # Append timeout to URL for RTSP as extra safety (use 5s timeout)
            if url.startswith("rtsp"):
                separator = "&" if "?" in url else "?"
                # stimeout is in microseconds for ffmpeg (5000000 = 5s)
                # also try 'timeout' which is sometimes used
                url += f"{separator}stimeout=5000000&timeout=5000000"
                    
            if not self._running:
                return False

            self._cap = cv2.VideoCapture(url)
            
            if not self._running:
                if self._cap:
                    self._cap.release()
                return False
            
            # Set buffer size (reduce latency)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test connection
            if not self._cap.isOpened():
                logger.error(f"Failed to open stream: {self.camera.url}")
                return False
            
            # Try reading a frame
            ret, frame = self._cap.read()
            if not ret or frame is None:
                logger.error(f"Failed to read initial frame from {self.camera.url}")
                self._cap.release()
                self._cap = None
                return False
            
            # Success
            self._set_status(StreamStatus.CONNECTED)
            self._reconnect_attempt = 0
            logger.info(f"Successfully connected to {self.camera.name}")
            
            return True
        
        except Exception as e:
            logger.error(f"Connection error for {self.camera.name}: {e}")
            self._cap = None
            return False
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        # Release video capture
        if self._cap:
            self._cap.release()
            self._cap = None
        
        # Stop recording
        self._stop_recording()
    
    def _handle_reconnection(self) -> None:
        """Handle reconnection logic."""
        if not self._running:
            logger.debug(f"Stream thread stopping, skipping reconnection for {self.camera.name}")
            return
        
        self._reconnect_attempt += 1
        
        if self._max_reconnect_attempts > 0 and self._reconnect_attempt > self._max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for {self.camera.name}")
            self.error_occurred.emit(f"Connection failed after {self._reconnect_attempt} attempts")
            self._set_status(StreamStatus.ERROR)
            self._running = False
            return
        
        logger.info(f"Reconnecting to {self.camera.name} (attempt {self._reconnect_attempt})")
        self._set_status(StreamStatus.RECONNECTING)
        
        # Exponential backoff (up to 30 seconds)
        wait_time = min(self._reconnect_interval * (2 ** min(self._reconnect_attempt - 1, 3)), 30)
        
        # Wait before retry (check _running periodically)
        end_time = time.time() + wait_time
        while time.time() < end_time and self._running:
            time.sleep(0.5)
    
    def _process_frame(self, frame: np.ndarray) -> None:
        """
        Process frame for motion detection and recording.
        
        Args:
            frame: Video frame to process
        """
        # Motion detection
        if self.camera.motion_detection:
            motion = self._detect_motion(frame)
            
            if motion != self._motion_detected:
                self._motion_detected = motion
                self.motion_detected.emit(motion)
            
            if motion:
                self._last_motion_time = time.time()
                
                # Start recording if enabled
                if self.camera.recording_enabled and not self._recording:
                    self._start_recording(frame)
        
        # Recording
        if self._recording:
            self._write_frame(frame)
            
            # Check if we should stop recording (motion cooldown)
            if self._last_motion_time and (time.time() - self._last_motion_time > self._motion_cooldown):
                self._stop_recording()
    
    def _detect_motion(self, frame: np.ndarray) -> bool:
        """
        Detect motion using MOG2 background subtraction.
        
        Args:
            frame: Current frame (BGR)
            
        Returns:
            True if motion detected, False otherwise
        """
        # Use MOG2 detector
        motion_detected, regions = self._motion_detector.detect(frame)
        
        # Store regions for visualization
        self._motion_regions = regions
        
        return motion_detected
    
    def _start_recording(self, frame: np.ndarray) -> None:
        """
        Start recording video.
        
        Args:
            frame: First frame to determine video properties
        """
        try:
            # Create recordings directory
            recording_path = "recordings"
            if not os.path.exists(recording_path):
                os.makedirs(recording_path)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(recording_path, f"{self.camera.name}_{timestamp}.mp4")
            
            # Video properties
            height, width, _ = frame.shape
            fps = self.fps_limit
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Create writer
            self._video_writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
            
            if not self._video_writer.isOpened():
                logger.error(f"Failed to create video writer for {self.camera.name}")
                self._video_writer = None
                return
            
            self._recording = True
            self._recording_start_time = time.time()
            self._set_status(StreamStatus.RECORDING)
            
            logger.info(f"Started recording: {filename}")
        
        except Exception as e:
            logger.error(f"Failed to start recording for {self.camera.name}: {e}")
            self._video_writer = None
    
    def _write_frame(self, frame: np.ndarray) -> None:
        """
        Write frame to video file.
        
        Args:
            frame: Frame to write
        """
        if self._video_writer and self._video_writer.isOpened():
            self._video_writer.write(frame)
    
    def _stop_recording(self) -> None:
        """Stop recording video."""
        if self._recording and self._video_writer:
            self._video_writer.release()
            self._video_writer = None
            self._recording = False
            
            duration = time.time() - self._recording_start_time if self._recording_start_time else 0
            logger.info(f"Stopped recording for {self.camera.name} (duration: {duration:.1f}s)")
            
            # Revert status to connected
            self._set_status(StreamStatus.CONNECTED)
    
    def _set_status(self, status: StreamStatus) -> None:
        """
        Set and emit status change.
        
        Args:
            status: New stream status
        """
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)
            logger.debug(f"Stream status for {self.camera.name}: {status}")
    
    def get_status(self) -> StreamStatus:
        """Get current stream status."""
        return self._status
    
    def set_fps_limit(self, fps: int) -> None:
        """
        Set FPS limit.
        
        Args:
            fps: Frames per second limit
        """
        with QMutexLocker(self._mutex):
            self.fps_limit = max(1, min(fps, 30))
            self.frame_interval = 1.0 / self.fps_limit
    
    def set_motion_sensitivity(self, sensitivity: int) -> None:
        """
        Set motion detection sensitivity.
        
        Args:
            sensitivity: Sensitivity value (10-100, lower = more sensitive)
        """
        with QMutexLocker(self._mutex):
            self._motion_detector.set_sensitivity(sensitivity)
    
    def set_motion_min_area(self, min_area: int) -> None:
        """
        Set minimum motion area threshold.
        
        Args:
            min_area: Minimum area in pixels
        """
        with QMutexLocker(self._mutex):
            self._motion_detector.set_min_area(min_area)
    
    def set_detection_zones(self, zones: list) -> None:
        """
        Set motion detection zones.
        
        Args:
            zones: List of DetectionZone objects
        """
        with QMutexLocker(self._mutex):
            self._motion_detector.set_zones(zones)
    
    def get_motion_regions(self) -> list:
        """
        Get current motion regions (bounding boxes).
        
        Returns:
            List of (x, y, width, height) tuples
        """
        with QMutexLocker(self._mutex):
            return self._motion_regions.copy()
    
    def _frame_to_qimage(self, frame: np.ndarray) -> Optional[QImage]:
        """
        Convert OpenCV BGR frame to QImage in worker thread.
        This is a key performance optimization - doing conversion here
        instead of main thread reduces UI lag significantly.
        
        Args:
            frame: BGR numpy array from OpenCV
            
        Returns:
            QImage ready for display, or None if conversion fails
        """
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get dimensions
            height, width, channels = frame_rgb.shape
            bytes_per_line = channels * width
            
            # Create QImage - use copy of data to ensure it persists after this function
            qimage = QImage(
                frame_rgb.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            ).copy()  # .copy() is critical! Without it, data may be garbage collected
            
            return qimage
            
        except Exception as e:
            logger.error(f"Frame conversion error: {e}")
            return None
