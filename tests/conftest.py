"""
MediaMTX VMS Client - Pytest Configuration
Fixtures and test configuration for automated testing.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_camera():
    """
    Fixture providing a sample Camera instance for testing.
    
    Returns:
        Camera: Sample camera with typical configuration
    """
    from models.camera import Camera
    
    return Camera(
        name="Test Camera",
        url="rtsp://192.168.1.100:554/stream1",
        sub_stream_url="rtsp://192.168.1.100:554/stream2",
        username="admin",
        password="password123",
        type="RTSP",
        group="Test Group",
        motion_detection=True,
        recording_enabled=True,
        location="Front Door",
        manufacturer="Hikvision",
        model="DS-2CD2042WD"
    )


@pytest.fixture
def sample_camera_no_substream():
    """
    Fixture providing a camera without sub-stream configuration.
    
    Returns:
        Camera: Sample camera without sub-stream
    """
    from models.camera import Camera
    
    return Camera(
        name="Simple Camera",
        url="rtsp://192.168.1.101:554/main",
        type="RTSP"
    )


@pytest.fixture
def sample_nvr():
    """
    Fixture providing a sample NVR instance for testing.
    
    Returns:
        NVR: Sample NVR with typical configuration
    """
    from models.nvr import NVR
    
    return NVR(
        name="Test NVR",
        host="192.168.1.200",
        port=80,
        username="admin",
        password="admin123",
        onvif_enabled=True,
        rtsp_port=554
    )


@pytest.fixture
def temp_config(tmp_path):
    """
    Fixture providing temporary config file for testing.
    
    Args:
        tmp_path: Pytest tmp_path fixture
        
    Returns:
        Path: Path to temporary config file
    """
    config_file = tmp_path / "test_config.json"
    return config_file


@pytest.fixture
def config_manager(temp_config):
    """
    Fixture providing a fresh ConfigManager instance for testing.
    
    Args:
        temp_config: Temporary config file path
        
    Returns:
        ConfigManager: Fresh config manager instance
    """
    from utils.config import ConfigManager
    
    manager = ConfigManager(str(temp_config))
    return manager


# PyQt6 fixtures (if needed for UI tests)
@pytest.fixture(scope="session")
def qapp():
    """
    Fixture providing QApplication instance for UI tests.
    Session-scoped to avoid multiple QApplication instances.
    
    Returns:
        QApplication: Qt application instance
    """
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    yield app
    
    # Cleanup
    app.quit()


@pytest.fixture
def qtbot(qapp, request):
    """
    Fixture providing QtBot for widget testing.
    
    Args:
        qapp: QApplication fixture
        request: Pytest request object
        
    Returns:
        QtBot: Qt test helper
    """
    try:
        from pytestqt.qtbot import QtBot
        bot = QtBot(request)
        return bot
    except ImportError:
        pytest.skip("pytest-qt not installed")
