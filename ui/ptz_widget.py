"""
MediaMTX VMS Client v2.0 - PTZ Control Widget
Pan-Tilt-Zoom control panel for PTZ cameras.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QSlider, QLabel, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.ptz_control import PTZController
from models.camera import Camera
from utils.logger import logger
from concurrent.futures import ThreadPoolExecutor

class PTZWidget(QWidget):
    """
    PTZ (Pan-Tilt-Zoom) control panel.
    Provides directional controls, zoom, focus, and presets.
    """
    
    # Signal for connection result (thread-safe)
    connect_finished = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        """Initialize PTZ widget."""
        super().__init__(parent)
        
        self._current_speed = 0.5
        self._controller = PTZController()
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        
        # Connect signals
        self.connect_finished.connect(self._on_connect_result)
        
        self._create_ui()
        self.set_enabled(False)
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Directional Controls
        direction_group = QGroupBox("Direction")
        direction_layout = QGridLayout()
        direction_layout.setSpacing(4)
        
        # Direction buttons (3x3 grid)
        # Text, Row, Col, Command
        buttons = [
            ("↖", 0, 0, "up_left"),
            ("↑", 0, 1, "up"),
            ("↗", 0, 2, "up_right"),
            ("←", 1, 0, "left"),
            ("⌂", 1, 1, "home"),
            ("→", 1, 2, "right"),
            ("↙", 2, 0, "down_left"),
            ("↓", 2, 1, "down"),
            ("↘", 2, 2, "down_right"),
        ]
        
        for text, row, col, command in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(50, 50)
            btn.setStyleSheet("font-size: 16pt;")
            
            if command == "home":
                # Home usually calls goto preset 1 or specific command
                btn.clicked.connect(self._goto_home)
            else:
                btn.pressed.connect(lambda c=command: self._send_command(c))
                btn.released.connect(self._stop_move)
            
            direction_layout.addWidget(btn, row, col)
        
        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)
        
        # Speed control
        speed_group = QGroupBox("Speed")
        speed_layout = QHBoxLayout()
        
        speed_label = QLabel("Slow")
        speed_layout.addWidget(speed_label)
        
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(1, 10)
        self._speed_slider.setValue(5)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self._speed_slider)
        
        speed_fast_label = QLabel("Fast")
        speed_layout.addWidget(speed_fast_label)
        
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)
        
        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QHBoxLayout()
        
        zoom_out_btn = QPushButton("➖")
        zoom_out_btn.setFixedWidth(60)
        zoom_out_btn.pressed.connect(lambda: self._send_command("zoom_out"))
        zoom_out_btn.released.connect(self._stop_move)
        zoom_layout.addWidget(zoom_out_btn)
        
        zoom_layout.addStretch()
        
        zoom_in_btn = QPushButton("➕")
        zoom_in_btn.setFixedWidth(60)
        zoom_in_btn.pressed.connect(lambda: self._send_command("zoom_in"))
        zoom_in_btn.released.connect(self._stop_move)
        zoom_layout.addWidget(zoom_in_btn)
        
        zoom_group.setLayout(zoom_layout)
        layout.addWidget(zoom_group)
        
        # Presets
        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout()
        
        preset_row1 = QHBoxLayout()
        self._preset_combo = QComboBox()
        self._preset_combo.addItems([f"Preset {i}" for i in range(1, 9)])
        preset_row1.addWidget(self._preset_combo)
        preset_layout.addLayout(preset_row1)
        
        preset_row2 = QHBoxLayout()
        
        goto_btn = QPushButton("Go To")
        goto_btn.clicked.connect(self._goto_preset)
        preset_row2.addWidget(goto_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_preset)
        preset_row2.addWidget(save_btn)
        
        preset_layout.addLayout(preset_row2)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Status
        self._status_label = QLabel("Select a camera to connect")
        self._status_label.setStyleSheet("color: #6A6A6A; font-style: italic;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)
        
        layout.addStretch()
        
    def set_camera(self, camera: Camera) -> None:
        """Set active camera for PTZ control."""
        if not camera:
            self.set_enabled(False)
            self._status_label.setText("No camera selected")
            return
            
        # Optional: Check if camera supports PTZ (e.g. type check)
        
        self.set_enabled(False)
        self._status_label.setText(f"Connecting to {camera.name}...")
        
        # Connect asynchronously
        self._thread_pool.submit(self._connect_task, camera)

    def _connect_task(self, camera: Camera):
        """Background connection task."""
        try:
            success = self._controller.connect(camera)
            self.connect_finished.emit(success, camera.name)
        except Exception as e:
            logger.error(f"Error in PTZ connection task: {e}")
            self.connect_finished.emit(False, camera.name)

    def _on_connect_result(self, success: bool, name: str):
        """Slot for connection result."""
        if success:
            self.set_enabled(True)
            self._status_label.setText(f"Connected to {name}")
        else:
            self.set_enabled(False)
            self._status_label.setText(f"PTZ unavailable for {name}")

    def _on_speed_changed(self, value: int) -> None:
        self._current_speed = value / 10.0
    
    def _send_command(self, command: str) -> None:
        """Map command to vectors and execute."""
        s = self._current_speed
        
        pan = 0.0
        tilt = 0.0
        zoom = 0.0
        
        if command == "up":
            tilt = s
        elif command == "down":
            tilt = -s
        elif command == "left":
            pan = -s
        elif command == "right":
            pan = s
        elif command == "up_left":
            pan = -s; tilt = s
        elif command == "up_right":
            pan = s; tilt = s
        elif command == "down_left":
            pan = -s; tilt = -s
        elif command == "down_right":
            pan = s; tilt = -s
        elif command == "zoom_in":
            zoom = s
        elif command == "zoom_out":
            zoom = -s
            
        self._thread_pool.submit(self._controller.move_continuous, pan, tilt, zoom)
        self._status_label.setText(f"Moving: {command}")

    def _stop_move(self) -> None:
        self._thread_pool.submit(self._controller.stop)
        self._status_label.setText("Ready")
        
    def _goto_home(self) -> None:
        self._goto_preset() # Mapped to preset 1 for now or implement Home in controller
        
    def _goto_preset(self) -> None:
        idx = self._preset_combo.currentIndex() + 1
        self._thread_pool.submit(self._controller.goto_preset, idx)
        self._status_label.setText(f"Going to P{idx}")

    def _save_preset(self) -> None:
        idx = self._preset_combo.currentIndex() + 1
        self._thread_pool.submit(self._controller.save_preset, idx)
        self._status_label.setText(f"Saved P{idx}")

    def set_enabled(self, enabled: bool) -> None:
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)
        self._speed_slider.setEnabled(enabled)
        self._preset_combo.setEnabled(enabled)
        if not enabled and self._status_label.text() == "Connected":
             self._status_label.setText("Disconnected")

