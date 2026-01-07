"""
MediaMTX VMS Client v2.0 - Database Manager
Database operations wrapper for cameras, NVRs, and layouts.
"""

from typing import List, Optional
from contextlib import contextmanager

from models.database import DatabaseConnection, CameraDB, NVRDB, LayoutDB
from models.camera import Camera
from models.nvr import NVR
from models.layout import Layout
from utils.logger import logger


class DatabaseManager:
    """
    Database operations manager.
    
    Provides high-level CRUD operations for cameras, NVRs, and layouts.
    """
    
    def __init__(self, db_path: str = "vms_client.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self._db = DatabaseConnection(db_path)
        self._db.create_tables()
        logger.info(f"DatabaseManager initialized (db={db_path})")
    
    @contextmanager
    def _session(self):
        """Context manager for database sessions."""
        session = self._db.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    # Camera operations
    
    def get_cameras(self) -> List[Camera]:
        """Get all cameras."""
        with self._session() as session:
            cameras_db = session.query(CameraDB).all()
            return [cam.to_camera() for cam in cameras_db]
    
    def get_camera(self, camera_id: str) -> Optional[Camera]:
        """Get camera by ID."""
        with self._session() as session:
            camera_db = session.query(CameraDB).filter(CameraDB.id == camera_id).first()
            return camera_db.to_camera() if camera_db else None
    
    def add_camera(self, camera: Camera) -> bool:
        """Add new camera."""
        try:
            with self._session() as session:
                camera_db = CameraDB.from_camera(camera)
                session.add(camera_db)
            logger.info(f"Added camera: {camera.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add camera: {e}")
            return False
    
    def update_camera(self, camera: Camera) -> bool:
        """Update existing camera."""
        try:
            with self._session() as session:
                camera_db = session.query(CameraDB).filter(CameraDB.id == camera.id).first()
                if camera_db:
                    # Update fields
                    for key, value in CameraDB.from_camera(camera).__dict__.items():
                        if not key.startswith('_'):
                            setattr(camera_db, key, value)
                    logger.info(f"Updated camera: {camera.name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update camera: {e}")
            return False
    
    def delete_camera(self, camera_id: str) -> bool:
        """Delete camera by ID."""
        try:
            with self._session() as session:
                camera_db = session.query(CameraDB).filter(CameraDB.id == camera_id).first()
                if camera_db:
                    session.delete(camera_db)
                    logger.info(f"Deleted camera: {camera_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete camera: {e}")
            return False
    
    # NVR operations
    
    def get_nvrs(self) -> List[NVR]:
        """Get all NVRs."""
        with self._session() as session:
            nvrs_db = session.query(NVRDB).all()
            return [nvr.to_nvr() for nvr in nvrs_db]
    
    def get_nvr(self, nvr_id: str) -> Optional[NVR]:
        """Get NVR by ID."""
        with self._session() as session:
            nvr_db = session.query(NVRDB).filter(NVRDB.id == nvr_id).first()
            return nvr_db.to_nvr() if nvr_db else None
    
    def add_nvr(self, nvr: NVR) -> bool:
        """Add new NVR."""
        try:
            with self._session() as session:
                nvr_db = NVRDB.from_nvr(nvr)
                session.add(nvr_db)
            logger.info(f"Added NVR: {nvr.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add NVR: {e}")
            return False
    
    def update_nvr(self, nvr: NVR) -> bool:
        """Update existing NVR."""
        try:
            with self._session() as session:
                nvr_db = session.query(NVRDB).filter(NVRDB.id == nvr.id).first()
                if nvr_db:
                    for key, value in NVRDB.from_nvr(nvr).__dict__.items():
                        if not key.startswith('_'):
                            setattr(nvr_db, key, value)
                    logger.info(f"Updated NVR: {nvr.name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update NVR: {e}")
            return False
    
    def delete_nvr(self, nvr_id: str) -> bool:
        """Delete NVR by ID."""
        try:
            with self._session() as session:
                nvr_db = session.query(NVRDB).filter(NVRDB.id == nvr_id).first()
                if nvr_db:
                    session.delete(nvr_db)
                    logger.info(f"Deleted NVR: {nvr_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete NVR: {e}")
            return False
    
    # Layout operations
    
    def get_layouts(self) -> List[Layout]:
        """Get all layouts."""
        with self._session() as session:
            layouts_db = session.query(LayoutDB).all()
            return [layout.to_layout() for layout in layouts_db]
    
    def get_layout(self, layout_id: str) -> Optional[Layout]:
        """Get layout by ID."""
        with self._session() as session:
            layout_db = session.query(LayoutDB).filter(LayoutDB.id == layout_id).first()
            return layout_db.to_layout() if layout_db else None
    
    def add_layout(self, layout: Layout) -> bool:
        """Add new layout."""
        try:
            with self._session() as session:
                layout_db = LayoutDB.from_layout(layout)
                session.add(layout_db)
            logger.info(f"Added layout: {layout.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add layout: {e}")
            return False
    
    def update_layout(self, layout: Layout) -> bool:
        """Update existing layout."""
        try:
            with self._session() as session:
                layout_db = session.query(LayoutDB).filter(LayoutDB.id == layout.id).first()
                if layout_db:
                    for key, value in LayoutDB.from_layout(layout).__dict__.items():
                        if not key.startswith('_'):
                            setattr(layout_db, key, value)
                    logger.info(f"Updated layout: {layout.name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update layout: {e}")
            return False
    
    def delete_layout(self, layout_id: str) -> bool:
        """Delete layout by ID."""
        try:
            with self._session() as session:
                layout_db = session.query(LayoutDB).filter(LayoutDB.id == layout_id).first()
                if layout_db:
                    session.delete(layout_db)
                    logger.info(f"Deleted layout: {layout_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete layout: {e}")
            return False
    
    # Utility operations
    
    def get_statistics(self) -> dict:
        """Get database statistics."""
        with self._session() as session:
            camera_count = session.query(CameraDB).count()
            nvr_count = session.query(NVRDB).count()
            layout_count = session.query(LayoutDB).count()
            
            return {
                'cameras': camera_count,
                'nvrs': nvr_count,
                'layouts': layout_count
            }
