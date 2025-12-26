"""
MediaMTX VMS Client v2.0 - Grid Widget
Multi-camera grid layout widget with drag & drop support.
"""

from typing import Dict, Optional, List, Tuple
from PyQt6.QtWidgets import QWidget, QGridLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal

from ui.video_widget import VideoWidget
from models.camera import Camera
from utils.logger import logger
from utils.config import config


class GridWidget(QWidget):
    """
    Grid layout widget for displaying multiple camera feeds.
    Supports 8 layouts: 1x1, 2x2, 3x3, 4x4, 5x5, 6x6, 8x8, 10x10
    """
    
    # Signals
    camera_assigned = pyqtSignal(str, int, int)  # camera_id, row, col
    
    # Layout configurations (rows, cols)
    LAYOUTS = {
        "1x1": (1, 1),
        "2x2": (2, 2),
        "3x3": (3, 3),
        "4x4": (4, 4),
        "5x5": (5, 5),
        "6x6": (6, 6),
        "8x8": (8, 8),
        "10x10": (10, 10),
    }
    
    def __init__(self, parent=None):
        """Initialize grid widget."""
        super().__init__(parent)
        
        # Grid layout
        self._layout = QGridLayout(self)
        self._layout.setSpacing(4)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        
        # Video widgets
        self._video_widgets: Dict[Tuple[int, int], VideoWidget] = {}
        
        # Current layout
        self._current_layout = "2x2"
        self._rows, self._cols = self.LAYOUTS[self._current_layout]
        
        # Camera assignments
        self._assignments: Dict[Tuple[int, int], str] = {}  # (row, col) -> camera_id
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Create initial grid
        self._create_grid()
        
        # Load assignments from config
        self._load_assignments()
    
    def _create_grid(self) -> None:
        """Create grid of video widgets."""
        # Clear existing widgets
        self._clear_grid()
        
        # Create new grid
        for row in range(self._rows):
            for col in range(self._cols):
                video_widget = VideoWidget(self)
                video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                
                # Connect signals
                video_widget.fullscreen_requested.connect(self._handle_fullscreen)
                video_widget.screenshot_requested.connect(self._handle_screenshot)
                video_widget.camera_dropped.connect(lambda cid, r=row, c=col: self._handle_camera_drop(cid, r, c))
                
                self._layout.addWidget(video_widget, row, col)
                self._video_widgets[(row, col)] = video_widget
        
        logger.info(f"Created {self._rows}x{self._cols} grid with {len(self._video_widgets)} cells")
    
    def _clear_grid(self) -> None:
        """Clear all widgets from grid."""
        # Stop all streams asynchronously (to prevent UI freeze)
        for widget in self._video_widgets.values():
            widget.stop_stream_async()
        
        # Remove from layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                # Note: widget.deleteLater() will happen, but we already signaled threads to stop.
                # Threads will clean themselves up via finished->deleteLater
                item.widget().deleteLater()
        
        self._video_widgets.clear()
    
    def set_layout(self, layout_name: str) -> None:
        """
        Change grid layout.
        
        Args:
            layout_name: Layout name (e.g., "2x2", "4x4")
        """
        if layout_name not in self.LAYOUTS:
            logger.error(f"Invalid layout: {layout_name}")
            return
        
        if layout_name == self._current_layout:
            return
        
        logger.info(f"Changing layout from {self._current_layout} to {layout_name}")
        
        # Save current assignments
        self._save_assignments()
        
        # Update layout
        self._current_layout = layout_name
        self._rows, self._cols = self.LAYOUTS[layout_name]
        
        # Recreate grid
        self._create_grid()
        
        # Restore assignments
        self._load_assignments()
        
        # Save to config
        config.set("layout.current", layout_name)
    
    def get_current_layout(self) -> str:
        """Get current layout name."""
        return self._current_layout
    
    def assign_camera_to_cell(self, camera: Camera, row: int, col: int) -> bool:
        """
        Assign camera to specific grid cell.
        
        Args:
            camera: Camera object
            row: Grid row
            col: Grid column
            
        Returns:
            True if successful, False otherwise
        """
        if (row, col) not in self._video_widgets:
            logger.error(f"Invalid cell: ({row}, {col})")
            return False
        
        # Get video widget
        widget = self._video_widgets[(row, col)]
        
        # Assign camera
        widget.set_camera(camera)
        
        # Update assignments
        self._assignments[(row, col)] = camera.id
        self._save_assignments()
        
        # Emit signal
        self.camera_assigned.emit(camera.id, row, col)
        
        logger.info(f"Assigned camera '{camera.name}' to cell ({row}, {col})")
        return True
    
    def remove_camera_from_cell(self, row: int, col: int) -> bool:
        """
        Remove camera from grid cell.
        
        Args:
            row: Grid row
            col: Grid column
            
        Returns:
            True if successful, False otherwise
        """
        if (row, col) not in self._video_widgets:
            return False
        
        # Get video widget
        widget = self._video_widgets[(row, col)]
        
        # Clear camera
        widget.set_camera(None)
        
        # Update assignments
        if (row, col) in self._assignments:
            del self._assignments[(row, col)]
            self._save_assignments()
        
        return True

    def remove_camera_by_id(self, camera_id: str) -> None:
        """
        Remove camera by ID from all cells (non-blocking).
        
        Args:
            camera_id: Camera ID to remove
        """
        cells_to_remove = []
        for (row, col), assigned_id in self._assignments.items():
            if assigned_id == camera_id:
                cells_to_remove.append((row, col))
        
        for row, col in cells_to_remove:
            if (row, col) in self._video_widgets:
                widget = self._video_widgets[(row, col)]
                widget.detach_camera()
            
            # Remove from assignments
            if (row, col) in self._assignments:
                del self._assignments[(row, col)]
        
        if cells_to_remove:
            self._save_assignments()
            logger.info(f"Removed camera {camera_id} from {len(cells_to_remove)} cells")

    def get_camera_at_cell(self, row: int, col: int) -> Optional[Camera]:
        """
        Get camera assigned to cell.
        
        Args:
            row: Grid row
            col: Grid column
            
        Returns:
            Camera object or None
        """
        if (row, col) in self._video_widgets:
            return self._video_widgets[(row, col)].get_camera()
        return None
    
    def start_all_streams(self) -> None:
        """Start all video streams."""
        logger.info("Starting all streams")
        for widget in self._video_widgets.values():
            if widget.get_camera() and not widget.is_streaming():
                widget.start_stream()
    
    def stop_all_streams(self) -> None:
        """Stop all video streams (parallel shutdown)."""
        logger.info("Stopping all streams")
        # Signal all threads to stop
        for widget in self._video_widgets.values():
            widget.stop_stream_async()
            
        # Wait for all threads to finish
        for widget in self._video_widgets.values():
            widget.wait_for_stream_stop()
    
    def get_active_stream_count(self) -> int:
        """Get number of active streams."""
        count = 0
        for widget in self._video_widgets.values():
            if widget.is_streaming():
                count += 1
        return count
    
    def _save_assignments(self) -> None:
        """Save camera assignments to config."""
        # Convert to serializable format
        assignments_data = {}
        for (row, col), camera_id in self._assignments.items():
            key = f"{row},{col}"
            assignments_data[key] = camera_id
        
        config.set(f"layout.grid_assignments.{self._current_layout}", assignments_data, save=True)
    
    def _load_assignments(self) -> None:
        """Load camera assignments from config."""
        from core.camera_manager import camera_manager
        
        assignments_data = config.get(f"layout.grid_assignments.{self._current_layout}", {})
        
        for key, camera_id in assignments_data.items():
            try:
                row, col = map(int, key.split(','))
                
                # Check if cell exists in current grid
                if (row, col) not in self._video_widgets:
                    continue
                
                # Get camera
                if camera_id.startswith("zero_"):
                    nvr_id = camera_id.replace("zero_", "")
                    from core.nvr_manager import nvr_manager
                    nvr = nvr_manager.get_nvr(nvr_id)
                    if nvr and getattr(nvr, 'zero_stream_enabled', False):
                        from models.camera import Camera
                        camera = Camera(
                            id=camera_id,
                            name=f"{nvr.name} (Preview)",
                            url=nvr.zero_stream_url,
                            username=nvr.username,
                            password=nvr.password,
                            nvr_id=nvr.id
                        )
                    else:
                        camera = None
                else:
                    camera = camera_manager.get_camera(camera_id)

                if camera:
                    self.assign_camera_to_cell(camera, row, col)
                else:
                    logger.warning(f"Camera {camera_id} not found for assignment")
            
            except Exception as e:
                logger.error(f"Failed to load assignment {key}: {e}")
    
    def _handle_fullscreen(self, video_widget: VideoWidget) -> None:
        """
        Handle fullscreen request from video widget.
        
        Args:
            video_widget: VideoWidget requesting fullscreen
        """
        camera = video_widget.get_camera()
        if not camera:
            logger.warning("Cannot go fullscreen: no camera assigned")
            return
        
        from ui.fullscreen_dialog import FullscreenVideoDialog
        
        # Stop the current stream in the widget (optional - to save resources)
        # video_widget.stop_stream()
        
        # Show fullscreen dialog
        dialog = FullscreenVideoDialog(camera, self)
        dialog.exec()
        
        # Restart stream in widget when fullscreen closes (if it was stopped)
        # video_widget.start_stream()
        
        logger.info(f"Fullscreen mode closed for {camera.name}")
    
    def _handle_screenshot(self, video_widget: VideoWidget) -> None:
        """
        Handle screenshot request from video widget.
        
        Args:
            video_widget: VideoWidget requesting screenshot
        """
        camera = video_widget.get_camera()
        frame = video_widget.get_current_frame()
        
        if not camera or frame is None:
            logger.warning("Cannot take screenshot: no camera or frame")
            return
        
        # Save screenshot
        import cv2
        import os
        from datetime import datetime
        
        screenshot_path = config.get("settings.screenshot_path", "./screenshots")
        if not os.path.exists(screenshot_path):
            os.makedirs(screenshot_path)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(screenshot_path, f"{camera.name}_{timestamp}.jpg")
        
        cv2.imwrite(filename, frame)
        logger.info(f"Screenshot saved: {filename}")
        
        # Show notification (optional)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Screenshot", f"Screenshot saved to:\n{filename}")
    
    def dragEnterEvent(self, event) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event) -> None:
        """Handle drop event."""
        # TODO: Implement drag & drop from resource tree
        logger.info("Drop event (drag & drop not yet fully implemented)")
        event.acceptProposedAction()
    
    def _handle_camera_drop(self, camera_id: str, row: int, col: int) -> None:
        """
        Handle camera drop on video widget.
        
        Args:
            camera_id: Camera ID
            row: Grid row
            col: Grid column
        """
        from core.camera_manager import camera_manager
        
        if camera_id.startswith("zero_"):
            # Handle Zero Channel drop
            nvr_id = camera_id.replace("zero_", "")
            from core.nvr_manager import nvr_manager
            nvr = nvr_manager.get_nvr(nvr_id)
            if nvr and getattr(nvr, 'zero_stream_enabled', False):
                from models.camera import Camera
                camera = Camera(
                    id=camera_id,
                    name=f"{nvr.name} (Preview)",
                    url=nvr.zero_stream_url,
                    username=nvr.username,
                    password=nvr.password,
                    nvr_id=nvr.id
                )
            else:
                logger.warning(f"Could not find NVR or Zero Channel for {camera_id}")
                return
        else:
            camera = camera_manager.get_camera(camera_id)
            
        if camera:
            self.assign_camera_to_cell(camera, row, col)
        else:
            logger.warning(f"Dropped camera ID not found: {camera_id}")
