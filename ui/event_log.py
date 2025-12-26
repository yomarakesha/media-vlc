"""
MediaMTX VMS Client v2.0 - Event Log Widget
Table widget for displaying system events.
"""

from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QLabel,
    QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from utils.logger import logger


class EventLog(QWidget):
    """
    Event log widget for displaying system events.
    Shows timestamps, cameras, event types, and descriptions.
    """
    
    # Event types
    EVENT_INFO = "Info"
    EVENT_WARNING = "Warning"
    EVENT_ERROR = "Error"
    EVENT_MOTION = "Motion"
    EVENT_RECORDING = "Recording"
    EVENT_CONNECTION = "Connection"
    
    # Colors for event types
    EVENT_COLORS = {
        EVENT_INFO: "#4EC9B0",      # Green
        EVENT_WARNING: "#CE9178",    # Orange
        EVENT_ERROR: "#F48771",      # Red
        EVENT_MOTION: "#DCDCAA",     # Yellow
        EVENT_RECORDING: "#F48771",  # Red
        EVENT_CONNECTION: "#569CD6", # Blue
    }
    
    def __init__(self, parent=None):
        """Initialize event log."""
        super().__init__(parent)
        
        self._max_events = 1000
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Filter
        filter_label = QLabel("Filter:")
        toolbar.addWidget(filter_label)
        
        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            "All Events",
            self.EVENT_INFO,
            self.EVENT_WARNING,
            self.EVENT_ERROR,
            self.EVENT_MOTION,
            self.EVENT_RECORDING,
            self.EVENT_CONNECTION
        ])
        self._filter_combo.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self._filter_combo)
        
        toolbar.addStretch()
        
        # Export button
        export_btn = QPushButton("📤 Export")
        export_btn.clicked.connect(self._export_log)
        toolbar.addWidget(export_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self._clear_log)
        toolbar.addWidget(clear_btn)
        
        layout.addLayout(toolbar)
        
        # Event table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Time", "Camera", "Event", "Description"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 100)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        
        layout.addWidget(self._table)
    
    def add_event(self, event_type: str, description: str, 
                  camera_name: str = "", timestamp: datetime = None) -> None:
        """
        Add event to the log.
        
        Args:
            event_type: Type of event
            description: Event description
            camera_name: Associated camera name (optional)
            timestamp: Event timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Remove oldest events if at max
        while self._table.rowCount() >= self._max_events:
            self._table.removeRow(self._table.rowCount() - 1)
        
        # Insert at top
        self._table.insertRow(0)
        
        # Time
        time_item = QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        self._table.setItem(0, 0, time_item)
        
        # Camera
        camera_item = QTableWidgetItem(camera_name)
        self._table.setItem(0, 1, camera_item)
        
        # Event type
        event_item = QTableWidgetItem(event_type)
        color = self.EVENT_COLORS.get(event_type, "#D4D4D4")
        event_item.setForeground(QColor(color))
        self._table.setItem(0, 2, event_item)
        
        # Description
        desc_item = QTableWidgetItem(description)
        self._table.setItem(0, 3, desc_item)
        
        # Store event type for filtering
        time_item.setData(Qt.ItemDataRole.UserRole, event_type)
        
        # Apply current filter
        self._apply_filter(self._filter_combo.currentText())
        
        logger.debug(f"Event logged: [{event_type}] {camera_name}: {description}")
    
    def add_info(self, description: str, camera_name: str = "") -> None:
        """Add info event."""
        self.add_event(self.EVENT_INFO, description, camera_name)
    
    def add_warning(self, description: str, camera_name: str = "") -> None:
        """Add warning event."""
        self.add_event(self.EVENT_WARNING, description, camera_name)
    
    def add_error(self, description: str, camera_name: str = "") -> None:
        """Add error event."""
        self.add_event(self.EVENT_ERROR, description, camera_name)
    
    def add_motion(self, camera_name: str, started: bool = True) -> None:
        """Add motion detection event."""
        desc = "Motion detected" if started else "Motion ended"
        self.add_event(self.EVENT_MOTION, desc, camera_name)
    
    def add_recording(self, camera_name: str, started: bool = True, filename: str = "") -> None:
        """Add recording event."""
        if started:
            desc = f"Recording started: {filename}" if filename else "Recording started"
        else:
            desc = "Recording stopped"
        self.add_event(self.EVENT_RECORDING, desc, camera_name)
    
    def add_connection(self, camera_name: str, connected: bool = True, error: str = "") -> None:
        """Add connection event."""
        if connected:
            desc = "Connected"
        else:
            desc = f"Disconnected: {error}" if error else "Disconnected"
        self.add_event(self.EVENT_CONNECTION, desc, camera_name)
    
    def _apply_filter(self, filter_text: str) -> None:
        """
        Apply event type filter.
        
        Args:
            filter_text: Filter text
        """
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item:
                event_type = item.data(Qt.ItemDataRole.UserRole)
                visible = (filter_text == "All Events" or event_type == filter_text)
                self._table.setRowHidden(row, not visible)
    
    def _export_log(self) -> None:
        """Export log to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Event Log",
            f"event_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Header
                f.write("Timestamp,Camera,Event Type,Description\n")
                
                # Data
                for row in range(self._table.rowCount()):
                    if not self._table.isRowHidden(row):
                        time = self._table.item(row, 0).text() if self._table.item(row, 0) else ""
                        camera = self._table.item(row, 1).text() if self._table.item(row, 1) else ""
                        event = self._table.item(row, 2).text() if self._table.item(row, 2) else ""
                        desc = self._table.item(row, 3).text() if self._table.item(row, 3) else ""
                        
                        # Escape commas
                        desc = desc.replace(',', ';')
                        
                        f.write(f"{time},{camera},{event},{desc}\n")
            
            QMessageBox.information(self, "Export Complete", f"Event log exported to:\n{filename}")
            logger.info(f"Event log exported to {filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export log:\n{e}")
            logger.error(f"Failed to export event log: {e}")
    
    def _clear_log(self) -> None:
        """Clear all events."""
        reply = QMessageBox.question(
            self,
            "Clear Log",
            "Are you sure you want to clear the event log?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._table.setRowCount(0)
            logger.info("Event log cleared")
