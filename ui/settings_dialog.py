"""
MediaMTX VMS Client v2.0 - Settings Dialog
Application settings configuration dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSpinBox, QLineEdit, QPushButton, QGroupBox,
    QLabel, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt

from utils.config import config
from utils.logger import logger


class SettingsDialog(QDialog):
    """
    Dialog for application settings.
    """
    
    def __init__(self, parent=None):
        """Initialize settings dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        
        self._create_ui()
        self._load_settings()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        
        # Streaming Settings
        streaming_group = QGroupBox("Streaming Settings")
        streaming_layout = QFormLayout()
        
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(5, 30)
        self._fps_spin.setSuffix(" FPS")
        self._fps_spin.setToolTip("Maximum frames per second per camera")
        streaming_layout.addRow("FPS Limit:", self._fps_spin)
        
        self._reconnect_spin = QSpinBox()
        self._reconnect_spin.setRange(1, 60)
        self._reconnect_spin.setSuffix(" seconds")
        self._reconnect_spin.setToolTip("Interval between reconnection attempts")
        streaming_layout.addRow("Reconnect Interval:", self._reconnect_spin)
        
        streaming_group.setLayout(streaming_layout)
        layout.addWidget(streaming_group)
        
        # Recording Settings
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        # Recording path
        path_layout = QHBoxLayout()
        self._recording_path_edit = QLineEdit()
        self._recording_path_edit.setReadOnly(True)
        path_layout.addWidget(self._recording_path_edit)
        
        browse_rec_btn = QPushButton("Browse...")
        browse_rec_btn.clicked.connect(self._browse_recording_path)
        path_layout.addWidget(browse_rec_btn)
        
        recording_layout.addRow("Recording Path:", path_layout)
        
        # Screenshot path
        screenshot_layout = QHBoxLayout()
        self._screenshot_path_edit = QLineEdit()
        self._screenshot_path_edit.setReadOnly(True)
        screenshot_layout.addWidget(self._screenshot_path_edit)
        
        browse_screenshot_btn = QPushButton("Browse...")
        browse_screenshot_btn.clicked.connect(self._browse_screenshot_path)
        screenshot_layout.addWidget(browse_screenshot_btn)
        
        recording_layout.addRow("Screenshot Path:", screenshot_layout)
        
        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)
        
        # Motion Detection Settings
        motion_group = QGroupBox("Motion Detection")
        motion_layout = QFormLayout()
        
        self._motion_sensitivity_spin = QSpinBox()
        self._motion_sensitivity_spin.setRange(10, 100)
        self._motion_sensitivity_spin.setToolTip("Lower = more sensitive")
        motion_layout.addRow("Sensitivity:", self._motion_sensitivity_spin)
        
        motion_group.setLayout(motion_layout)
        layout.addWidget(motion_group)
        
        # Display Settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        
        self._show_overlay_check = QCheckBox("Show camera name and time overlay")
        display_layout.addWidget(self._show_overlay_check)
        
        self._show_timestamp_check = QCheckBox("Show timestamp on video")
        display_layout.addWidget(self._show_timestamp_check)
        
        self._auto_start_check = QCheckBox("Auto-start streams on camera assignment")
        display_layout.addWidget(self._auto_start_check)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        defaults_btn = QPushButton("Restore Defaults")
        defaults_btn.clicked.connect(self._restore_defaults)
        button_layout.addWidget(defaults_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _load_settings(self) -> None:
        """Load current settings."""
        self._fps_spin.setValue(config.get("settings.fps_limit", 15))
        self._reconnect_spin.setValue(config.get("settings.reconnect_interval", 5))
        self._recording_path_edit.setText(config.get("settings.recording_path", "./recordings"))
        self._screenshot_path_edit.setText(config.get("settings.screenshot_path", "./screenshots"))
        self._motion_sensitivity_spin.setValue(config.get("settings.motion_detection_sensitivity", 30))
        self._show_overlay_check.setChecked(config.get("settings.show_overlay", True))
        self._show_timestamp_check.setChecked(config.get("settings.show_timestamp", True))
        self._auto_start_check.setChecked(config.get("settings.auto_start_streams", True))
    
    def _browse_recording_path(self) -> None:
        """Browse for recording directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Recording Directory",
            self._recording_path_edit.text()
        )
        
        if directory:
            self._recording_path_edit.setText(directory)
    
    def _browse_screenshot_path(self) -> None:
        """Browse for screenshot directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Screenshot Directory",
            self._screenshot_path_edit.text()
        )
        
        if directory:
            self._screenshot_path_edit.setText(directory)
    
    def _restore_defaults(self) -> None:
        """Restore default settings."""
        self._fps_spin.setValue(15)
        self._reconnect_spin.setValue(5)
        self._recording_path_edit.setText("./recordings")
        self._screenshot_path_edit.setText("./screenshots")
        self._motion_sensitivity_spin.setValue(30)
        self._show_overlay_check.setChecked(True)
        self._show_timestamp_check.setChecked(True)
        self._auto_start_check.setChecked(True)
    
    def _save_settings(self) -> None:
        """Save settings to config."""
        config.set("settings.fps_limit", self._fps_spin.value(), save=False)
        config.set("settings.reconnect_interval", self._reconnect_spin.value(), save=False)
        config.set("settings.recording_path", self._recording_path_edit.text(), save=False)
        config.set("settings.screenshot_path", self._screenshot_path_edit.text(), save=False)
        config.set("settings.motion_detection_sensitivity", self._motion_sensitivity_spin.value(), save=False)
        config.set("settings.show_overlay", self._show_overlay_check.isChecked(), save=False)
        config.set("settings.show_timestamp", self._show_timestamp_check.isChecked(), save=False)
        config.set("settings.auto_start_streams", self._auto_start_check.isChecked(), save=False)
        
        # Save all at once
        config.save()
        
        logger.info("Settings saved")
        self.accept()
