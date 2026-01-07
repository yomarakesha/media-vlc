"""
MediaMTX VMS Client v2.0 - Motion Zone Editor Dialog
Visual editor for drawing and managing motion detection zones.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QListWidget, QListWidgetItem, QLabel, QLineEdit,
                              QCheckBox, QGroupBox, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QImage, QBrush
import cv2
import numpy as np

from core.motion_detector import DetectionZone
from models.camera import Camera
from utils.logger import logger


class ZoneCanvas(QLabel):
    """
    Canvas widget for drawing detection zones on video frame.
    """
    
    zone_created = pyqtSignal(DetectionZone)
    
    def __init__(self, parent=None):
        """Initialize zone canvas."""
        super().__init__(parent)
        
        self.setMinimumSize(640, 480)
        self.setStyleSheet("border: 2px solid #3E3E42; background-color: #1E1E1E;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # State
        self._frame : Optional[np.ndarray] = None
        self._zones: List[DetectionZone] = []
        self._drawing = False
        self._start_point: Optional[QPoint] = None
        self._current_rect: Optional[QRect] = None
        self._selected_zone_index = -1
    
    def set_frame(self, frame: np.ndarray) -> None:
        """
        Set background frame.
        
        Args:
            frame: Video frame (BGR)
        """
        self._frame = frame
        self._update_display()
    
    def set_zones(self, zones: List[DetectionZone]) -> None:
        """
        Set zones to display.
        
        Args:
            zones: List of DetectionZone objects
        """
        self._zones = zones
        self._update_display()
    
    def set_selected_zone(self, index: int) -> None:
        """
        Highlight selected zone.
        
        Args:
            index: Zone index (-1 for none)
        """
        self._selected_zone_index = index
        self._update_display()
    
    def mousePressEvent(self, event) -> None:
        """Start drawing zone."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._start_point = event.pos()
            self._current_rect = QRect(self._start_point, self._start_point)
    
    def mouseMoveEvent(self, event) -> None:
        """Update zone rectangle while drawing."""
        if self._drawing and self._start_point:
            self._current_rect = QRect(self._start_point, event.pos()).normalized()
            self._update_display()
    
    def mouseReleaseEvent(self, event) -> None:
        """Finish drawing zone."""
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            
            if self._current_rect and self._current_rect.width() > 20 and self._current_rect.height() > 20:
                # Convert to relative coordinates (0-1)
                canvas_rect = self.rect()
                zone = DetectionZone(
                    x=self._current_rect.x() / canvas_rect.width(),
                    y=self._current_rect.y() / canvas_rect.height(),
                    width=self._current_rect.width() / canvas_rect.width(),
                    height=self._current_rect.height() / canvas_rect.height(),
                    name=f"Zone {len(self._zones) + 1}"
                )
                
                self.zone_created.emit(zone)
            
            self._current_rect = None
            self._update_display()
    
    def _update_display(self) -> None:
        """Redraw canvas with frame and zones."""
        if self._frame is None:
            # No frame - just show placeholder
            self.setText("No camera preview available\nClick and drag to draw detection zones")
            return
        
        # Convert frame to QPixmap
        frame_rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # Scale to canvas size
        pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        
        # Draw zones on pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw existing zones
        for i, zone in enumerate(self._zones):
            if not zone.enabled:
                continue
            
            x, y, w, h = zone.get_absolute_rect(pixmap.width(), pixmap.height())
            
            # Color based on selection
            is_selected = (i == self._selected_zone_index)
            color = QColor(0, 255, 0) if not is_selected else QColor(255, 165, 0)
            
            # Draw rectangle
            pen = QPen(color, 3 if is_selected else 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 30)))
            painter.drawRect(x, y, w, h)
            
            # Draw zone name
            painter.drawText(x + 5, y + 20, zone.name)
        
        # Draw current drawing rectangle
        if self._current_rect:
            painter.setPen(QPen(QColor(255, 255, 0), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(255, 255, 0, 30)))
            painter.drawRect(self._current_rect)
        
        painter.end()
        
        self.setPixmap(pixmap)


class MotionZoneEditorDialog(QDialog):
    """
    Dialog for creating and managing motion detection zones.
    """
    
    def __init__(self, camera: Camera, current_frame: Optional[np.ndarray] = None, parent=None):
        """
        Initialize zone editor dialog.
        
        Args:
            camera: Camera to configure zones for
            current_frame: Optional current video frame for preview
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._camera = camera
        self._zones: List[DetectionZone] = []
        
        self.setWindowTitle(f"Motion Detection Zones - {camera.name}")
        self.setMinimumSize(900, 650)
        
        self._create_ui()
        
        if current_frame is not None:
            self._canvas.set_frame(current_frame)
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        
        # Main splitter (canvas | zone list)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Canvas area
        canvas_group = QGroupBox("Draw Detection Zones")
        canvas_layout = QVBoxLayout()
        
        instructions = QLabel(
            "Click and drag on the video preview to draw detection zones.\n"
            "Motion will only be detected within the marked zones."
        )
        instructions.setWordWrap(True)
        canvas_layout.addWidget(instructions)
        
        self._canvas = ZoneCanvas()
        self._canvas.zone_created.connect(self._on_zone_created)
        canvas_layout.addWidget(self._canvas)
        
        canvas_group.setLayout(canvas_layout)
        splitter.addWidget(canvas_group)
        
        # Zone list area
        zone_list_group = QGroupBox("Detection Zones")
        zone_list_layout = QVBoxLayout()
        
        self._zone_list = QListWidget()
        self._zone_list.currentRowChanged.connect(self._on_zone_selected)
        zone_list_layout.addWidget(self._zone_list)
        
        # Zone properties
        props_layout = QHBoxLayout()
        props_layout.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_name_changed)
        props_layout.addWidget(self._name_edit)
        
        self._enabled_check = QCheckBox("Enabled")
        self._enabled_check.setChecked(True)
        self._enabled_check.toggled.connect(self._on_enabled_changed)
        props_layout.addWidget(self._enabled_check)
        
        zone_list_layout.addLayout(props_layout)
        
        # Zone actions
        actions_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_zones)
        actions_layout.addWidget(clear_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected_zone)
        actions_layout.addWidget(remove_btn)
        
        zone_list_layout.addLayout(actions_layout)
        
        zone_list_group.setLayout(zone_list_layout)
        splitter.addWidget(zone_list_group)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Zones")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def set_zones(self, zones: List[DetectionZone]) -> None:
        """
        Load existing zones.
        
        Args:
            zones: List of DetectionZone objects
        """
        self._zones = zones.copy()
        self._refresh_zone_list()
        self._canvas.set_zones(self._zones)
    
    def get_zones(self) -> List[DetectionZone]:
        """Get configured zones."""
        return self._zones.copy()
    
    def _on_zone_created(self, zone: DetectionZone) -> None:
        """Handle new zone drawn on canvas."""
        self._zones.append(zone)
        self._refresh_zone_list()
        self._canvas.set_zones(self._zones)
        
        # Select new zone
        self._zone_list.setCurrentRow(len(self._zones) - 1)
    
    def _on_zone_selected(self, index: int) -> None:
        """Handle zone selection in list."""
        if 0 <= index < len(self._zones):
            zone = self._zones[index]
            self._name_edit.setText(zone.name)
            self._enabled_check.setChecked(zone.enabled)
            self._canvas.set_selected_zone(index)
        else:
            self._name_edit.clear()
            self._canvas.set_selected_zone(-1)
    
    def _on_name_changed(self, text: str) -> None:
        """Handle zone name change."""
        index = self._zone_list.currentRow()
        if 0 <= index < len(self._zones):
            self._zones[index].name = text
            self._refresh_zone_list()
            self._zone_list.setCurrentRow(index)
    
    def _on_enabled_changed(self, enabled: bool) -> None:
        """Handle zone enabled state change."""
        index = self._zone_list.currentRow()
        if 0 <= index < len(self._zones):
            self._zones[index].enabled = enabled
            self._canvas.set_zones(self._zones)
    
    def _remove_selected_zone(self) -> None:
        """Remove currently selected zone."""
        index = self._zone_list.currentRow()
        if 0 <= index < len(self._zones):
            self._zones.pop(index)
            self._refresh_zone_list()
            self._canvas.set_zones(self._zones)
    
    def _clear_zones(self) -> None:
        """Clear all zones."""
        if not self._zones:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All Zones",
            "Are you sure you want to remove all detection zones?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._zones.clear()
            self._refresh_zone_list()
            self._canvas.set_zones(self._zones)
    
    def _refresh_zone_list(self) -> None:
        """Refresh zone list widget."""
        current_row = self._zone_list.currentRow()
        self._zone_list.clear()
        
        for i, zone in enumerate(self._zones):
            status = "✓" if zone.enabled else "✗"
            item = QListWidgetItem(f"{status} {zone.name}")
            self._zone_list.addItem(item)
        
        if 0 <= current_row < len(self._zones):
            self._zone_list.setCurrentRow(current_row)
