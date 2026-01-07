"""
MediaMTX VMS Client v2.0 - Video Widget
Custom QLabel widget for displaying video with overlay information.
"""

import cv2
import numpy as np
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QAction

from core.stream_manager import VideoStreamThread
from utils.logger import logger
from models.stream import StreamStatus
from models.camera import Camera


class VideoWidget(QLabel):
    """
    Custom widget for displaying video feed from a camera.
    Shows video with overlay (camera name, timestamp, status).
    Supports fullscreen mode and context menu.
    """
    
    # Signals
    fullscreen_requested = pyqtSignal(object)  # Emit self for fullscreen
    screenshot_requested = pyqtSignal(object)  # Emit self for screenshot
    camera_dropped = pyqtSignal(str) # camera_id
    
    def __init__(self, parent=None):
        """Initialize video widget."""
        super().__init__(parent)
        
        # Widget properties
        self.setMinimumSize(QSize(240, 180))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)
        self.setStyleSheet("background-color: #000000; border: 2px solid #3E3E42;")
        self.setProperty("videoWidget", True)
        
        # Enable dropping
        self.setAcceptDrops(True)
        
        # State
        self._camera: Optional[Camera] = None
        self._stream_thread: Optional[VideoStreamThread] = None
        self._status = StreamStatus.DISCONNECTED
        self._current_qimage: Optional[QImage] = None  # Now stores QImage, not numpy
        self._motion_active = False
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Display "No Camera" message
        self._update_display()
    

    
    def set_camera(self, camera: Optional[Camera]) -> None:
        """
        Set camera and start streaming.
        
        Args:
            camera: Camera object or None to clear
        """
        # Stop existing stream
        self.stop_stream()
        
        self._camera = camera
        
        if camera:
            logger.info(f"VideoWidget assigned to camera: {camera.name}")
            self.start_stream()
        else:
            self._update_display()
    
    def get_camera(self) -> Optional[Camera]:
        """Get current camera."""
        return self._camera
    
    def start_stream(self) -> None:
        """Start video streaming."""
        if not self._camera:
            logger.warning("Cannot start stream: no camera assigned")
            return
        
        # Stop existing stream
        self.stop_stream()
        
        # Get FPS limit from config
        from utils.config import config
        fps_limit = config.get("settings.fps_limit", 15)
        
        # Create and start stream thread
        self._stream_thread = VideoStreamThread(self._camera, fps_limit)
        self._stream_thread.frame_ready.connect(self._on_frame_ready)
        self._stream_thread.status_changed.connect(self._on_status_changed)
        self._stream_thread.motion_detected.connect(self._on_motion_detected)
        self._stream_thread.error_occurred.connect(self._on_error)
        self._stream_thread.finished.connect(self._on_thread_finished)
        
        self._stream_thread.start()
        logger.info(f"Started stream for {self._camera.name}")
    
    def stop_stream(self) -> None:
        """Stop video streaming synchronously."""
        self.stop_stream_async()
        self.wait_for_stream_stop()

    def stop_stream_async(self) -> None:
        """Signal stream to stop without waiting."""
        if self._stream_thread:
            logger.info(f"Signal stop stream for {self._camera.name if self._camera else 'Unknown'}")
            self._stream_thread.stop_async()

    def wait_for_stream_stop(self) -> None:
        """Wait for stream to stop and cleanup."""
        if self._stream_thread:
            self._stream_thread.wait_until_finished()
            self._stream_thread = None
            self._status = StreamStatus.DISCONNECTED
            self._current_qimage = None
            self._update_display()
    
    def detach_camera(self) -> None:
        """Stop stream asynchronously and clear camera (non-blocking)."""
        if self._stream_thread:
            logger.info(f"Detaching stream for {self._camera.name if self._camera else 'Unknown'}")
            thread_to_stop = self._stream_thread
            self._stream_thread = None
            
            # Disconnect signals to prevent updates to detached widget
            try:
                thread_to_stop.frame_ready.disconnect(self._on_frame_ready)
                thread_to_stop.status_changed.disconnect(self._on_status_changed)
                thread_to_stop.motion_detected.disconnect(self._on_motion_detected)
                thread_to_stop.error_occurred.disconnect(self._on_error)
            except (TypeError, RuntimeError):
                pass  # Signal was not connected
            
            # Signal thread to stop (non-blocking)
            thread_to_stop.stop_async()
            
            # Thread will clean itself up via finished -> deleteLater

        self._camera = None
        self._status = StreamStatus.DISCONNECTED
        self._current_qimage = None
        self._update_border_color()
        self._update_display()

    def _on_frame_ready(self, qimage: QImage) -> None:
        """
        Handle new frame from stream.
        
        Args:
            qimage: Pre-converted QImage from worker thread
        """
        self._current_qimage = qimage
        self._update_display()
    
    def _on_status_changed(self, status: StreamStatus) -> None:
        """
        Handle stream status change.
        
        Args:
            status: New stream status
        """
        self._status = status
        self._update_border_color()
    
    def _on_motion_detected(self, motion: bool) -> None:
        """
        Handle motion detection event.
        
        Args:
            motion: True if motion detected
        """
        self._motion_active = motion
    
    def _on_error(self, error_msg: str) -> None:
        """
        Handle stream error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Stream error for {self._camera.name if self._camera else 'Unknown'}: {error_msg}")

    def _on_thread_finished(self) -> None:
        """Handle stream thread finishing safely."""
        # Only cleanup if this is the currently active thread
        if self.sender() == self._stream_thread:
            logger.info(f"Stream thread finished for {self._camera.name if self._camera else 'Unknown'}, cleaning up.")
            self._stream_thread = None
            self._status = StreamStatus.DISCONNECTED
            self._update_border_color()
            self._update_display()
    
    def _update_display(self) -> None:
        """Update widget display with current QImage and overlay."""
        if self._current_qimage is not None and self._camera:
            # Create pixmap from pre-converted QImage (fast!)
            pixmap = QPixmap.fromImage(self._current_qimage)
            
            # Draw overlay using QPainter (faster than OpenCV on main thread)
            self._draw_overlay_on_pixmap(pixmap)
            
            # Scale to widget size while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation  # Use Fast instead of Smooth for performance
            )
            
            self.setPixmap(scaled_pixmap)
        else:
            # No camera or no frame
            self.clear()
    
    def _draw_overlay_on_pixmap(self, pixmap: QPixmap) -> None:
        """
        Draw overlay information on pixmap using QPainter.
        This is much faster than OpenCV text drawing.
        
        Args:
            pixmap: QPixmap to draw on
        """
        from utils.config import config
        
        if not config.get("settings.show_overlay", True):
            return
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Font setup
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Camera name (top-left)
        if self._camera:
            # Shadow
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawText(12, 22, self._camera.name)
            # Text
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(10, 20, self._camera.name)
        
        # Timestamp (top-right)
        if config.get("settings.show_timestamp", True):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(timestamp)
            x = pixmap.width() - text_width - 10
            # Shadow
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawText(x + 2, 22, timestamp)
            # Text
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(x, 20, timestamp)
        
        # Status indicator (bottom-left)
        status_text = self._status.get_display_text()
        if self._motion_active:
            status_text += " [MOTION]"
            painter.setPen(QPen(QColor(244, 135, 113), 1))
        else:
            status_color = self._status.get_color()
            painter.setPen(QPen(QColor(status_color), 1))
        
        y = pixmap.height() - 10
        painter.drawText(10, y, status_text)
        
        # Recording indicator (red circle)
        if self._status == StreamStatus.RECORDING:
            painter.setBrush(QColor(255, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(22, 40, 16, 16)
        
        painter.end()
    
    def _draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw overlay information on frame.
        
        Args:
            frame: Video frame (RGB format)
            
        Returns:
            Frame with overlay
        """
        from utils.config import config
        
        if not config.get("settings.show_overlay", True):
            return frame
        
        frame = frame.copy()
        
        # Overlay settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        color = (255, 255, 255)  # White
        shadow_color = (0, 0, 0)  # Black shadow
        
        # Camera name (top-left)
        if self._camera:
            name_text = self._camera.name
            text_size = cv2.getTextSize(name_text, font, font_scale, thickness)[0]
            
            # Shadow
            cv2.putText(frame, name_text, (12, 32), font, font_scale, shadow_color, thickness + 1, cv2.LINE_AA)
            # Text
            cv2.putText(frame, name_text, (10, 30), font, font_scale, color, thickness, cv2.LINE_AA)
        
        # Timestamp (top-right)
        if config.get("settings.show_timestamp", True):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_size = cv2.getTextSize(timestamp, font, font_scale, thickness)[0]
            x = frame.shape[1] - text_size[0] - 10
            
            # Shadow
            cv2.putText(frame, timestamp, (x + 2, 32), font, font_scale, shadow_color, thickness + 1, cv2.LINE_AA)
            # Text
            cv2.putText(frame, timestamp, (x, 30), font, font_scale, color, thickness, cv2.LINE_AA)
        
        # Status indicator (bottom-left)
        status_text = self._status.get_display_text()
        status_color_hex = self._status.get_color()
        status_color = tuple(int(status_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # Motion indicator
        if self._motion_active:
            status_text += " [MOTION]"
            status_color = (244, 135, 113)  # Red for motion
        
        y = frame.shape[0] - 10
        
        # Shadow
        cv2.putText(frame, status_text, (12, y + 2), font, font_scale, shadow_color, thickness + 1, cv2.LINE_AA)
        # Text
        cv2.putText(frame, status_text, (10, y), font, font_scale, status_color, thickness, cv2.LINE_AA)
        
        # Recording indicator (red circle)
        if self._status == StreamStatus.RECORDING:
            cv2.circle(frame, (30, 50), 8, (0, 0, 255), -1)
        
        return frame
    
    def _update_border_color(self) -> None:
        """Update widget border color based on status."""
        color = self._status.get_color()
        self.setStyleSheet(f"background-color: #000000; border: 2px solid {color};")
        self.setProperty("status", self._status.name.lower())
    
    def _show_context_menu(self, position) -> None:
        """
        Show context menu.
        
        Args:
            position: Menu position
        """
        menu = QMenu(self)
        
        if self._camera:
            # Start/Stop
            if self._stream_thread and self._stream_thread.isRunning():
                stop_action = QAction("⏹ Stop Stream", self)
                # Use async stop to avoid freezing UI if connection is hung
                stop_action.triggered.connect(self.stop_stream_async)
                menu.addAction(stop_action)
            else:
                start_action = QAction("▶ Start Stream", self)
                start_action.triggered.connect(self.start_stream)
                menu.addAction(start_action)
            
            menu.addSeparator()
            
            # Screenshot
            screenshot_action = QAction("📷 Screenshot", self)
            screenshot_action.triggered.connect(lambda: self.screenshot_requested.emit(self))
            menu.addAction(screenshot_action)
            
            # Fullscreen
            fullscreen_action = QAction("⛶ Fullscreen", self)
            fullscreen_action.triggered.connect(lambda: self.fullscreen_requested.emit(self))
            menu.addAction(fullscreen_action)
            
            menu.addSeparator()
            
            # Info
            info_action = QAction("ℹ Camera Info", self)
            info_action.triggered.connect(self._show_camera_info)
            menu.addAction(info_action)
        else:
            no_camera_action = QAction("No camera assigned", self)
            no_camera_action.setEnabled(False)
            menu.addAction(no_camera_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _show_camera_info(self) -> None:
        """Show camera information dialog."""
        if self._camera:
            from PyQt6.QtWidgets import QMessageBox
            info = f"Name: {self._camera.name}\n"
            info += f"URL: {self._camera.url}\n"
            info += f"Type: {self._camera.type}\n"
            info += f"Group: {self._camera.group}\n"
            info += f"Status: {self._status.get_display_text()}"
            
            QMessageBox.information(self, "Camera Information", info)
    
    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click for fullscreen."""
        if self._camera:
            self.fullscreen_requested.emit(self)
        super().mouseDoubleClickEvent(event)
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current frame for screenshot."""
        # Convert QImage back to numpy array for screenshot
        if self._current_qimage is None:
            return None
        
        qimage = self._current_qimage
        width = qimage.width()
        height = qimage.height()
        
        # Get raw bytes from QImage
        ptr = qimage.bits()
        ptr.setsize(height * width * 3)
        arr = np.array(ptr).reshape(height, width, 3)
        
        # Convert RGB to BGR for OpenCV compatibility
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self._stream_thread is not None and self._stream_thread.isRunning()

    def dragEnterEvent(self, event) -> None:
        """Handle drag enter."""
        if event.mimeData().hasFormat("application/x-mediamtx-camera"):
            event.acceptProposedAction()
            self.setStyleSheet("background-color: #1E1E1E; border: 2px dashed #007ACC;")
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave."""
        self._update_border_color()
    
    def dropEvent(self, event) -> None:
        """Handle drop event."""
        if event.mimeData().hasFormat("application/x-mediamtx-camera"):
            byte_data = event.mimeData().data("application/x-mediamtx-camera")
            from PyQt6.QtCore import QDataStream, QIODevice
            stream = QDataStream(byte_data, QIODevice.OpenModeFlag.ReadOnly)
            camera_id_bytes = stream.readString()
            if camera_id_bytes:
                camera_id = camera_id_bytes.decode('utf-8')
                self.camera_dropped.emit(camera_id)
                event.acceptProposedAction()
        
        self._update_border_color()
