"""
MediaMTX VMS Client v2.0 - Main Window
Primary application window with toolbar, tab widget, and dock panels.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QTabWidget, QWidget,
    QMessageBox, QFileDialog, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence

from ui.grid_widget import GridWidget
from utils.logger import logger
from utils.config import config


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Features:
    - Toolbar with actions
    - Tab widget (Live View, Playback, E-Map)
    - Dock widgets (Resource Tree, PTZ Panel, Event Log)
    - Status bar
    """
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        self.setWindowTitle("MediaMTX VMS Client v2.0")
        self.resize(1280, 800)
        
        # Load Theme
        from PyQt6.QtWidgets import QApplication
        from ui.theme_manager import ThemeManager
        self._theme_manager = ThemeManager(QApplication.instance())
        
        # UI Setup
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_dock_widgets()
        self._create_status_bar()
        
        # Start Resource Monitor
        from utils.resource_monitor import resource_monitor
        resource_monitor.usage_updated.connect(self._update_resource_stats)
        resource_monitor.start()
        
        logger.info("MainWindow initialized")
        
    def closeEvent(self, event):
        """Handle window close."""
        from utils.resource_monitor import resource_monitor
        resource_monitor.stop()
        
        self._grid_widget.stop_all_streams()
        logger.info("Application closing")
        event.accept()
    
    def _create_central_widget(self) -> None:
        """Create central widget (tabs)."""
        self._tab_widget = QTabWidget()
        self.setCentralWidget(self._tab_widget)
        self._create_tabs()
        
    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View Menu
        view_menu = menu_bar.addMenu("&View")
        
        # Layouts
        layout_menu = view_menu.addMenu("Grid Layout")
        for layout_name in ["1x1", "2x2", "3x3", "4x4", "6x6", "8x8"]:
            action = QAction(layout_name, self)
            action.triggered.connect(lambda checked, n=layout_name: self._change_layout(n))
            layout_menu.addAction(action)

        view_menu.addSeparator()
        
        # Theme Toggle
        theme_action = QAction("Toggle Theme (Dark/Light)", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)
        
        # Tools Menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        discovery_action = QAction("Device Discovery...", self)
        discovery_action.triggered.connect(self._discover_devices)
        tools_menu.addAction(discovery_action)
        
        add_nvr_action = QAction("Add ONVIF NVR...", self)
        add_nvr_action.triggered.connect(self._add_nvr)
        tools_menu.addAction(add_nvr_action)
        
        tools_menu.addSeparator()
        
        # Motion Detection
        motion_menu = tools_menu.addMenu("Motion Detection")
        
        config_zones_action = QAction("Configure Zones...", self)
        config_zones_action.setShortcut("Ctrl+M")
        config_zones_action.triggered.connect(self._configure_motion_zones)
        motion_menu.addAction(config_zones_action)
        
        # Recording
        recording_menu = tools_menu.addMenu("Recording")
        
        schedules_action = QAction("Recording Schedules...", self)
        schedules_action.setShortcut("Ctrl+R")
        schedules_action.triggered.connect(self._configure_recording_schedules)
        recording_menu.addAction(schedules_action)
        
        # Layout Manager
        tools_menu.addSeparator()
        
        layout_mgr_action = QAction("Layout Manager...", self)
        layout_mgr_action.setShortcut("Ctrl+L")
        layout_mgr_action.triggered.connect(self._open_layout_manager)
        tools_menu.addAction(layout_mgr_action)
        
        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """Create main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(toolbar.iconSize() * 1.2)
        
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        # Add Camera
        add_camera_action = QAction("📷 Add Camera", self)
        add_camera_action.setShortcut(QKeySequence("Ctrl+N"))
        add_camera_action.triggered.connect(self._add_camera)
        toolbar.addAction(add_camera_action)
        
        # Add NVR
        add_nvr_action = QAction("📹 Add NVR", self)
        add_nvr_action.triggered.connect(self._add_nvr)
        toolbar.addAction(add_nvr_action)
        
        toolbar.addSeparator()
        
        # Discover Devices
        discover_action = QAction("🔍 Search Devices", self)
        discover_action.triggered.connect(self._discover_devices)
        toolbar.addAction(discover_action)
        
        toolbar.addSeparator()
        
        # Layout selector
        toolbar.addWidget(self._create_layout_selector())
        
        toolbar.addSeparator()
        
        # Start/Stop All
        start_all_action = QAction("▶ Start All", self)
        start_all_action.triggered.connect(self._start_all_streams)
        toolbar.addAction(start_all_action)
        
        stop_all_action = QAction("⏹ Stop All", self)
        stop_all_action.triggered.connect(self._stop_all_streams)
        toolbar.addAction(stop_all_action)
        
        toolbar.addSeparator()
        
        # Screenshot
        screenshot_action = QAction("📸 Screenshot", self)
        screenshot_action.setShortcut(QKeySequence("Ctrl+S"))
        screenshot_action.triggered.connect(self._take_screenshot)
        toolbar.addAction(screenshot_action)
        
        toolbar.addSeparator()
        
        # Phase 2 Features
        layout_mgr_action = QAction("💾 Layouts", self)
        layout_mgr_action.setToolTip("Layout Manager")
        layout_mgr_action.triggered.connect(self._open_layout_manager)
        toolbar.addAction(layout_mgr_action)
        
        toolbar.addSeparator()
        
        # Settings
        settings_action = QAction("⚙ Settings", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)
        
        # About
        about_action = QAction("ℹ About", self)
        about_action.triggered.connect(self._show_about)
        toolbar.addAction(about_action)
        
        self._toolbar = toolbar
    
    def _create_layout_selector(self) -> QWidget:
        """Create layout selector widget for toolbar."""
        container = QWidget()
        from PyQt6.QtWidgets import QHBoxLayout, QLabel
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 0, 10, 0)
        
        label = QLabel("Layout:")
        self._layout_combo = QComboBox()
        self._layout_combo.addItems(list(GridWidget.LAYOUTS.keys()))
        self._layout_combo.setCurrentText(config.get("layout.current", "2x2"))
        self._layout_combo.currentTextChanged.connect(self._change_layout)
        
        layout.addWidget(label)
        layout.addWidget(self._layout_combo)
        
        return container
    
    def _create_tabs(self) -> None:
        """Create tab widgets."""
        # Live View tab
        self._grid_widget = GridWidget()
        self._tab_widget.addTab(self._grid_widget, "📹 Live View")
        
        # Playback tab
        from ui.playback_widget import PlaybackWidget
        self._playback_widget = PlaybackWidget()
        self._tab_widget.addTab(self._playback_widget, "⏯ Playback")
        
        # E-Map tab
        from ui.emap_widget import EMapWidget
        self._emap_widget = EMapWidget()
        self._tab_widget.addTab(self._emap_widget, "🗺 E-Map")

    def _create_status_bar(self) -> None:
        """Create status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Permanent widgets
        self._cpu_label = QLabel("CPU: -%")
        self._ram_label = QLabel("RAM: -%")
        self._cpu_label.setStyleSheet("padding: 0 10px;")
        self._ram_label.setStyleSheet("padding: 0 10px;")
        
        status_bar.addPermanentWidget(self._cpu_label)
        status_bar.addPermanentWidget(self._ram_label)
        
        # Status update timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start(1000)
    
    def _toggle_theme(self):
        new_theme = self._theme_manager.toggle_theme()
        self.statusBar().showMessage(f"Switched to {new_theme} theme", 3000)

    def _update_resource_stats(self, cpu, ram_pct, ram_used, ram_total):
        self._cpu_label.setText(f"CPU: {cpu:.1f}%")
        self._ram_label.setText(f"RAM: {ram_used:.1f}/{ram_total:.1f} GB ({ram_pct:.1f}%)")
        
        # Color warning if high
        if cpu > 80:
             self._cpu_label.setStyleSheet("color: #FF5555; padding: 0 10px; font-weight: bold;")
        else:
             self._cpu_label.setStyleSheet("padding: 0 10px;")

    def _update_status_bar(self) -> None:
        """Update status bar information."""
        from core.camera_manager import camera_manager
        from core.nvr_manager import nvr_manager
        
        total_cameras = camera_manager.count()
        total_nvrs = nvr_manager.count()
        active_streams = self._grid_widget.get_active_stream_count()
        current_layout = self._grid_widget.get_current_layout()
        
        status_text = f"Cameras: {total_cameras} | NVRs: {total_nvrs} | Active Streams: {active_streams} | Layout: {current_layout}"
        self.statusBar().showMessage(status_text)
    
    def _create_dock_widgets(self) -> None:
        """Create dock widgets."""
        from PyQt6.QtWidgets import QDockWidget
        from ui.resource_tree import ResourceTree
        from ui.ptz_widget import PTZWidget
        from ui.event_log import EventLog
        
        # Resource Tree (left)
        resource_dock = QDockWidget("Resource Tree", self)
        resource_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self._resource_tree = ResourceTree()
        self._resource_tree.camera_double_clicked.connect(self._on_camera_selected)
        self._resource_tree.nvr_double_clicked.connect(self._on_nvr_selected)
        self._resource_tree.camera_deleted.connect(self._on_camera_deleted)
        resource_dock.setWidget(self._resource_tree)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, resource_dock)
        self._resource_dock = resource_dock
        
        # PTZ Panel (right)
        ptz_dock = QDockWidget("PTZ Control", self)
        ptz_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self._ptz_widget = PTZWidget()
        ptz_dock.setWidget(self._ptz_widget)
        
        # Connect signal now that both exist
        self._resource_tree.camera_selected.connect(self._ptz_widget.set_camera)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ptz_dock)
        self._ptz_dock = ptz_dock
        
        # Event Log (bottom)
        event_dock = QDockWidget("Event Log", self)
        event_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        
        self._event_log = EventLog()
        self._event_log.add_info("Application started")
        event_dock.setWidget(self._event_log)
        
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, event_dock)
        self._event_dock = event_dock

    def _add_camera(self) -> None:
        from ui.camera_dialog import CameraDialog
        
        dialog = CameraDialog(self)
        if dialog.exec():
            camera = dialog.get_camera()
            if camera:
                from core.camera_manager import camera_manager
                if camera_manager.add_camera(camera):
                    logger.info(f"Camera added: {camera.name}")
                    self._resource_tree.refresh()
                    self._event_log.add_info(f"Camera '{camera.name}' added")
                    QMessageBox.information(self, "Success", f"Camera '{camera.name}' added successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to add camera. Check logs for details.")
    
    def _add_nvr(self) -> None:
        """Open add NVR dialog."""
        from ui.onvif_nvr_dialog import ONVIFNVRDialog
        
        dialog = ONVIFNVRDialog(self)
        if dialog.exec():
            nvr = dialog.get_nvr()
            if nvr:
                self._resource_tree.refresh()
                self._event_log.add_info(f"NVR '{nvr.name}' added with {len(nvr.cameras)} cameras")
    
    def _discover_devices(self) -> None:
        """Open device discovery dialog."""
        from ui.discovery_dialog import DiscoveryDialog
        
        dialog = DiscoveryDialog(self)
        dialog.exec()
        
        # Refresh resource tree after discovery
        self._resource_tree.refresh()
    
    def _on_camera_selected(self, camera) -> None:
        """Handle camera selection from resource tree."""
        # Find first empty cell and assign camera
        for row in range(self._grid_widget._rows):
            for col in range(self._grid_widget._cols):
                if self._grid_widget.get_camera_at_cell(row, col) is None:
                    self._grid_widget.assign_camera_to_cell(camera, row, col)
                    self._event_log.add_info(f"Camera '{camera.name}' assigned to cell ({row},{col})", camera.name)
                    return
        
        QMessageBox.warning(self, "Grid Full", "No empty cells available. Change layout or remove a camera.")
        
    def _on_nvr_selected(self, nvr) -> None:
        """Handle NVR selection from resource tree."""
        if not getattr(nvr, 'zero_stream_enabled', False):
            return
            
        if not nvr.zero_stream_url:
            QMessageBox.warning(self, "Zero Stream", f"Zero stream is enabled for '{nvr.name}' but no URL is provided.")
            return

        # Create a virtual camera for the zero stream
        from models.camera import Camera
        vcamera = Camera(
            id=f"zero_{nvr.id}",
            name=f"{nvr.name} (Preview)",
            url=nvr.zero_stream_url,
            username=nvr.username,
            password=nvr.password,
            nvr_id=nvr.id
        )
        
        # Try to find an empty cell or just use the first one if empty
        self._on_camera_selected(vcamera)
    
    def _on_camera_deleted(self, camera_id: str) -> None:
        """
        Handle camera deletion.
        
        Args:
            camera_id: Deleted camera ID
        """
        logger.debug(f"[HANG_DEBUG] _on_camera_deleted start for {camera_id}")
        
        # Remove from Grid
        try:
            self._grid_widget.remove_camera_by_id(camera_id)
            logger.debug(f"[HANG_DEBUG] grid_widget removed {camera_id}")
        except Exception as e:
            logger.error(f"[HANG_DEBUG] grid_widget removal failed: {e}")

        # Remove from E-Map
        try:
            self._emap_widget.remove_camera_by_id(camera_id)
            logger.debug(f"[HANG_DEBUG] emap_widget removed {camera_id}")
        except Exception as e:
            logger.error(f"[HANG_DEBUG] emap_widget removal failed: {e}")
        
        # Clear PTZ if needed
        try:
            self._ptz_widget.set_camera(None)
            logger.debug(f"[HANG_DEBUG] ptz_widget cleared")
        except Exception as e:
            logger.error(f"[HANG_DEBUG] ptz_widget clear failed: {e}")
        
        self._event_log.add_info("Camera removed from grid and map", camera_id)
        logger.debug(f"[HANG_DEBUG] _on_camera_deleted done")
    
    def _change_layout(self, layout_name: str) -> None:
        """
        Change grid layout.
        
        Args:
            layout_name: Layout name (e.g., "2x2")
        """
        self._grid_widget.set_layout(layout_name)
        logger.info(f"Layout changed to {layout_name}")
    
    def _start_all_streams(self) -> None:
        """Start all camera streams."""
        self._grid_widget.start_all_streams()
        logger.info("Starting all streams")
    
    def _stop_all_streams(self) -> None:
        """Stop all camera streams."""
        self._grid_widget.stop_all_streams()
        logger.info("Stopping all streams")
    
    def _take_screenshot(self) -> None:
        """Take screenshot of all visible cameras."""
        QMessageBox.information(self, "Screenshot", "Screenshot functionality will capture current view.")
    
    def _open_settings(self) -> None:
        """Open settings dialog."""
        from ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def _configure_motion_zones(self) -> None:
        """Open motion zone configuration dialog."""
        # TODO: Get current selected camera from grid or resource tree
        QMessageBox.information(
            self,
            "Motion Zones",
            "Select a camera from the grid or resource tree first, then right-click and choose 'Configure Motion Zones'."
        )
    
    def _configure_recording_schedules(self) -> None:
        """Open recording schedules dialog."""
        from ui.recording_schedule_dialog import RecordingScheduleDialog
        
        dialog = RecordingScheduleDialog(self)
        # TODO: Load existing schedules from config
        if dialog.exec():
            schedules = dialog.get_schedules()
            # TODO: Save schedules to config
            self._event_log.add_info(f"Recording schedules updated ({len(schedules)} schedule(s))")
            logger.info(f"Recording schedules configured: {len(schedules)}")
    
    def _open_layout_manager(self) -> None:
        """Open layout manager dialog."""
        QMessageBox.information(
            self,
            "Layout Manager",
            "Layout Manager allows you to create, save, and load custom grid layouts.\n\n" +
            "Feature coming soon!"
        )
        # TODO: Implement LayoutManagerDialog
        # from ui.layout_manager_dialog import LayoutManagerDialog
        # dialog = LayoutManagerDialog(self)
        # dialog.exec()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        about_text = """
        <h2>MediaMTX VMS Client v2.1</h2>
        <p>Professional Video Management System for Windows</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Multi-camera grid (up to 100 cameras)</li>
            <li>RTSP & HLS streaming support</li>
            <li>ONVIF NVR integration</li>
            <li>Advanced motion detection (MOG2)</li>
            <li>Pre-buffer recording & schedules</li>
            <li>Custom layout manager</li>
            <li>SQLite database support</li>
        </ul>
        <p><b>Version:</b> 2.1.0</p>
        <p><b>Build Date:</b> 2026-01-07</p>
        <p>© 2025-2026 MediaMTX VMS Client Project</p>
        """
        
        QMessageBox.about(self, "About MediaMTX VMS Client", about_text)
    

