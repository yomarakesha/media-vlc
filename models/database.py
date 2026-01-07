"""
MediaMTX VMS Client v2.0 - Database Models
SQLAlchemy ORM models for SQLite database.
"""

from sqlalchemy import create_engine, Column, String, Integer, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import json

Base = declarative_base()


class CameraDB(Base):
    """Camera database model."""
    
    __tablename__ = 'cameras'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    sub_stream_url = Column(String, default='')
    username = Column(String, default='')
    password = Column(String, default='')
    type = Column(String, default='RTSP')
    group = Column(String, default='Default')
    stream_quality = Column(String, default='auto')
    motion_detection = Column(Boolean, default=False)
    recording_enabled = Column(Boolean, default=False)
    recording_mode = Column(String, default='motion')
    pre_buffer_seconds = Column(Integer, default=5)
    post_buffer_seconds = Column(Integer, default=10)
    description = Column(String, default='')
    location = Column(String, default='')
    manufacturer = Column(String, default='')
    model = Column(String, default='')
    nvr_id = Column(String, nullable=True)
    channel = Column(Integer, nullable=True)
    
    # JSON fields for complex data
    recording_schedule = Column(Text, default='[]')  # JSON array
    detection_zones = Column(Text, default='[]')  # JSON array
    
    def to_camera(self):
        """Convert to Camera model."""
        from models.camera import Camera
        
        return Camera(
            id=self.id,
            name=self.name,
            url=self.url,
            sub_stream_url=self.sub_stream_url,
            username=self.username,
            password=self.password,
            type=self.type,
            group=self.group,
            stream_quality=self.stream_quality,
            motion_detection=self.motion_detection,
            recording_enabled=self.recording_enabled,
            description=self.description,
            location=self.location,
            manufacturer=self.manufacturer,
            model=self.model,
            nvr_id=self.nvr_id,
            channel=self.channel
        )
    
    @staticmethod
    def from_camera(camera):
        """Create from Camera model."""
        return CameraDB(
            id=camera.id,
            name=camera.name,
            url=camera.url,
            sub_stream_url=getattr(camera, 'sub_stream_url', ''),
            username=camera.username,
            password=camera.password,
            type=camera.type,
            group=camera.group,
            stream_quality=getattr(camera, 'stream_quality', 'auto'),
            motion_detection=camera.motion_detection,
            recording_enabled=camera.recording_enabled,
            description=camera.description,
            location=camera.location,
            manufacturer=camera.manufacturer,
            model=camera.model,
            nvr_id=camera.nvr_id,
            channel=camera.channel
        )


class NVRDB(Base):
    """NVR database model."""
    
    __tablename__ = 'nvrs'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, default=80)
    username = Column(String, default='')
    password = Column(String, default='')
    onvif_enabled = Column(Boolean, default=True)
    onvif_port = Column(Integer, default=80)
    rtsp_port = Column(Integer, default=554)
    manufacturer = Column(String, default='')
    model = Column(String, default='')
    firmware = Column(String, default='')
    
    # Zero channel stream
    zero_channel_enabled = Column(Boolean, default=False)
    zero_channel_url = Column(String, default='')
    
    # Camera list (JSON)
    cameras_json = Column(Text, default='[]')
    
    def to_nvr(self):
        """Convert to NVR model."""
        from models.nvr import NVR
        
        return NVR(
            id=self.id,
            name=self.name,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            onvif_enabled=self.onvif_enabled,
            onvif_port=self.onvif_port,
            rtsp_port=self.rtsp_port,
            manufacturer=self.manufacturer,
            model=self.model,
            firmware=self.firmware,
            zero_channel_enabled=self.zero_channel_enabled,
            zero_channel_url=self.zero_channel_url,
            cameras=json.loads(self.cameras_json) if self.cameras_json else []
        )
    
    @staticmethod
    def from_nvr(nvr):
        """Create from NVR model."""
        return NVRDB(
            id=nvr.id,
            name=nvr.name,
            host=nvr.host,
            port=nvr.port,
            username=nvr.username,
            password=nvr.password,
            onvif_enabled=nvr.onvif_enabled,
            onvif_port=nvr.onvif_port,
            rtsp_port=nvr.rtsp_port,
            manufacturer=nvr.manufacturer,
            model=nvr.model,
            firmware=nvr.firmware,
            zero_channel_enabled=nvr.zero_channel_enabled,
            zero_channel_url=nvr.zero_channel_url,
            cameras_json=json.dumps(nvr.cameras) if nvr.cameras else '[]'
        )


class LayoutDB(Base):
    """Layout database model."""
    
    __tablename__ = 'layouts'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    rows = Column(Integer, nullable=False)
    cols = Column(Integer, nullable=False)
    created_at = Column(String)
    modified_at = Column(String)
    
    # Camera assignments (JSON)
    assignments_json = Column(Text, default='{}')
    
    def to_layout(self):
        """Convert to Layout model."""
        from models.layout import Layout
        
        return Layout(
            id=self.id,
            name=self.name,
            rows=self.rows,
            cols=self.cols,
            camera_assignments=json.loads(self.assignments_json) if self.assignments_json else {},
            created_at=self.created_at,
            modified_at=self.modified_at
        )
    
    @staticmethod
    def from_layout(layout):
        """Create from Layout model."""
        return LayoutDB(
            id=layout.id,
            name=layout.name,
            rows=layout.rows,
            cols=layout.cols,
            created_at=layout.created_at,
            modified_at=layout.modified_at,
            assignments_json=json.dumps(layout.camera_assignments)
        )


class DatabaseConnection:
    """Database connection manager."""
    
    def __init__(self, db_path: str = "vms_client.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)
    
    def drop_tables(self) -> None:
        """Drop all tables."""
        Base.metadata.drop_all(self.engine)
    
    def get_session(self) -> Session:
        """Get new database session."""
        return self.SessionLocal()
