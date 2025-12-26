"""
MediaMTX VMS Client v2.0 - Resource Tree Widget
Tree view for organizing cameras and NVRs.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from core.camera_manager import camera_manager
from core.nvr_manager import nvr_manager
from models.camera import Camera
from models.nvr import NVR
from utils.logger import logger


class DraggableTreeWidget(QTreeWidget):
    """Tree widget with custom drag support."""
    
    def mimeTypes(self):
        """Supported mime types."""
        return ["application/x-mediamtx-camera"]
    
    def startDrag(self, supportedActions):
        """
        Handle drag start.
        Pack camera ID into mime data.
        """
        item = self.currentItem()
        if not item:
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "camera":
            # Only allow dragging cameras
            return
            
        # Pack ID and type
        item_type = data.get("type")
        if item_type == "camera":
            camera = data.get("camera")
            id_str = camera.id
        elif item_type == "zero_channel":
            nvr = data.get("nvr")
            id_str = f"zero_{nvr.id}"
        else:
            return
            
        from PyQt6.QtCore import QMimeData, QByteArray, QDataStream, QIODevice
        
        # Create mime data
        mime_data = QMimeData()
        
        # Pack ID
        byte_data = QByteArray()
        stream = QDataStream(byte_data, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeString(id_str.encode('utf-8'))
        
        mime_data.setData("application/x-mediamtx-camera", byte_data)
        
        # Create drag object
        from PyQt6.QtGui import QDrag
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Exec drag
        drag.exec(Qt.DropAction.CopyAction)


class ResourceTree(QWidget):
    """
    Tree widget for displaying and managing cameras and NVRs.
    Supports drag & drop to grid cells.
    """
    
    # Signals
    camera_selected = pyqtSignal(Camera)  # Emitted when camera clicked
    camera_double_clicked = pyqtSignal(Camera)  # Emitted on double-click
    camera_drag_started = pyqtSignal(Camera)  # For drag & drop
    camera_deleted = pyqtSignal(str)  # Emitted when camera deleted
    nvr_double_clicked = pyqtSignal(NVR)  # Emitted on NVR double-click
    
    def __init__(self, parent=None):
        """Initialize resource tree."""
        super().__init__(parent)
        
        self._create_ui()
        self._load_data()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_btn)
        
        expand_btn = QPushButton("➕")
        expand_btn.setToolTip("Expand All")
        expand_btn.setFixedWidth(30)
        expand_btn.clicked.connect(lambda: self._tree.expandAll())
        toolbar.addWidget(expand_btn)
        
        collapse_btn = QPushButton("➖")
        collapse_btn.setToolTip("Collapse All")
        collapse_btn.setFixedWidth(30)
        collapse_btn.clicked.connect(lambda: self._tree.collapseAll())
        toolbar.addWidget(collapse_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Tree widget
        self._tree = DraggableTreeWidget()
        self._tree.setHeaderLabel("Resources")
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        
        layout.addWidget(self._tree)
# ...existing code...
    
    def _load_data(self) -> None:
        """Load cameras and NVRs into tree."""
        self._tree.clear()
        
        # Groups
        groups = camera_manager.get_groups()
        cameras = camera_manager.get_all_cameras()
        nvrs = nvr_manager.get_all_nvrs()
        
        # Create group items
        group_items = {}
        for group in groups:
            group_item = QTreeWidgetItem(self._tree, [f"📁 {group}"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "name": group})
            group_item.setExpanded(True)
            group_items[group] = group_item
        
        # Add cameras to groups
        for camera in cameras:
            group = camera.group or "Default"
            if group not in group_items:
                # Create missing group
                group_item = QTreeWidgetItem(self._tree, [f"📁 {group}"])
                group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "name": group})
                group_item.setExpanded(True)
                group_items[group] = group_item
            
            camera_item = QTreeWidgetItem(group_items[group], [f"📷 {camera.name}"])
            camera_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "camera", "camera": camera})
            camera_item.setToolTip(0, f"URL: {camera.url}")
        
        # Add NVRs
        if nvrs:
            nvr_root = QTreeWidgetItem(self._tree, ["📹 NVRs"])
            nvr_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "nvr_root"})
            nvr_root.setExpanded(True)
            
            for nvr in nvrs:
                nvr_item = QTreeWidgetItem(nvr_root, [f"📹 {nvr.name}"])
                nvr_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "nvr", "nvr": nvr})
                nvr_item.setToolTip(0, f"Host: {nvr.host}:{nvr.port}")
                
                # Add Zero Channel if enabled
                if getattr(nvr, 'zero_stream_enabled', False):
                    zero_item = QTreeWidgetItem(nvr_item, ["📺 Zero Channel (Preview)"])
                    zero_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "zero_channel", "nvr": nvr})
                    zero_item.setToolTip(0, f"NVR Preview Stream: {nvr.zero_stream_url}")
                    zero_item.setForeground(0, Qt.GlobalColor.blue)

                # Add NVR cameras
                for camera_id in nvr.cameras:
                    camera = camera_manager.get_camera(camera_id)
                    if camera:
                        cam_item = QTreeWidgetItem(nvr_item, [f"📷 {camera.name}"])
                        cam_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "camera", "camera": camera})
        
        logger.debug(f"Resource tree loaded: {len(cameras)} cameras, {len(nvrs)} NVRs")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handle item click.
        
        Args:
            item: Clicked item
            column: Column index
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "camera":
            camera = data.get("camera")
            if camera:
                self.camera_selected.emit(camera)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handle item double-click.
        
        Args:
            item: Double-clicked item
            column: Column index
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "camera":
            camera = data.get("camera")
            if camera:
                self.camera_double_clicked.emit(camera)
        elif data and data.get("type") == "zero_channel":
            nvr = data.get("nvr")
            if nvr:
                self.nvr_double_clicked.emit(nvr)
        elif data and data.get("type") == "nvr":
            nvr = data.get("nvr")
            if nvr:
                self.nvr_double_clicked.emit(nvr)
    
    def _show_context_menu(self, position) -> None:
        """
        Show context menu for tree item.
        
        Args:
            position: Menu position
        """
        item = self._tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        item_type = data.get("type")
        
        if item_type == "camera":
            camera = data.get("camera")
            
            view_action = QAction("👁 View Camera", self)
            view_action.triggered.connect(lambda: self.camera_double_clicked.emit(camera))
            menu.addAction(view_action)
            
            menu.addSeparator()
            
            edit_action = QAction("✏️ Edit Camera", self)
            edit_action.triggered.connect(lambda: self._edit_camera(camera))
            menu.addAction(edit_action)
            
            delete_action = QAction("🗑️ Delete Camera", self)
            delete_action.triggered.connect(lambda: self._delete_camera(camera))
            menu.addAction(delete_action)
        
        elif item_type == "zero_channel":
            nvr = data.get("nvr")
            view_action = QAction("👁 View Zero Channel", self)
            view_action.triggered.connect(lambda: self.nvr_double_clicked.emit(nvr))
            menu.addAction(view_action)
            
        elif item_type == "group":
            group_name = data.get("name")
            
            add_action = QAction("➕ Add Camera to Group", self)
            add_action.triggered.connect(lambda: self._add_camera_to_group(group_name))
            menu.addAction(add_action)
            
            if group_name not in ["Default", "Indoor", "Outdoor", "Entrance"]:
                delete_action = QAction("🗑️ Delete Group", self)
                delete_action.triggered.connect(lambda: self._delete_group(group_name))
                menu.addAction(delete_action)
        
        elif item_type == "nvr":
            nvr = data.get("nvr")
            
            if getattr(nvr, 'zero_stream_enabled', False):
                view_zero_action = QAction("👁 View Zero Stream (Preview All)", self)
                view_zero_action.triggered.connect(lambda: self.nvr_double_clicked.emit(nvr))
                menu.addAction(view_zero_action)
                menu.addSeparator()

            edit_nvr_action = QAction("✏️ Edit NVR", self)
            edit_nvr_action.triggered.connect(lambda: self._edit_nvr(nvr))
            menu.addAction(edit_nvr_action)
            
            delete_action = QAction("🗑️ Delete NVR", self)
            delete_action.triggered.connect(lambda: self._delete_nvr(nvr))
            menu.addAction(delete_action)
        
        menu.exec(self._tree.mapToGlobal(position))
    
    def _edit_camera(self, camera: Camera) -> None:
        """
        Edit camera.
        
        Args:
            camera: Camera to edit
        """
        from ui.camera_dialog import CameraDialog
        
        dialog = CameraDialog(self, camera)
        if dialog.exec():
            updated_camera = dialog.get_camera()
            camera_manager.update_camera(updated_camera)
            self._load_data()
    
    def _delete_camera(self, camera: Camera) -> None:
        """
        Delete camera.
        
        Args:
            camera: Camera to delete
        """
        reply = QMessageBox.question(
            self,
            "Delete Camera",
            f"Are you sure you want to delete '{camera.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Emit deletion signal first to allow cleanup (e.g. stop streams)
            logger.debug(f"[HANG_DEBUG] Emitting camera_deleted for {camera.id}")
            self.camera_deleted.emit(camera.id)
            logger.debug(f"[HANG_DEBUG] camera_deleted signal emitted")
            
            logger.debug(f"[HANG_DEBUG] Removing from camera_manager")
            camera_manager.remove_camera(camera.id)
            logger.debug(f"[HANG_DEBUG] Removed from camera_manager")
            
            self._load_data()
            logger.debug(f"[HANG_DEBUG] Tree reloaded")
    
    def _add_camera_to_group(self, group_name: str) -> None:
        """
        Add new camera to group.
        
        Args:
            group_name: Target group
        """
        from ui.camera_dialog import CameraDialog
        
        dialog = CameraDialog(self)
        if dialog.exec():
            camera = dialog.get_camera()
            camera.group = group_name
            camera_manager.add_camera(camera)
            self._load_data()
    
    def _delete_group(self, group_name: str) -> None:
        """
        Delete group (moves cameras to Default).
        
        Args:
            group_name: Group to delete
        """
        cameras_in_group = camera_manager.get_cameras_by_group(group_name)
        
        if cameras_in_group:
            reply = QMessageBox.question(
                self,
                "Delete Group",
                f"Group '{group_name}' contains {len(cameras_in_group)} cameras.\n"
                "They will be moved to 'Default' group.\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Move cameras to Default
            for camera in cameras_in_group:
                camera.group = "Default"
                camera_manager.update_camera(camera)
        
        # Remove group from config
        from utils.config import config
        groups = config.get("groups", [])
        if group_name in groups:
            groups.remove(group_name)
            config.set("groups", groups)
        
        self._load_data()
        
    def _edit_nvr(self, nvr: NVR) -> None:
        """Edit NVR."""
        from ui.onvif_nvr_dialog import ONVIFNVRDialog
        dialog = ONVIFNVRDialog(self, nvr)
        if dialog.exec():
            self._load_data()
    
    def _delete_nvr(self, nvr: NVR) -> None:
        """
        Delete NVR.
        
        Args:
            nvr: NVR to delete
        """
        reply = QMessageBox.question(
            self,
            "Delete NVR",
            f"Are you sure you want to delete '{nvr.name}'?\n"
            f"This will also remove {len(nvr.cameras)} associated cameras.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            nvr_manager.remove_nvr(nvr.id, remove_cameras=True)
            self._load_data()
    
    def refresh(self) -> None:
        """Refresh tree data."""
        self._load_data()
