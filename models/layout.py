"""
MediaMTX VMS Client v2.0 - Layout Model
Custom grid layout configuration data model.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict
import uuid


@dataclass
class Layout:
    """
    Custom grid layout configuration.
    
    Attributes:
        id: Unique layout identifier
        name: Layout name
        rows: Number of rows
        cols: Number of columns
        camera_assignments: Dictionary mapping positions to camera IDs
                           Format: {"row,col": "camera_id"}
        created_at: Creation timestamp
        modified_at: Last modification timestamp
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rows: int = 2
    cols: int = 2
    camera_assignments: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert layout to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Layout':
        """Create layout from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def update_modified(self) -> None:
        """Update modification timestamp."""
        self.modified_at = datetime.now().isoformat()
    
    def get_camera_at(self, row: int, col: int) -> str:
        """
        Get camera ID at position.
        
        Args:
            row: Row index
            col: Column index
            
        Returns:
            Camera ID or empty string
        """
        key = f"{row},{col}"
        return self.camera_assignments.get(key, "")
    
    def set_camera_at(self, row: int, col: int, camera_id: str) -> None:
        """
        Set camera at position.
        
        Args:
            row: Row index
            col: Column index
            camera_id: Camera ID (empty to clear)
        """
        key = f"{row},{col}"
        if camera_id:
            self.camera_assignments[key] = camera_id
        elif key in self.camera_assignments:
            del self.camera_assignments[key]
        self.update_modified()
    
    def clear_position(self, row: int, col: int) -> None:
        """
        Clear camera at position.
        
        Args:
            row: Row index
            col: Column index
        """
        self.set_camera_at(row, col, "")
    
    def clear_all(self) -> None:
        """Clear all camera assignments."""
        self.camera_assignments.clear()
        self.update_modified()
    
    def get_assigned_cameras(self) -> list:
        """
        Get list of assigned camera IDs.
        
        Returns:
            List of unique camera IDs
        """
        return list(set(self.camera_assignments.values()))
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate layout configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.name:
            return False, "Layout name is required"
        
        if self.rows < 1 or self.rows > 10:
            return False, "Rows must be between 1 and 10"
        
        if self.cols < 1 or self.cols > 10:
            return False, "Columns must be between 1 and 10"
        
        return True, ""
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Layout(id={self.id[:8]}..., name={self.name}, grid={self.rows}x{self.cols}, cameras={len(self.get_assigned_cameras())})"
