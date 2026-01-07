"""
MediaMTX VMS Client - Camera Model Tests
Comprehensive unit tests for the Camera dataclass.
"""

import pytest
from models.camera import Camera


class TestCameraCreation:
    """Test camera object creation and initialization."""
    
    def test_camera_default_values(self):
        """Test camera creation with default values."""
        camera = Camera()
        
        assert camera.name == "Camera"
        assert camera.url == ""
        assert camera.sub_stream_url == ""
        assert camera.type == "RTSP"
        assert camera.group == "Default"
        assert camera.stream_quality == "auto"
        assert camera.motion_detection is False
        assert camera.recording_enabled is False
        assert camera.id is not None  # UUID generated
    
    def test_camera_custom_values(self, sample_camera):
        """Test camera creation with custom values."""
        assert sample_camera.name == "Test Camera"
        assert sample_camera.url == "rtsp://192.168.1.100:554/stream1"
        assert sample_camera.sub_stream_url == "rtsp://192.168.1.100:554/stream2"
        assert sample_camera.username == "admin"
        assert sample_camera.type == "RTSP"
        assert sample_camera.motion_detection is True
    
    def test_camera_unique_ids(self):
        """Test that each camera gets a unique ID."""
        camera1 = Camera(name="Camera 1")
        camera2 = Camera(name="Camera 2")
        
        assert camera1.id != camera2.id


class TestCameraValidation:
    """Test camera validation logic."""
    
    def test_valid_rtsp_camera(self, sample_camera):
        """Test validation of valid RTSP camera."""
        is_valid, message = sample_camera.validate()
        
        assert is_valid is True
        assert message == ""
    
    def test_valid_hls_camera(self):
        """Test validation of valid HLS camera."""
        camera = Camera(
            name="HLS Camera",
            url="http://example.com/stream.m3u8",
            type="HLS"
        )
        is_valid, message = camera.validate()
        
        assert is_valid is True
        assert message == ""
    
    def test_missing_name(self):
        """Test validation fails for missing camera name."""
        camera = Camera(name="", url="rtsp://test")
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "name is required" in message
    
    def test_missing_url(self):
        """Test validation fails for missing URL."""
        camera = Camera(name="Test", url="")
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "URL is required" in message
    
    def test_invalid_stream_type(self):
        """Test validation fails for invalid stream type."""
        camera = Camera(name="Test", url="rtsp://test", type="INVALID")
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "type must be" in message
    
    def test_rtsp_url_format(self):
        """Test validation of RTSP URL format."""
        camera = Camera(name="Test", url="http://wrong", type="RTSP")
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "rtsp://" in message
    
    def test_hls_url_format(self):
        """Test validation of HLS URL format."""
        camera = Camera(name="Test", url="rtsp://wrong", type="HLS")
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "http" in message
    
    def test_sub_stream_rtsp_validation(self):
        """Test validation of sub-stream RTSP URL."""
        camera = Camera(
            name="Test",
            url="rtsp://main",
            sub_stream_url="http://wrong",
            type="RTSP"
        )
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "Sub-stream" in message and "rtsp://" in message
    
    def test_sub_stream_hls_validation(self):
        """Test validation of sub-stream HLS URL."""
        camera = Camera(
            name="Test",
            url="http://main.m3u8",
            sub_stream_url="rtsp://wrong",
            type="HLS"
        )
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "Sub-stream" in message and "http" in message
    
    def test_invalid_stream_quality(self):
        """Test validation of stream quality setting."""
        camera = Camera(
            name="Test",
            url="rtsp://test",
            stream_quality="invalid"
        )
        is_valid, message = camera.validate()
        
        assert is_valid is False
        assert "quality" in message


class TestStreamURLSelection:
    """Test stream URL selection logic."""
    
    def test_get_stream_url_high_quality(self, sample_camera):
        """Test explicit high quality selection returns main URL."""
        url = sample_camera.get_stream_url(quality="high")
        
        assert url == sample_camera.url
        assert url == "rtsp://192.168.1.100:554/stream1"
    
    def test_get_stream_url_low_quality(self, sample_camera):
        """Test explicit low quality selection returns sub-stream."""
        url = sample_camera.get_stream_url(quality="low")
        
        assert url == sample_camera.sub_stream_url
        assert url == "rtsp://192.168.1.100:554/stream2"
    
    def test_get_stream_url_low_no_substream(self, sample_camera_no_substream):
        """Test low quality falls back to main when no sub-stream."""
        url = sample_camera_no_substream.get_stream_url(quality="low")
        
        assert url == sample_camera_no_substream.url
    
    def test_get_stream_url_auto_small_widget(self, sample_camera):
        """Test auto quality uses sub-stream for small widgets."""
        url = sample_camera.get_stream_url(
            quality="auto",
            widget_size=(200, 200)
        )
        
        assert url == sample_camera.sub_stream_url
    
    def test_get_stream_url_auto_large_widget(self, sample_camera):
        """Test auto quality uses main stream for large widgets."""
        url = sample_camera.get_stream_url(
            quality="auto",
            widget_size=(800, 600)
        )
        
        assert url == sample_camera.url
    
    def test_get_stream_url_auto_no_size(self, sample_camera):
        """Test auto quality defaults to main stream without size."""
        url = sample_camera.get_stream_url(quality="auto")
        
        assert url == sample_camera.url
    
    def test_get_stream_url_auto_no_substream(self, sample_camera_no_substream):
        """Test auto quality with no sub-stream always returns main."""
        url = sample_camera_no_substream.get_stream_url(
            quality="auto",
            widget_size=(100, 100)
        )
        
        assert url == sample_camera_no_substream.url
    
    def test_has_sub_stream_true(self, sample_camera):
        """Test has_sub_stream returns True when configured."""
        assert sample_camera.has_sub_stream() is True
    
    def test_has_sub_stream_false(self, sample_camera_no_substream):
        """Test has_sub_stream returns False when not configured."""
        assert sample_camera_no_substream.has_sub_stream() is False


class TestCameraSerialization:
    """Test camera serialization and deserialization."""
    
    def test_to_dict(self, sample_camera):
        """Test camera to dictionary conversion."""
        camera_dict = sample_camera.to_dict()
        
        assert isinstance(camera_dict, dict)
        assert camera_dict["name"] == "Test Camera"
        assert camera_dict["url"] == "rtsp://192.168.1.100:554/stream1"
        assert camera_dict["sub_stream_url"] == "rtsp://192.168.1.100:554/stream2"
        assert camera_dict["stream_quality"] == "auto"
        assert "id" in camera_dict
    
    def test_from_dict(self):
        """Test camera creation from dictionary."""
        camera_data = {
            "name": "Dict Camera",
            "url": "rtsp://test",
            "sub_stream_url": "rtsp://test/sub",
            "type": "RTSP",
            "stream_quality": "high",
            "motion_detection": True
        }
        
        camera = Camera.from_dict(camera_data)
        
        assert camera.name == "Dict Camera"
        assert camera.url == "rtsp://test"
        assert camera.sub_stream_url == "rtsp://test/sub"
        assert camera.stream_quality == "high"
        assert camera.motion_detection is True
    
    def test_roundtrip_serialization(self, sample_camera):
        """Test camera survives roundtrip serialization."""
        original_dict = sample_camera.to_dict()
        restored_camera = Camera.from_dict(original_dict)
        restored_dict = restored_camera.to_dict()
        
        # Compare key fields (exclude ID as it might differ)
        assert original_dict["name"] == restored_dict["name"]
        assert original_dict["url"] == restored_dict["url"]
        assert original_dict["sub_stream_url"] == restored_dict["sub_stream_url"]


class TestCameraDisplayMethods:
    """Test camera display helper methods."""
    
    def test_get_display_name_with_location(self, sample_camera):
        """Test display name includes location when set."""
        display_name = sample_camera.get_display_name()
        
        assert display_name == "Test Camera (Front Door)"
    
    def test_get_display_name_without_location(self, sample_camera_no_substream):
        """Test display name is just name when location not set."""
        display_name = sample_camera_no_substream.get_display_name()
        
        assert display_name == "Simple Camera"
    
    def test_repr(self, sample_camera):
        """Test camera string representation."""
        repr_str = repr(sample_camera)
        
        assert "Camera(" in repr_str
        assert "Test Camera" in repr_str
        assert "RTSP" in repr_str
        assert "id=" in repr_str
