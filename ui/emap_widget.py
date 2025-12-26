"""
MediaMTX VMS Client v2.0 - E-Map Widget
Interactive facility map with camera placement.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
    QGraphicsItem, QToolBar, QFileDialog, QMessageBox,
    QGraphicsSceneDragDropEvent, QMenu
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QBrush, QColor, QPen, QPainter, QPixmap, QAction, 
    QFont
)

from utils.config import config
from utils.logger import logger
from core.camera_manager import camera_manager
from models.camera import Camera

class CameraMapItem(QGraphicsItem):
    """Graphics item representing a camera on the map."""
    
    def __init__(self, camera_id: str):
        super().__init__()
        self.camera_id = camera_id
        self.camera = camera_manager.get_camera(camera_id)
        
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10) # Ensure on top of map
        
        # Tooltip
        if self.camera:
            self.setToolTip(f"{self.camera.name}\n{self.camera.url}")
        else:
            self.setToolTip(f"Unknown Camera ({camera_id})")
            
    def boundingRect(self) -> QRectF:
        return QRectF(-15, -15, 30, 50) # Include text area below
        
    def paint(self, painter: QPainter, option, widget) -> None:
        # Draw camera icon (simplified CCTV shape)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color based on selection
        color = QColor("#007ACC") if self.isSelected() else QColor("#444")
        if not self.camera:
            color = QColor("#CC0000") # Error color
            
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.setBrush(QBrush(color))
        
        # Body
        painter.drawRoundedRect(-12, -8, 24, 16, 4, 4)
        # Lens
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawEllipse(-5, -5, 10, 10)
        
        # Text
        if self.camera:
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Arial", 8))
            name = self.camera.name
            # Truncate if long
            if len(name) > 10:
                name = name[:9] + "..."
            painter.drawText(QRectF(-25, 10, 50, 20), Qt.AlignmentFlag.AlignCenter, name)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
           # Notify scene of movement if needed
           scene = self.scene()
           if scene and hasattr(scene, "notify_change"):
               scene.notify_change()
        return super().itemChange(change, value)
        
    def mouseDoubleClickEvent(self, event):
        # Open stream
        if self.camera:
            from ui.fullscreen_dialog import FullscreenVideoDialog
            # Ensure we have a parent widget context
            views = self.scene().views()
            if views:
                # Find the main window or use view
                dialog = FullscreenVideoDialog(self.camera, views[0])
                dialog.exec()
        super().mouseDoubleClickEvent(event)
        
    def contextMenuEvent(self, event):
        menu = QMenu()
        remove_action = menu.addAction("Remove from Map")
        info_action = menu.addAction("Camera Info")
        
        selected_action = menu.exec(event.screenPos())
        
        if selected_action == remove_action:
            scene = self.scene()
            if scene and hasattr(scene, "remove_camera_item"):
                 scene.remove_camera_item(self)
        elif selected_action == info_action:
             if self.camera:
                 QMessageBox.information(None, "Info", str(self.camera))

class EMapScene(QGraphicsScene):
    """Custom scene handling dropping."""
    
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor("#1E1E1E")))
        self.bg_item = None
        
    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent):
        if event.mimeData().hasFormat("application/x-mediamtx-camera"):
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent):
        if event.mimeData().hasFormat("application/x-mediamtx-camera"):
            event.acceptProposedAction()
            
    def dropEvent(self, event: QGraphicsSceneDragDropEvent):
        if event.mimeData().hasFormat("application/x-mediamtx-camera"):
            byte_data = event.mimeData().data("application/x-mediamtx-camera")
            from PyQt6.QtCore import QDataStream, QIODevice
            stream = QDataStream(byte_data, QIODevice.OpenModeFlag.ReadOnly)
            camera_id_bytes = stream.readString()
            if camera_id_bytes:
                camera_id = camera_id_bytes.decode('utf-8')
                self.add_camera_item(camera_id, event.scenePos())
                event.acceptProposedAction()
                self.notify_change()
            
    def add_camera_item(self, camera_id: str, pos: QPointF):
        item = CameraMapItem(camera_id)
        item.setPos(pos)
        self.addItem(item)
        logger.info(f"Added camera {camera_id} to map at {pos.x()},{pos.y()}")
        
    def remove_camera_item(self, item: CameraMapItem):
        self.removeItem(item)
        self.notify_change()
        
    def remove_camera_by_id(self, camera_id: str):
        items_to_remove = [item for item in self.items() if isinstance(item, CameraMapItem) and item.camera_id == camera_id]
        for item in items_to_remove:
            self.removeItem(item)
        if items_to_remove:
            self.notify_change()

class EMapWidget(QWidget):
    """
    Electronic Map widget.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_bg_path = ""
        self._init_ui()
        self._load_config()
        
    def remove_camera_by_id(self, camera_id: str):
        """Remove camera from map by ID."""
        self._scene.remove_camera_by_id(camera_id)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Toolbar
        toolbar = QToolBar()
        load_action = QAction("🖼 Load Map Image", self)
        load_action.triggered.connect(self._load_map_image)
        toolbar.addAction(load_action)
        
        clear_action = QAction("🗑 Clear Cameras", self)
        clear_action.triggered.connect(self._clear_cameras)
        toolbar.addAction(clear_action)
        
        layout.addWidget(toolbar)
        
        # View
        self._scene = EMapScene()
        self._scene.config_changed.connect(self._save_config)
        
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Allow panning
        layout.addWidget(self._view)
        
    def _load_map_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self._set_background(path)
            self._save_config()
            
    def _set_background(self, path: str):
        if os.path.exists(path):
            pixmap = QPixmap(path)
            
            # Remove old BG
            if self._scene.bg_item:
                self._scene.removeItem(self._scene.bg_item)
                
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            bg = QGraphicsPixmapItem(pixmap)
            bg.setZValue(0)
            self._scene.addItem(bg)
            self._scene.bg_item = bg
            self._scene.setSceneRect(QRectF(pixmap.rect()))
            
            self._current_bg_path = path
        else:
            logger.error(f"Map image not found: {path}")

    def _clear_cameras(self):
        # Remove only CameraItems
        items_to_remove = [item for item in self._scene.items() if isinstance(item, CameraMapItem)]
        for item in items_to_remove:
            self._scene.removeItem(item)
        self._save_config()
        
    def _save_config(self):
        # Save Items
        items_data = []
        for item in self._scene.items():
            if isinstance(item, CameraMapItem):
                pos = item.pos()
                items_data.append({
                    "id": item.camera_id,
                    "x": pos.x(),
                    "y": pos.y()
                })
        
        config.set("emap.cameras", items_data)
        if self._current_bg_path:
            config.set("emap.background", self._current_bg_path)
        config.save()
        logger.debug("E-Map config saved")

    def _load_config(self):
        # Load BG
        bg_path = config.get("emap.background", "")
        if bg_path:
            self._set_background(bg_path)
            
        # Load Items
        items_data = config.get("emap.cameras", [])
        for data in items_data:
            self._scene.add_camera_item(data["id"], QPointF(data["x"], data["y"]))
