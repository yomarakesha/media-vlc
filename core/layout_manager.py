"""
MediaMTX VMS Client v2.0 - Layout Manager  
CRUD operations for custom grid layouts.
"""

import json
import os
from typing import List, Optional
from pathlib import Path

from models.layout import Layout
from utils.logger import logger


class LayoutManager:
    """
    Manages custom grid layout configurations.
    
    Handles creation, saving, loading, and deletion of layouts.
    Layouts are stored as JSON files in the layouts directory.
    """
    
    TEMPLATES = {
        "Security 4+1": {
            "name": "Security 4+1",
            "rows": 3,
            "cols": 3,
            "description": "Large camera in top-left 2x2, 4 small cameras on right and bottom"
        },
        "Entrance Focus": {
            "name": "Entrance Focus",
            "rows": 4,
            "cols": 4,
            "description": "Large entrance camera, 6 smaller side cameras"
        },
        "Retail Store": {
            "name": "Retail Store",
            "rows": 3,
            "cols": 4,
            "description": "4 overhead + 8 side cameras"
        },
        "Office Monitoring": {
            "name": "Office Monitoring",
            "rows": 2,
            "cols": 3,
            "description": "6 cameras for office spaces"
        },
        "Parking Lot": {
            "name": "Parking Lot",
            "rows": 2,
            "cols": 4,
            "description": "8 cameras for wide parking coverage"
        }
    }
    
    def __init__(self, layouts_dir: str = "layouts"):
        """
        Initialize layout manager.
        
        Args:
            layouts_dir: Directory to store layout files
        """
        self._layouts_dir = Path(layouts_dir)
        self._layouts_dir.mkdir(exist_ok=True)
        
        self._layouts: List[Layout] = []
        self._load_all()
        
        logger.info(f"LayoutManager initialized ({len(self._layouts)} layouts loaded)")
    
    def create_layout(self, name: str, rows: int, cols: int) -> Layout:
        """
        Create new layout.
        
        Args:
            name: Layout name
            rows: Number of rows
            cols: Number of columns
            
        Returns:
            New Layout object
        """
        layout = Layout(name=name, rows=rows, cols=cols)
        is_valid, error = layout.validate()
        
        if not is_valid:
            raise ValueError(f"Invalid layout: {error}")
        
        self._layouts.append(layout)
        self._save_layout(layout)
        
        logger.info(f"Created layout: {name} ({rows}x{cols})")
        return layout
    
    def create_from_template(self, template_name: str) -> Optional[Layout]:
        """
        Create layout from template.
        
        Args:
            template_name: Template name
            
        Returns:
            New Layout or None if template not found
        """
        if template_name not in self.TEMPLATES:
            logger.error(f"Template not found: {template_name}")
            return None
        
        template = self.TEMPLATES[template_name]
        return self.create_layout(
            name=template['name'],
            rows=template['rows'],
            cols=template['cols']
        )
    
    def get_all_layouts(self) -> List[Layout]:
        """Get all layouts."""
        return self._layouts.copy()
    
    def get_layout(self, layout_id: str) -> Optional[Layout]:
        """
        Get layout by ID.
        
        Args:
            layout_id: Layout ID
            
        Returns:
            Layout or None if not found
        """
        for layout in self._layouts:
            if layout.id == layout_id:
                return layout
        return None
    
    def update_layout(self, layout: Layout) -> bool:
        """
        Update existing layout.
        
        Args:
            layout: Layout object with updated data
            
        Returns:
            True if successful
        """
        for i, existing in enumerate(self._layouts):
            if existing.id == layout.id:
                layout.update_modified()
                self._layouts[i] = layout
                self._save_layout(layout)
                logger.info(f"Updated layout: {layout.name}")
                return True
        
        logger.error(f"Layout not found: {layout.id}")
        return False
    
    def delete_layout(self, layout_id: str) -> bool:
        """
        Delete layout.
        
        Args:
            layout_id: Layout ID
            
        Returns:
            True if successful
        """
        for i, layout in enumerate(self._layouts):
            if layout.id == layout_id:
                self._layouts.pop(i)
                self._delete_file(layout_id)
                logger.info(f"Deleted layout: {layout.name}")
                return True
        
        return False
    
    def export_layout(self, layout_id: str, export_path: str) -> bool:
        """
        Export layout to JSON file.
        
        Args:
            layout_id: Layout ID
            export_path: Export file path
            
        Returns:
            True if successful
        """
        layout = self.get_layout(layout_id)
        if not layout:
            return False
        
        try:
            with open(export_path, 'w') as f:
                json.dump(layout.to_dict(), f, indent=2)
            logger.info(f"Exported layout to: {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export layout: {e}")
            return False
    
    def import_layout(self, import_path: str) -> Optional[Layout]:
        """
        Import layout from JSON file.
        
        Args:
            import_path: Import file path
            
        Returns:
            Imported Layout or None if failed
        """
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)
            
            layout = Layout.from_dict(data)
            
            # Generate new ID to avoid conflicts
            import uuid
            layout.id = str(uuid.uuid4())
            layout.update_modified()
            
            is_valid, error = layout.validate()
            if not is_valid:
                raise ValueError(f"Invalid layout: {error}")
            
            self._layouts.append(layout)
            self._save_layout(layout)
            
            logger.info(f"Imported layout: {layout.name}")
            return layout
        
        except Exception as e:
            logger.error(f"Failed to import layout: {e}")
            return None
    
    def _load_all(self) -> None:
        """Load all layouts from directory."""
        self._layouts.clear()
        
        if not self._layouts_dir.exists():
            return
        
        for file_path in self._layouts_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                layout = Layout.from_dict(data)
                self._layouts.append(layout)
                
            except Exception as e:
                logger.warning(f"Failed to load layout {file_path}: {e}")
        
        logger.debug(f"Loaded {len(self._layouts)} layouts")
    
    def _save_layout(self, layout: Layout) -> None:
        """
        Save layout to file.
        
        Args:
            layout: Layout to save
        """
        file_path = self._layouts_dir / f"{layout.id}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(layout.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
    
    def _delete_file(self, layout_id: str) -> None:
        """
        Delete layout file.
        
        Args:
            layout_id: Layout ID
        """
        file_path = self._layouts_dir / f"{layout_id}.json"
        
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete layout file: {e}")
    
    @staticmethod
    def get_template_names() -> List[str]:
        """Get list of available template names."""
        return list(LayoutManager.TEMPLATES.keys())
    
    @staticmethod
    def get_template_description(template_name: str) -> str:
        """
        Get template description.
        
        Args:
            template_name: Template name
            
        Returns:
            Description or empty string
        """
        template = LayoutManager.TEMPLATES.get(template_name)
        return template.get('description', '') if template else ''
