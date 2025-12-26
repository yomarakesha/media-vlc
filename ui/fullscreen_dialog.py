"""
MediaMTX VMS Client v2.0 - Fullscreen Video Dialog
Fullscreen video display with ESC to exit.
"""

from typing import Optional
import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QPixmap, QImage

from models.camera import Camera
from core.stream_manager import VideoStreamThread
from models.stream import StreamStatus
from utils.logger import logger
from utils.config import config


class FullscreenVideoDialog(QDialog):
    """
    Fullscreen video display dialog.
    Press ESC to exit fullscreen.
    """
    
    closed = pyqtSignal()
    
    def __init__(self, camera: Camera, parent=None):
        """
        Initialize fullscreen video dialog.
        
        Args:
            camera: Camera to display
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._camera = camera
        self._stream_thread: Optional[VideoStreamThread] = None
        self._current_frame: Optional[np.ndarray] = None
        
        self.setWindowTitle(f"Fullscreen - {camera.name}")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Video display
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._video_label = QLabel()
        self._video_label.setStyleSheet("background-color: black;")
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._video_label)
        
        # Start fullscreen
        self.showFullScreen()
        
        # Start stream
        self._start_stream()
        
        logger.info(f"Fullscreen mode started for {camera.name}")
    
    def _start_stream(self) -> None:
        """Start video streaming."""
        fps_limit = config.get("settings.fps_limit", 15)
        
        self._stream_thread = VideoStreamThread(self._camera, fps_limit)
        self._stream_thread.frame_ready.connect(self._on_frame_ready)
        self._stream_thread.status_changed.connect(self._on_status_changed)
        self._stream_thread.start()
    
    def _stop_stream(self) -> None:
        """Stop video streaming."""
        if self._stream_thread:
            self._stream_thread.stop()
            self._stream_thread = None
    
    def _on_frame_ready(self, frame: np.ndarray) -> None:
        """
        Handle new frame from stream.
        
        Args:
            frame: Video frame (BGR format)
        """
        import cv2
        
        self._current_frame = frame
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to QPixmap
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale to fill screen while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self._video_label.setPixmap(scaled_pixmap)
    
    def _on_status_changed(self, status: StreamStatus) -> None:
        """Handle stream status change."""
        if status == StreamStatus.ERROR:
            self._video_label.setText(f"Connection Error\n{self._camera.name}\n\nPress ESC to exit")
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        self._stop_stream()
        self.closed.emit()
        logger.info(f"Fullscreen mode ended for {self._camera.name}")
        super().closeEvent(event)
