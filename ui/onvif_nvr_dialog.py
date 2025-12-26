"""
MediaMTX VMS Client v2.0 - ONVIF NVR Dialog
Dialog for adding NVR devices via ONVIF protocol.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QLabel, QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import requests

from models.nvr import NVR
from models.camera import Camera
from core.nvr_manager import nvr_manager
from core.camera_manager import camera_manager
from utils.logger import logger


class ONVIFProbeThread(QThread):
    """Thread for probing ONVIF device."""
    
    cameras_found = pyqtSignal(list)  # List of camera info dicts
    error = pyqtSignal(str)
    finished_probe = pyqtSignal()
    
    finished_probe = pyqtSignal()
    
    def __init__(self, host: str, port: int, username: str, password: str, device_type: str = "ONVIF"):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.device_type = device_type
    
    def run(self):
        """Probe device for cameras."""
        try:
            cameras = []
            
            if self.device_type == "MediaMTX":
                # MediaMTX API Probe
                logger.info(f"Probing MediaMTX API at {self.host}:{self.port}")
                api_url = f"http://{self.host}:{self.port}/v3/paths/list"
                
                # Basic Auth if provided
                auth = None
                if self.username:
                    auth = (self.username, self.password)
                
                response = requests.get(api_url, auth=auth, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                # Parse paths
                items = data.get("items", [])
                for i, item in enumerate(items):
                    name = item.get("name")
                    if name:
                        # Construct RTSP URL (assuming 8554 for now, need field later or reuse logic)
                        # We don't know the RTSP port for sure from API, but usually 8554.
                        # NVR object has rtsp_port, we can use that if we had access, but for now defaults.
                        rtsp_url = f"rtsp://{self.host}:8554/{name}" 
                        if self.username: # Add auth to URL if used
                             rtsp_url = f"rtsp://{self.username}:{self.password}@{self.host}:8554/{name}"

                        cameras.append({
                            'name': f"{name}",
                            'token': name, # Use name as token
                            'url': rtsp_url,
                            'encoding': 'Auto' 
                        })

            else:
                # ONVIF Probe
                # Try to connect using onvif-zeep
                from onvif import ONVIFCamera
                
                logger.info(f"Probing ONVIF device at {self.host}:{self.port}")
                
                # Create ONVIF camera client
                cam = ONVIFCamera(
                    self.host,
                    self.port,
                    self.username,
                    self.password
                )
                
                # Get media service
                media_service = cam.create_media_service()
                
                # Get profiles
                profiles = media_service.GetProfiles()
                
                for i, profile in enumerate(profiles):
                    try:
                        # Get stream URI for this profile
                        stream_setup = {
                            'Stream': 'RTP-Unicast',
                            'Transport': {'Protocol': 'RTSP'}
                        }
                        uri = media_service.GetStreamUri({
                            'StreamSetup': stream_setup,
                            'ProfileToken': profile.token
                        })
                        
                        cameras.append({
                            'name': f"Channel {i + 1} - {profile.Name}",
                            'token': profile.token,
                            'url': uri.Uri,
                            'encoding': getattr(profile.VideoEncoderConfiguration, 'Encoding', 'Unknown') if hasattr(profile, 'VideoEncoderConfiguration') else 'Unknown'
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to get stream for profile {profile.Name}: {e}")
            
            self.cameras_found.emit(cameras)
            
        except ImportError:
            self.error.emit("ONVIF library not installed. Run: pip install onvif-zeep")
        except requests.exceptions.RequestException as e:
             self.error.emit(f"MediaMTX API Error: {e}")
        except Exception as e:
            logger.error(f"ONVIF probe failed: {e}")
            self.error.emit(str(e))
        finally:
            self.finished_probe.emit()


class ONVIFNVRDialog(QDialog):
    """
    Dialog for adding NVR devices via ONVIF.
    """
    
    def __init__(self, parent=None, nvr: NVR = None):
        """
        Initialize ONVIF NVR dialog.
        
        Args:
            parent: Parent widget
            nvr: Existing NVR to edit (None for new NVR)
        """
        super().__init__(parent)
        
        self._nvr = nvr
        self._is_edit_mode = nvr is not None
        self._probe_thread = None
        self._discovered_cameras = []
        
        self.setWindowTitle("Edit Device" if self._is_edit_mode else "Add Device (NVR / MediaMTX)")
        self.setMinimumSize(600, 500)
        
        self._create_ui()
        
        if self._is_edit_mode:
            self._load_nvr_data()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        
        # Connection Settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g., Office NVR")
        conn_layout.addRow("Name:", self._name_edit)
        
        self._type_combo = QComboBox()
        self._type_combo.addItems(["ONVIF", "MediaMTX"])
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        conn_layout.addRow("Type:", self._type_combo)
        
        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("192.168.1.100")
        conn_layout.addRow("Host/IP:", self._host_edit)
        
        self._port_label = QLabel("Port:")
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(80)
        conn_layout.addRow(self._port_label, self._port_spin)
        
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("admin")
        conn_layout.addRow("Username:", self._username_edit)
        
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addRow("Password:", self._password_edit)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Probe button
        probe_layout = QHBoxLayout()
        
        self._probe_btn = QPushButton("🔍 Probe Device")
        self._probe_btn.clicked.connect(self._probe_device)
        probe_layout.addWidget(self._probe_btn)
        
        probe_layout.addStretch()
        layout.addLayout(probe_layout)
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self._progress_bar)
        
        # Cameras table
        cameras_group = QGroupBox("Discovered Cameras")
        cameras_layout = QVBoxLayout()
        
        self._cameras_table = QTableWidget()
        self._cameras_table.setColumnCount(4)
        self._cameras_table.setHorizontalHeaderLabels(["Select", "Name", "URL", "Encoding"])
        self._cameras_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._cameras_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._cameras_table.setColumnWidth(0, 50)
        self._cameras_table.setColumnWidth(1, 150)
        self._cameras_table.setColumnWidth(3, 80)
        
        cameras_layout.addWidget(self._cameras_table)
        cameras_group.setLayout(cameras_layout)
        layout.addWidget(cameras_group)
        
        # Proxy settings
        proxy_group = QGroupBox("Proxy Settings (Optional)")
        proxy_layout = QFormLayout()
        
        self._use_proxy = QCheckBox("Use MediaMTX as proxy")
        self._use_proxy.toggled.connect(self._on_proxy_toggled)
        proxy_layout.addRow(self._use_proxy)
        
        self._proxy_url = QLineEdit()
        self._proxy_url.setPlaceholderText("rtsp://localhost:8554")
        self._proxy_url.setEnabled(False)
        proxy_layout.addRow("Proxy URL:", self._proxy_url)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        # Zero Channel settings
        zero_group = QGroupBox("Zero Channel (NVR Preview)")
        zero_layout = QFormLayout()
        
        self._zero_stream_enabled = QCheckBox("Enable Zero Channel preview")
        self._zero_stream_enabled.setToolTip("Use a combined preview stream if supported by the NVR")
        self._zero_stream_enabled.toggled.connect(self._on_zero_toggled)
        zero_layout.addRow(self._zero_stream_enabled)
        
        self._zero_stream_url = QLineEdit()
        self._zero_stream_url.setPlaceholderText("rtsp://admin:password@ip:554/Streaming/Channels/001")
        self._zero_stream_url.setEnabled(False)
        zero_layout.addRow("Zero Stream URL:", self._zero_stream_url)
        
        zero_group.setLayout(zero_layout)
        layout.addWidget(zero_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self._save_btn = QPushButton("Save" if self._is_edit_mode else "Add")
        self._save_btn.setProperty("primary", True)
        self._save_btn.clicked.connect(self._save_nvr)
        self._save_btn.setEnabled(False)
        button_layout.addWidget(self._save_btn)
        
        layout.addLayout(button_layout)

    def _on_type_changed(self, type_name: str) -> None:
        """Handle type change."""
        if type_name == "MediaMTX":
            self._port_label.setText("API Port:")
            self._port_spin.setValue(9997)
            self._username_edit.setPlaceholderText("Optional")
        else:
            self._port_label.setText("ONVIF Port:")
            self._port_spin.setValue(80)
            self._username_edit.setPlaceholderText("admin")
    
    def _on_proxy_toggled(self, checked: bool) -> None:
        """Handle proxy checkbox toggle."""
        self._proxy_url.setEnabled(checked)
    
    def _on_zero_toggled(self, checked: bool) -> None:
        """Handle zero channel checkbox toggle."""
        self._zero_stream_url.setEnabled(checked)
        if checked and not self._zero_stream_url.text():
            # Try to suggest a URL if host is present
            host = self._host_edit.text()
            user = self._username_edit.text()
            if host:
                self._zero_stream_url.setText(f"rtsp://{user or 'admin'}:@{host}:554/Streaming/Channels/001")
    
    def _probe_device(self) -> None:
        """Probe ONVIF device for cameras."""
        host = self._host_edit.text().strip()
        port = self._port_spin.value()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        device_type = self._type_combo.currentText()
        
        if not host:
            QMessageBox.warning(self, "Error", "Please enter host/IP address.")
            return
        
        # Clear previous results
        self._cameras_table.setRowCount(0)
        self._discovered_cameras = []
        
        # Show progress
        self._progress_bar.setVisible(True)
        self._probe_btn.setEnabled(False)
        
        # Start probe thread
        self._probe_thread = ONVIFProbeThread(host, port, username, password, device_type)
        self._probe_thread.cameras_found.connect(self._on_cameras_found)
        self._probe_thread.error.connect(self._on_probe_error)
        self._probe_thread.finished_probe.connect(self._on_probe_finished)
        self._probe_thread.start()
    
    def _on_cameras_found(self, cameras: list) -> None:
        """
        Handle discovered cameras.
        
        Args:
            cameras: List of camera info dicts
        """
        self._discovered_cameras = cameras
        
        for cam in cameras:
            row = self._cameras_table.rowCount()
            self._cameras_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self._cameras_table.setCellWidget(row, 0, checkbox)
            
            # Data
            self._cameras_table.setItem(row, 1, QTableWidgetItem(cam['name']))
            self._cameras_table.setItem(row, 2, QTableWidgetItem(cam['url']))
            self._cameras_table.setItem(row, 3, QTableWidgetItem(cam.get('encoding', 'Unknown')))
        
        self._save_btn.setEnabled(len(cameras) > 0)
        
        QMessageBox.information(self, "Probe Complete", f"Found {len(cameras)} camera(s).")
    
    def _on_probe_error(self, error_msg: str) -> None:
        """
        Handle probe error.
        
        Args:
            error_msg: Error message
        """
        QMessageBox.critical(self, "Probe Error", f"Failed to probe device:\n{error_msg}")
    
    def _on_probe_finished(self) -> None:
        """Handle probe completion."""
        self._progress_bar.setVisible(False)
        self._probe_btn.setEnabled(True)
    
    def _load_nvr_data(self) -> None:
        """Load NVR data into form."""
        if not self._nvr:
            return
        
        self._name_edit.setText(self._nvr.name)
        self._host_edit.setText(self._nvr.host)
        self._port_spin.setValue(self._nvr.port)
        self._username_edit.setText(self._nvr.username)
        self._password_edit.setText(self._nvr.password)
        self._use_proxy.setChecked(self._nvr.use_proxy)
        self._proxy_url.setText(self._nvr.proxy_url)
        self._zero_stream_enabled.setChecked(getattr(self._nvr, 'zero_stream_enabled', False))
        self._zero_stream_url.setText(getattr(self._nvr, 'zero_stream_url', ""))
    
    def _save_nvr(self) -> None:
        """Save NVR and selected cameras."""
        name = self._name_edit.text().strip()
        host = self._host_edit.text().strip()
        port = self._port_spin.value()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        use_proxy = self._use_proxy.isChecked()
        proxy_url = self._proxy_url.text().strip()
        zero_enabled = self._zero_stream_enabled.isChecked()
        zero_url = self._zero_stream_url.text().strip()
        
        # Validate
        if not name:
            QMessageBox.warning(self, "Validation Error", "NVR name is required.")
            return
        
        if not host:
            QMessageBox.warning(self, "Validation Error", "Host/IP is required.")
            return
        
        # Create NVR
        if self._is_edit_mode:
            self._nvr.name = name
            self._nvr.host = host
            self._nvr.port = port
            self._nvr.username = username
            self._nvr.password = password
            self._nvr.use_proxy = use_proxy
            self._nvr.proxy_url = proxy_url
            self._nvr.zero_stream_enabled = zero_enabled
            self._nvr.zero_stream_url = zero_url
        else:
            self._nvr = NVR(
                name=name,
                host=host,
                port=port,
                username=username,
                password=password,
                use_proxy=use_proxy,
                proxy_url=proxy_url,
                zero_stream_enabled=zero_enabled,
                zero_stream_url=zero_url
            )
        
        # Add selected cameras
        camera_ids = []
        for row in range(self._cameras_table.rowCount()):
            checkbox = self._cameras_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                cam_data = self._discovered_cameras[row]
                
                # Create camera
                camera = Camera(
                    name=cam_data['name'],
                    url=cam_data['url'],
                    username=username,
                    password=password,

                    type=self._type_combo.currentText(),
                    nvr_id=self._nvr.id,
                    channel=row + 1
                )
                
                if camera_manager.add_camera(camera):
                    camera_ids.append(camera.id)
        
        # Update NVR with camera IDs
        self._nvr.cameras = camera_ids
        
        # Save NVR
        if self._is_edit_mode:
            nvr_manager.update_nvr(self._nvr)
        else:
            nvr_manager.add_nvr(self._nvr)
        
        logger.info(f"NVR saved: {name} with {len(camera_ids)} cameras")
        self.accept()
    
    def get_nvr(self) -> Optional[NVR]:
        """
        Get NVR from dialog.
        
        Returns:
            NVR object or None
        """
        return self._nvr
    
    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self._probe_thread and self._probe_thread.isRunning():
            self._probe_thread.terminate()
            self._probe_thread.wait()
        
        super().closeEvent(event)
