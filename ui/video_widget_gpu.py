"""
MediaMTX VMS Client v2.0 - Video Widget (GPU Accelerated)
Custom widget for displaying video with GPU-accelerated rendering.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu, QStackedLayout
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtMultimediaWidgets import QVideoWidget

from core.video_player import VideoPlayer
from ui.overlay_widget import OverlayWidget
from utils.logger import logger
from models.stream import StreamStatus
from models.camera import Camera


class VideoWidget(QWidget):
    """
    GPU-accelerated video widget using Qt Multimedia.
    
    Displays video using QVideoWidget with hardware decoding.
    Overlay information rendered on transparent layer.
    Maintains backward compatible API with OpenCV version.
    """
    
    # Signals
    fullscreen_requested = pyqtSignal(object)  # Emit self for fullscreen
    screenshot_requested = pyqtSignal(object)  # Emit self for screenshot
    camera_dropped = pyqtSignal(str)  # camera_id
    
    def __init__(self, parent=None):
        """Initialize video widget."""
        super().__init__(parent)
        
        # Widget properties
        self.setMinimumSize(QSize(240, 180))
        self.setStyleSheet("background-color: #000000; border: 2px solid #3E3E42;")
        self.setProperty("videoWidget", True)
        
        # Enable dropping
        self.setAcceptDrops(True)
        
        # State
        self._camera: Optional[Camera] = None
        self._status = StreamStatus.DISCONNECTED
        self._motion_active = False
        
        # Create UI components
        self._create_ui()
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        logger.debug("VideoWidget initialized (GPU-accelerated mode)")
    
    def _create_ui(self) -> None:
        """Create user interface components."""
        # Main layout
        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Video output widget (bottom layer - GPU rendered)
        self._video_widget = QVideoWidget()
        self._video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._video_widget.setStyleSheet("background-color: #000000;")
        layout.addWidget(self._video_widget)
        
        # Overlay widget (top layer - transparent)
        self._overlay = OverlayWidget()
        layout.addWidget(self._overlay)
        
        # Video player
        self._player = VideoPlayer(self)
        self._player.set_video_output(self._video_widget)
        
        # Connect player signals
        self._player.status_changed.connect(self._on_status_changed)
        self._player.error_occurred.connect(self._on_error)
        self._player.stream_started.connect(self._on_stream_started)
        self._player.stream_stopped.connect(self._on_stream_stopped)
    
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
            self._overlay.set_camera_name(camera.name)
            self.start_stream()
        else:
            self._overlay.set_camera_name("")
            self._update_border_color()
    
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
        
        # Determine stream quality based on widget size
        widget_size = (self.width(), self.height())
        quality = self._camera.stream_quality
        
        # Start playback
        self._player.set_camera(self._camera)
        self._player.play(quality, widget_size)
        
        logger.info(f"Started stream for {self._camera.name}")
    
    def stop_stream(self) -> None:
        """Stop video streaming."""
        if self._player:
            self._player.stop()
        
        self._status = StreamStatus.DISCONNECTED
        self._overlay.set_status(self._status)
        self._update_border_color()
    
    def stop_stream_async(self) -> None:
        """Signal stream to stop without waiting (backward compatibility)."""
        self.stop_stream()
    
    def wait_for_stream_stop(self) -> None:
        """Wait for stream to stop (backward compatibility - no-op for QMediaPlayer)."""
        pass
    
    def detach_camera(self) -> None:
        """Stop stream and clear camera (backward compatibility)."""
        self.stop_stream()
        self._camera = None
        self._overlay.set_camera_name("")
    
    def switch_quality(self, quality: str) -> None:
        """
        Switch stream quality on the fly.
        
        Args:
            quality: Quality setting ("auto", "high", "low")
        """
        if self._player and self._camera:
            widget_size = (self.width(), self.height())
            self._player.switch_quality(quality, widget_size)
            logger.info(f"Switched to {quality} quality")
    
    def set_motion_detected(self, motion: bool) -> None:
        """
        Set motion detection state.
        
        Args:
            motion: True if motion detected
        """
        self._motion_active = motion
        self._overlay.set_motion_detected(motion)
    
    def set_recording(self, recording: bool) -> None:
        """
        Set recording state.
        
        Args:
            recording: True if recording
        """
        self._overlay.set_recording(recording)
    
    def _on_status_changed(self, status: StreamStatus) -> None:
        """
        Handle stream status change.
        
        Args:
            status: New stream status
        """
        self._status = status
        self._overlay.set_status(status)
        self._update_border_color()
    
    def _on_error(self, error_msg: str) -> None:
        """
        Handle stream error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Stream error for {self._camera.name if self._camera else 'Unknown'}: {error_msg}")
    
    def _on_stream_started(self) -> None:
        """Handle stream start."""
        logger.debug(f"Stream started for {self._camera.name if self._camera else 'Unknown'}")
    
    def _on_stream_stopped(self) -> None:
        """Handle stream stop."""
        logger.debug(f"Stream stopped for {self._camera.name if self._camera else 'Unknown'}")
    
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
            if self._player.is_playing():
                stop_action = QAction("⏹ Stop Stream", self)
                stop_action.triggered.connect(self.stop_stream)
                menu.addAction(stop_action)
            else:
                start_action = QAction("▶ Start Stream", self)
                start_action.triggered.connect(self.start_stream)
                menu.addAction(start_action)
            
            menu.addSeparator()
            
            # Quality selection (if sub-stream available)
            if self._camera.has_sub_stream():
                quality_menu = menu.addMenu("📊 Quality")
                
                auto_action = QAction("Auto", self)
                auto_action.setCheckable(True)
                auto_action.setChecked(self._camera.stream_quality == "auto")
                auto_action.triggered.connect(lambda: self.switch_quality("auto"))
                quality_menu.addAction(auto_action)
                
                high_action = QAction("High (Main Stream)", self)
                high_action.setCheckable(True)
                high_action.setChecked(self._camera.stream_quality == "high")
                high_action.triggered.connect(lambda: self.switch_quality("high"))
                quality_menu.addAction(high_action)
                
                low_action = QAction("Low (Sub Stream)", self)
                low_action.setCheckable(True)
                low_action.setChecked(self._camera.stream_quality == "low")
                low_action.triggered.connect(lambda: self.switch_quality("low"))
                quality_menu.addAction(low_action)
                
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
            
            # Copy Stream URL
            copy_url_action = QAction("📋 Copy Stream URL", self)
            copy_url_action.triggered.connect(self._copy_stream_url)
            menu.addAction(copy_url_action)
            
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
    
    def _copy_stream_url(self) -> None:
        """Copy current stream URL to clipboard."""
        if self._camera:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self._camera.url)
            logger.info(f"Copied stream URL to clipboard: {self._camera.url}")
    
    def _show_camera_info(self) -> None:
        """Show camera information dialog."""
        if self._camera:
            from PyQt6.QtWidgets import QMessageBox
            info = f"Name: {self._camera.name}\n"
            info += f"URL: {self._camera.url}\n"
            if self._camera.sub_stream_url:
                info += f"Sub-stream: {self._camera.sub_stream_url}\n"
            info += f"Type: {self._camera.type}\n"
            info += f"Group: {self._camera.group}\n"
            info += f"Quality: {self._camera.stream_quality}\n"
            info += f"Status: {self._status.get_display_text()}"
            
            QMessageBox.information(self, "Camera Information", info)
    
    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click for fullscreen."""
        if self._camera:
            self.fullscreen_requested.emit(self)
        super().mouseDoubleClickEvent(event)
    
    def get_current_frame(self) -> Optional[object]:
        """
        Get current frame for screenshot.
        
        Note: With QMediaPlayer, frame extraction is more complex.
        Returns placeholder for backward compatibility.
        """
        # TODO: Implement frame grabbing from QMediaPlayer
        # This requires using QVideoSink and capturing frames
        logger.warning("Screenshot from GPU player not yet implemented")
        return None
    
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self._player.is_playing() if self._player else False
    
    def resizeEvent(self, event) -> None:
        """
        Handle widget resize.
        
        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        
        # Auto-adjust stream quality based on new size
        if self._camera and self._camera.stream_quality == "auto" and self._player.is_playing():
            widget_size = (self.width(), self.height())
            current_url = self._player._current_url
            optimal_url = self._camera.get_stream_url("auto", widget_size)
            
            # Switch if optimal URL changed
            if current_url != optimal_url:
                self.switch_quality("auto")
    
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
