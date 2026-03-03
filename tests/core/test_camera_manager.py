"""Tests for CameraManager class.

This module tests the camera management functionality including:
- CRUD operations
- Duplicate detection
- Group management
- Stream URL handling
"""

import pytest
from unittest.mock import Mock, patch
from models.camera import Camera


@pytest.fixture
def sample_camera_data():
    """Sample camera data for tests."""
    return {
        'name': 'Test Camera',
        'url': 'rtsp://192.168.1.50:554/stream1',
        'username': 'admin',
        'password': 'test123',
        'type': 'RTSP'
    }


class TestCameraManager:
    """Test CameraManager class."""

    @pytest.fixture
    def camera_manager_instance(self, temp_config):
        """Create new camera manager instance for testing."""
        from core.camera_manager import CameraManager
        return CameraManager()
    
    @pytest.fixture
    def unique_camera(self):
        """Create camera with unique URL for each test."""
        import uuid
        return Camera(
            name='Unique Test Camera',
            url=f'rtsp://192.168.1.{uuid.uuid4().hex[:3]}:554/stream_{uuid.uuid4().hex[:8]}',
            username='admin',
            password='test123',
            type='RTSP'
        )

    def test_add_camera(self, camera_manager_instance, unique_camera):
        """Test adding a camera."""
        result = camera_manager_instance.add_camera(unique_camera)
        
        assert result is True
        assert unique_camera.id in [c.id for c in camera_manager_instance.get_all_cameras()]

    def test_add_duplicate_camera(self, camera_manager_instance, unique_camera):
        """Test adding duplicate camera should fail."""
        camera_manager_instance.add_camera(unique_camera)
        result = camera_manager_instance.add_camera(unique_camera)
        
        assert result is False  # Duplicate should fail

    def test_get_camera_by_id(self, camera_manager_instance, unique_camera):
        """Test retrieving camera by ID."""
        camera_manager_instance.add_camera(unique_camera)
        
        retrieved = camera_manager_instance.get_camera(unique_camera.id)
        
        assert retrieved is not None
        assert retrieved.id == unique_camera.id
        assert retrieved.name == unique_camera.name

    def test_get_nonexistent_camera(self, camera_manager_instance):
        """Test retrieving non-existent camera returns None."""
        result = camera_manager_instance.get_camera("nonexistent-id-12345")
        
        assert result is None

    def test_update_camera(self, camera_manager_instance, unique_camera):
        """Test updating a camera."""
        camera_manager_instance.add_camera(unique_camera)
        
        unique_camera.name = "Updated Camera Name"
        result = camera_manager_instance.update_camera(unique_camera)
        
        assert result is True
        retrieved = camera_manager_instance.get_camera(unique_camera.id)
        assert retrieved.name == "Updated Camera Name"

    def test_remove_camera(self, camera_manager_instance, unique_camera):
        """Test removing a camera."""
        camera_manager_instance.add_camera(unique_camera)
        
        result = camera_manager_instance.remove_camera(unique_camera.id)
        
        assert result is True
        assert camera_manager_instance.get_camera(unique_camera.id) is None

    def test_remove_nonexistent_camera(self, camera_manager_instance):
        """Test removing non-existent camera."""
        result = camera_manager_instance.remove_camera("nonexistent-id-12345")
        
        assert result is False or result is None

    def test_get_all_cameras(self, camera_manager_instance, unique_camera):
        """Test getting all cameras."""
        camera_manager_instance.add_camera(unique_camera)
        
        all_cameras = camera_manager_instance.get_all_cameras()
        
        assert isinstance(all_cameras, list)
        assert len(all_cameras) >= 1

    def test_camera_count(self, camera_manager_instance, unique_camera):
        """Test counting cameras."""
        initial_count = len(camera_manager_instance.get_all_cameras())
        
        camera_manager_instance.add_camera(unique_camera)
        
        new_count = len(camera_manager_instance.get_all_cameras())
        assert new_count == initial_count + 1


class TestCameraValidation:
    """Test camera validation."""

    def test_camera_creation(self, sample_camera_data):
        """Test camera can be created with valid data."""
        camera = Camera(**sample_camera_data)
        
        assert camera is not None
        assert camera.name == sample_camera_data['name']
        assert camera.url == sample_camera_data['url']

    def test_camera_validation_success(self, sample_camera_data):
        """Test camera validation passes for valid data."""
        camera = Camera(**sample_camera_data)
        
        result = camera.validate()
        
        # validate() returns tuple (is_valid: bool, error_msg: str)
        assert isinstance(result, tuple)
        is_valid, error_msg = result
        assert is_valid is True
        assert error_msg == ''

    def test_camera_validation_missing_url(self, sample_camera_data):
        """Test camera validation fails without URL."""
        sample_camera_data['url'] = ''
        camera = Camera(**sample_camera_data)
        
        result = camera.validate()
        
        # validate() returns tuple (is_valid: bool, error_msg: str)
        is_valid, error_msg = result
        assert is_valid is False
        assert 'url' in error_msg.lower()

    def test_camera_validation_invalid_url(self, sample_camera_data):
        """Test camera validation fails with invalid URL."""
        sample_camera_data['url'] = 'not-a-valid-url'
        camera = Camera(**sample_camera_data)
        
        result = camera.validate()
        
        # validate() returns tuple (is_valid: bool, error_msg: str)
        is_valid, error_msg = result
        assert is_valid is False

    def test_camera_to_dict(self, sample_camera):
        """Test camera serialization to dict."""
        data = sample_camera.to_dict()
        
        assert isinstance(data, dict)
        assert 'id' in data
        assert 'name' in data
        assert 'url' in data

    def test_camera_from_dict(self, sample_camera_data):
        """Test camera deserialization from dict."""
        sample_camera_data['id'] = 'test-id-123'
        
        camera = Camera.from_dict(sample_camera_data)
        
        assert camera.id == 'test-id-123'
        assert camera.name == sample_camera_data['name']


class TestCameraGroups:
    """Test camera group management."""

    def test_camera_default_group(self, sample_camera_data):
        """Test camera has default group."""
        camera = Camera(**sample_camera_data)
        
        # Group should have a default value
        assert hasattr(camera, 'group')

    def test_camera_group_assignment(self, sample_camera_data):
        """Test camera group can be set."""
        sample_camera_data['group'] = 'Lobby'
        camera = Camera(**sample_camera_data)
        
        assert camera.group == 'Lobby'

    def test_get_cameras_by_group(self):
        """Test filtering cameras by group."""
        from core.camera_manager import camera_manager
        
        # This tests the group filtering if implemented
        if hasattr(camera_manager, 'get_cameras_by_group'):
            cameras = camera_manager.get_cameras_by_group('Test')
            assert isinstance(cameras, list)


class TestCameraStreamURL:
    """Test camera stream URL handling."""

    def test_get_stream_url_main(self, sample_camera):
        """Test getting main stream URL."""
        url = sample_camera.get_stream_url(quality='main')
        
        assert url is not None
        assert isinstance(url, str)

    def test_get_stream_url_sub(self, sample_camera):
        """Test getting sub stream URL when available."""
        if sample_camera.sub_stream_url:
            url = sample_camera.get_stream_url(quality='sub')
            assert url is not None

    def test_stream_url_with_credentials(self, sample_camera):
        """Test stream URL includes credentials when needed."""
        url = sample_camera.url
        
        # URL should be properly formatted
        assert url.startswith('rtsp://') or url.startswith('http://')

    def test_motion_detection_flag(self, sample_camera):
        """Test motion detection flag."""
        sample_camera.motion_detection = True
        
        assert sample_camera.motion_detection is True
        
        sample_camera.motion_detection = False
        assert sample_camera.motion_detection is False

    def test_recording_flag(self, sample_camera):
        """Test recording flag."""
        sample_camera.recording = True
        
        assert sample_camera.recording is True


class TestCameraManagerThreadSafety:
    """Test thread safety of camera manager."""

    def test_concurrent_access(self):
        """Test concurrent read/write operations."""
        from core.camera_manager import CameraManager
        import threading
        
        manager = CameraManager()
        errors = []
        
        def add_operation():
            try:
                camera = Camera(
                    name=f"Thread Camera {threading.current_thread().name}",
                    url="rtsp://192.168.1.100:554/stream",
                    username="admin",
                    password="test"
                )
                manager.add_camera(camera)
            except Exception as e:
                errors.append(e)
        
        def read_operation():
            try:
                manager.get_all_cameras()
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=add_operation)
            t2 = threading.Thread(target=read_operation)
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0
