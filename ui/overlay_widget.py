"""
MediaMTX VMS Client v2.0 - Video Overlay Widget
Transparent overlay widget for displaying OSD elements on top of video.
"""

from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from models.stream import StreamStatus
from utils.logger import logger


class OverlayWidget(QWidget):
    """
    Transparent overlay widget for video OSD (On-Screen Display).
    
    Displays:
    - Camera name
    - Timestamp
    - Status indicators (connected/recording/motion)
    - FPS counter
    - Bitrate indicator
    
    This widget sits on top of QVideoWidget to provide UI elements
    while keeping video rendering on the GPU.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize overlay widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Make widget transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Overlay data
        self._camera_name: str = ""
        self._status: StreamStatus = StreamStatus.IDLE
        self._show_overlay: bool = True
        self._show_timestamp: bool = True
        self._show_fps: bool = False
        self._is_recording: bool = False
        self._motion_detected: bool = False
        
        # Performance metrics
        self._fps: float = 0.0
        self._bitrate: float = 0.0
        
        # Timestamp update timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)  # Update every second
        
        # Fonts
        self._title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self._info_font = QFont("Segoe UI", 9)
        self._small_font = QFont("Segoe UI", 8)
    
    def set_camera_name(self, name: str) -> None:
        """
        Set camera name to display.
        
        Args:
            name: Camera name
        """
        self._camera_name = name
        self.update()
    
    def set_status(self, status: StreamStatus) -> None:
        """
        Set stream status.
        
        Args:
            status: Stream status
        """
        self._status = status
        self.update()
    
    def set_recording(self, recording: bool) -> None:
        """
        Set recording indicator.
        
        Args:
            recording: True if recording
        """
        self._is_recording = recording
        self.update()
    
    def set_motion_detected(self, motion: bool) -> None:
        """
        Set motion detection indicator.
        
        Args:
            motion: True if motion detected
        """
        self._motion_detected = motion
        self.update()
    
    def set_fps(self, fps: float) -> None:
        """
        Set FPS counter value.
        
        Args:
            fps: Frames per second
        """
        self._fps = fps
        if self._show_fps:
            self.update()
    
    def set_bitrate(self, bitrate: float) -> None:
        """
        Set bitrate indicator (Mbps).
        
        Args:
            bitrate: Bitrate in Mbps
        """
        self._bitrate = bitrate
        self.update()
    
    def set_overlay_visible(self, visible: bool) -> None:
        """
        Show/hide overlay.
        
        Args:
            visible: True to show overlay
        """
        self._show_overlay = visible
        self.update()
    
    def set_timestamp_visible(self, visible: bool) -> None:
        """
        Show/hide timestamp.
        
        Args:
            visible: True to show timestamp
        """
        self._show_timestamp = visible
        self.update()
    
    def set_fps_visible(self, visible: bool) -> None:
        """
        Show/hide FPS counter.
        
        Args:
            visible: True to show FPS
        """
        self._show_fps = visible
        self.update()
    
    def paintEvent(self, event) -> None:
        """
        Paint overlay elements.
        
        Args:
            event: Paint event
        """
        if not self._show_overlay:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw status-based border
        self._draw_border(painter)
        
        # Draw camera name (top-left)
        if self._camera_name:
            self._draw_camera_name(painter)
        
        # Draw timestamp (top-right)
        if self._show_timestamp:
            self._draw_timestamp(painter)
        
        # Draw status indicator (top-left, below name)
        self._draw_status_indicator(painter)
        
        # Draw recording indicator (top-right with red circle)
        if self._is_recording:
            self._draw_recording_indicator(painter)
        
        # Draw motion indicator
        if self._motion_detected:
            self._draw_motion_indicator(painter)
        
        # Draw FPS counter (bottom-left)
        if self._show_fps:
            self._draw_fps_counter(painter)
        
        # Draw bitrate (bottom-right)
        if self._bitrate > 0:
            self._draw_bitrate(painter)
    
    def _draw_border(self, painter: QPainter) -> None:
        """
        Draw status-based border.
        
        Args:
            painter: QPainter instance
        """
        # Determine border color based on status
        if self._status == StreamStatus.CONNECTED:
            color = QColor("#4EC9B0")  # Success green
            width = 2
        elif self._status == StreamStatus.CONNECTING:
            color = QColor("#CE9178")  # Warning orange
            width = 2
        elif self._status == StreamStatus.ERROR:
            color = QColor("#F48771")  # Error red
            width = 3
        elif self._is_recording:
            color = QColor("#F48771")  # Recording red
            width = 3
        else:
            color = QColor("#3E3E42")  # Default gray
            width = 2
        
        pen = QPen(color, width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        rect = self.rect().adjusted(width, width, -width, -width)
        painter.drawRect(rect)
    
    def _draw_camera_name(self, painter: QPainter) -> None:
        """
        Draw camera name with background.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._title_font)
        
        # Calculate text size
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self._camera_name)
        text_height = metrics.height()
        
        # Draw semi-transparent background
        padding = 8
        bg_rect = QRect(8, 8, text_width + padding * 2, text_height + padding)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        # Draw text
        painter.setPen(QColor("#FFFFFF"))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        self._camera_name)
    
    def _draw_timestamp(self, painter: QPainter) -> None:
        """
        Draw timestamp.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._info_font)
        
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate text size
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(timestamp)
        text_height = metrics.height()
        
        # Position at top-right
        padding = 8
        x = self.width() - text_width - padding * 2 - 8
        y = 8
        
        # Draw semi-transparent background
        bg_rect = QRect(x, y, text_width + padding * 2, text_height + padding)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        # Draw text
        painter.setPen(QColor("#D4D4D4"))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        timestamp)
    
    def _draw_status_indicator(self, painter: QPainter) -> None:
        """
        Draw status text indicator.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._small_font)
        
        # Status text and color
        status_map = {
            StreamStatus.IDLE: ("IDLE", "#6A6A6A"),
            StreamStatus.CONNECTING: ("CONNECTING...", "#CE9178"),
            StreamStatus.CONNECTED: ("LIVE", "#4EC9B0"),
            StreamStatus.ERROR: ("ERROR", "#F48771"),
            StreamStatus.RECONNECTING: ("RECONNECTING...", "#CE9178"),
        }
        
        status_text, status_color = status_map.get(self._status, ("UNKNOWN", "#6A6A6A"))
        
        # Calculate position (below camera name)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(status_text)
        text_height = metrics.height()
        
        # Adjust Y based on whether camera name is shown
        y_offset = 40 if self._camera_name else 8
        
        # Draw background
        padding = 6
        bg_rect = QRect(8, y_offset, text_width + padding * 2, text_height + padding)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        # Draw text
        painter.setPen(QColor(status_color))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        status_text)
    
    def _draw_recording_indicator(self, painter: QPainter) -> None:
        """
        Draw recording indicator (red circle).
        
        Args:
            painter: QPainter instance
        """
        # Draw pulsing red circle
        circle_size = 12
        x = self.width() - circle_size - 16
        y = 50  # Below timestamp
        
        painter.setBrush(QColor("#F48771"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(x, y, circle_size, circle_size)
        
        # Draw "REC" text
        painter.setFont(self._small_font)
        painter.setPen(QColor("#F48771"))
        text_rect = QRect(x - 35, y - 2, 30, circle_size + 4)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "REC")
    
    def _draw_motion_indicator(self, painter: QPainter) -> None:
        """
        Draw motion detection indicator.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._small_font)
        
        # Draw at bottom-left, above FPS if shown
        y_offset = self.height() - 50 if self._show_fps else self.height() - 25
        
        text = "MOTION"
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()
        
        padding = 6
        bg_rect = QRect(8, y_offset - text_height - padding, 
                       text_width + padding * 2, text_height + padding)
        painter.fillRect(bg_rect, QColor(206, 145, 120, 180))  # Orange background
        
        painter.setPen(QColor("#FFFFFF"))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
    
    def _draw_fps_counter(self, painter: QPainter) -> None:
        """
        Draw FPS counter.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._small_font)
        
        fps_text = f"{self._fps:.1f} FPS"
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(fps_text)
        text_height = metrics.height()
        
        # Position at bottom-left
        padding = 6
        y = self.height() - text_height - padding - 8
        bg_rect = QRect(8, y, text_width + padding * 2, text_height + padding)
        
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        painter.setPen(QColor("#D4D4D4"))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        fps_text)
    
    def _draw_bitrate(self, painter: QPainter) -> None:
        """
        Draw bitrate indicator.
        
        Args:
            painter: QPainter instance
        """
        painter.setFont(self._small_font)
        
        bitrate_text = f"{self._bitrate:.1f} Mbps"
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(bitrate_text)
        text_height = metrics.height()
        
        # Position at bottom-right
        padding = 6
        x = self.width() - text_width - padding * 2 - 8
        y = self.height() - text_height - padding - 8
        bg_rect = QRect(x, y, text_width + padding * 2, text_height + padding)
        
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        painter.setPen(QColor("#D4D4D4"))
        text_rect = bg_rect.adjusted(padding, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                        bitrate_text)
