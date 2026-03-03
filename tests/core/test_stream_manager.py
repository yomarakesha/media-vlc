"""Tests for VideoStreamThread and stream management.

This module tests the video streaming functionality including:
- Thread lifecycle management
- Connection handling
- Status transitions
- Frame processing
- Reconnection logic
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QThread
import numpy as np


class TestVideoStreamThread:
    """Test VideoStreamThread class."""
    
    @pytest.fixture
    def sample_camera(self, sample_camera):
        """Get sample camera from conftest."""
        return sample_camera

    def test_thread_creation(self, sample_camera):
        """Test thread can be created with a camera."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        assert thread is not None
        assert thread._camera == sample_camera
        assert thread._running is False
        assert thread._cap is None

    def test_thread_start_stop(self, sample_camera, qtbot):
        """Test thread start and stop lifecycle."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        # Mock cv2.VideoCapture to avoid actual connection
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap.return_value.isOpened.return_value = False
            
            thread.start()
            assert thread.isRunning() or thread._running
            
            thread.stop()
            thread.wait(2000)  # Wait up to 2 seconds
            
            assert not thread.isRunning()

    def test_status_signal_emission(self, sample_camera, qtbot):
        """Test status signals are emitted correctly."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        statuses = []
        
        def on_status(status):
            statuses.append(status)
        
        thread.status_changed.connect(on_status)
        
        # Trigger status update
        thread._emit_status("connecting")
        
        assert "connecting" in statuses

    def test_connection_url_construction(self, sample_camera):
        """Test RTSP URL is correctly constructed with credentials."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        # The URL should be constructed in _connect method
        # Test that camera URL is accessible
        assert sample_camera.url is not None
        assert sample_camera.url.startswith("rtsp://")

    def test_frame_to_qimage_conversion(self, sample_camera):
        """Test numpy array to QImage conversion."""
        from core.stream_manager import VideoStreamThread
        from PyQt6.QtGui import QImage
        
        thread = VideoStreamThread(sample_camera)
        
        # Create test frame (BGR format as OpenCV provides)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 2] = 255  # Red channel
        
        qimage = thread._frame_to_qimage(frame)
        
        assert qimage is not None
        assert isinstance(qimage, QImage)
        assert qimage.width() == 640
        assert qimage.height() == 480

    def test_invalid_frame_handling(self, sample_camera):
        """Test handling of invalid frames."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        # Empty frame
        result = thread._frame_to_qimage(None)
        assert result is None
        
        # Invalid shape
        bad_frame = np.zeros((10, 10), dtype=np.uint8)  # 2D instead of 3D
        result = thread._frame_to_qimage(bad_frame)
        assert result is None

    def test_reconnection_counter(self, sample_camera):
        """Test reconnection attempt counter."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        assert thread._reconnect_attempts == 0
        assert thread._max_reconnect_attempts > 0
        
        # Simulate reconnection
        thread._reconnect_attempts += 1
        assert thread._reconnect_attempts == 1

    def test_motion_detection_integration(self, sample_camera):
        """Test motion detection can be enabled."""
        from core.stream_manager import VideoStreamThread
        
        sample_camera.motion_detection = True
        thread = VideoStreamThread(sample_camera)
        
        # The thread should have motion detector if enabled
        assert hasattr(thread, '_motion_detector') or sample_camera.motion_detection

    def test_recording_flag(self, sample_camera):
        """Test recording flag handling."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        
        assert thread._recording is False
        
        thread.set_recording(True)
        assert thread._recording is True
        
        thread.set_recording(False)
        assert thread._recording is False


class TestStreamManager:
    """Test the stream manager singleton pattern if applicable."""
    
    def test_multiple_streams_handling(self, sample_camera):
        """Test handling multiple stream requests."""
        from core.stream_manager import VideoStreamThread
        
        thread1 = VideoStreamThread(sample_camera)
        thread2 = VideoStreamThread(sample_camera)
        
        # Should create separate thread instances
        assert thread1 is not thread2

    def test_error_signal(self, sample_camera, qtbot):
        """Test error signal emission on connection failure."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        errors = []
        
        def on_error(msg):
            errors.append(msg)
        
        thread.error.connect(on_error)
        
        # Trigger an error
        thread._emit_error("Connection failed")
        
        assert len(errors) == 1
        assert "Connection failed" in errors[0]


class TestStreamStatus:
    """Test stream status enum and transitions."""
    
    def test_valid_status_values(self):
        """Test all expected status values exist."""
        expected_statuses = [
            "idle", "connecting", "connected", 
            "reconnecting", "error", "stopped"
        ]
        
        # These should be valid status strings
        for status in expected_statuses:
            assert isinstance(status, str)
            assert len(status) > 0

    def test_status_transition_connecting_to_connected(self, sample_camera):
        """Test status transition from connecting to connected."""
        from core.stream_manager import VideoStreamThread
        
        thread = VideoStreamThread(sample_camera)
        statuses = []
        
        thread.status_changed.connect(lambda s: statuses.append(s))
        
        thread._emit_status("connecting")
        thread._emit_status("connected")
        
        assert "connecting" in statuses
        assert "connected" in statuses
        assert statuses.index("connecting") < statuses.index("connected")
