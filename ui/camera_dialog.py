"""
MediaMTX VMS Client v2.0 - Camera Dialog
Dialog for adding/editing cameras.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt

from models.camera import Camera
from utils.config import config
from utils.logger import logger


class CameraDialog(QDialog):
    """
    Dialog for adding or editing a camera.
    """
    
    def __init__(self, parent=None, camera: Camera = None):
        """
        Initialize camera dialog.
        
        Args:
            parent: Parent widget
            camera: Existing camera to edit (None for new camera)
        """
        super().__init__(parent)
        
        self._camera = camera
        self._is_edit_mode = camera is not None
        
        self.setWindowTitle("Edit Camera" if self._is_edit_mode else "Add Camera")
        self.setMinimumWidth(500)
        
        self._create_ui()
        
        if self._is_edit_mode:
            self._load_camera_data()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        
        # Basic Information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g., Front Door Camera")
        basic_layout.addRow("Name:", self._name_edit)
        
        self._group_combo = QComboBox()
        self._group_combo.setEditable(True)
        self._group_combo.addItems(config.get("groups", ["Default"]))
        basic_layout.addRow("Group:", self._group_combo)
        
        self._location_edit = QLineEdit()
        self._location_edit.setPlaceholderText("e.g., Entrance, Parking Lot")
        basic_layout.addRow("Location:", self._location_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Connection Settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self._type_combo = QComboBox()
        self._type_combo.addItems(["RTSP", "HLS"])
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        conn_layout.addRow("Type:", self._type_combo)
        
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("rtsp://192.168.1.100:554/stream")
        conn_layout.addRow("URL:", self._url_edit)
        
        # URL Templates
        template_label = QLabel("Quick URLs:")
        template_layout = QHBoxLayout()
        
        rtsp_template_btn = QPushButton("RTSP Template")
        rtsp_template_btn.clicked.connect(lambda: self._apply_template("rtsp"))
        template_layout.addWidget(rtsp_template_btn)
        
        mediamtx_template_btn = QPushButton("MediaMTX Template")
        mediamtx_template_btn.clicked.connect(lambda: self._apply_template("mediamtx"))
        template_layout.addWidget(mediamtx_template_btn)
        
        template_layout.addStretch()
        conn_layout.addRow(template_label, template_layout)
        
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("admin")
        conn_layout.addRow("Username:", self._username_edit)
        
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("password")
        conn_layout.addRow("Password:", self._password_edit)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Features
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout()
        
        self._motion_detection_check = QCheckBox("Enable Motion Detection")
        features_layout.addWidget(self._motion_detection_check)
        
        self._recording_check = QCheckBox("Enable Recording on Motion")
        features_layout.addWidget(self._recording_check)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        test_btn = QPushButton("🔧 Test Connection")
        test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(test_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save" if self._is_edit_mode else "Add")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._save_camera)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _on_type_changed(self, type_name: str) -> None:
        """
        Handle camera type change.
        
        Args:
            type_name: Camera type (RTSP or HLS)
        """
        if type_name == "RTSP":
            self._url_edit.setPlaceholderText("rtsp://192.168.1.100:554/stream")
        else:
            self._url_edit.setPlaceholderText("http://192.168.1.100:8000/stream/index.m3u8")
    
    def _apply_template(self, template_type: str) -> None:
        """
        Apply URL template.
        
        Args:
            template_type: Template type (rtsp, mediamtx, etc.)
        """
        if template_type == "rtsp":
            self._type_combo.setCurrentText("RTSP")
            self._url_edit.setText("rtsp://192.168.1.100:554/stream")
            self._username_edit.setText("admin")
        elif template_type == "mediamtx":
            self._type_combo.setCurrentText("RTSP")
            self._url_edit.setText("rtsp://localhost:8554/mystream")
            self._username_edit.setText("")
            self._password_edit.setText("")
    
    def _load_camera_data(self) -> None:
        """Load camera data into form."""
        if not self._camera:
            return
        
        self._name_edit.setText(self._camera.name)
        self._group_combo.setCurrentText(self._camera.group)
        self._location_edit.setText(self._camera.location)
        self._type_combo.setCurrentText(self._camera.type)
        self._url_edit.setText(self._camera.url)
        self._username_edit.setText(self._camera.username)
        self._password_edit.setText(self._camera.password)
        self._motion_detection_check.setChecked(self._camera.motion_detection)
        self._recording_check.setChecked(self._camera.recording_enabled)
    
    def _test_connection(self) -> None:
        """Test camera connection."""
        url = self._url_edit.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a camera URL.")
            return
        
        QMessageBox.information(self, "Test Connection", "Connection test will be implemented in next phase.")
    
    def _save_camera(self) -> None:
        """Save camera data."""
        # Get form data
        name = self._name_edit.text().strip()
        group = self._group_combo.currentText().strip()
        location = self._location_edit.text().strip()
        camera_type = self._type_combo.currentText()
        url = self._url_edit.text().strip()
        username = self._username_edit.text().strip()
        password = self._password_edit.text().strip()
        motion_detection = self._motion_detection_check.isChecked()
        recording_enabled = self._recording_check.isChecked()
        
        # Validate
        if not name:
            QMessageBox.warning(self, "Validation Error", "Camera name is required.")
            return
        
        if not url:
            QMessageBox.warning(self, "Validation Error", "Camera URL is required.")
            return
        
        # Create or update camera
        if self._is_edit_mode:
            self._camera.name = name
            self._camera.group = group
            self._camera.location = location
            self._camera.type = camera_type
            self._camera.url = url
            self._camera.username = username
            self._camera.password = password
            self._camera.motion_detection = motion_detection
            self._camera.recording_enabled = recording_enabled
        else:
            self._camera = Camera(
                name=name,
                group=group,
                location=location,
                type=camera_type,
                url=url,
                username=username,
                password=password,
                motion_detection=motion_detection,
                recording_enabled=recording_enabled
            )
        
        # Validate camera
        is_valid, error_msg = self._camera.validate()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return
        
        # Accept dialog
        self.accept()
    
    def get_camera(self) -> Camera:
        """
        Get camera data from dialog.
        
        Returns:
            Camera object
        """
        return self._camera
