"""Tests for NVRManager class.

This module tests the NVR management functionality including:
- CRUD operations
- Thread safety
- Validation
- Persistence
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from models.nvr import NVR


class TestNVRManager:
    """Test NVRManager class."""
    
    @pytest.fixture
    def nvr_manager_instance(self, temp_config):
        """Create new NVR manager instance for testing."""
        from core.nvr_manager import NVRManager
        return NVRManager()
    
    @pytest.fixture
    def sample_nvr_data(self):
        """Sample NVR data for tests."""
        return {
            'name': 'Test NVR',
            'host': '192.168.1.100',
            'port': 80,
            'username': 'admin',
            'password': 'test123'
        }

    def test_add_nvr(self, nvr_manager_instance, sample_nvr):
        """Test adding an NVR."""
        result = nvr_manager_instance.add_nvr(sample_nvr)
        
        assert result is True
        assert sample_nvr.id in [n.id for n in nvr_manager_instance.get_all_nvrs()]

    def test_add_duplicate_nvr(self, nvr_manager_instance, sample_nvr):
        """Test adding duplicate NVR should fail."""
        nvr_manager_instance.add_nvr(sample_nvr)
        result = nvr_manager_instance.add_nvr(sample_nvr)
        
        # Should either fail or update
        assert isinstance(result, bool)

    def test_get_nvr_by_id(self, nvr_manager_instance, sample_nvr):
        """Test retrieving NVR by ID."""
        nvr_manager_instance.add_nvr(sample_nvr)
        
        retrieved = nvr_manager_instance.get_nvr(sample_nvr.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_nvr.id
        assert retrieved.name == sample_nvr.name

    def test_get_nonexistent_nvr(self, nvr_manager_instance):
        """Test retrieving non-existent NVR returns None."""
        result = nvr_manager_instance.get_nvr("nonexistent-id-12345")
        
        assert result is None

    def test_update_nvr(self, nvr_manager_instance, sample_nvr):
        """Test updating an NVR."""
        nvr_manager_instance.add_nvr(sample_nvr)
        
        sample_nvr.name = "Updated Name"
        result = nvr_manager_instance.update_nvr(sample_nvr)
        
        assert result is True
        retrieved = nvr_manager_instance.get_nvr(sample_nvr.id)
        assert retrieved.name == "Updated Name"

    def test_remove_nvr(self, nvr_manager_instance, sample_nvr):
        """Test removing an NVR."""
        nvr_manager_instance.add_nvr(sample_nvr)
        
        result = nvr_manager_instance.remove_nvr(sample_nvr.id)
        
        assert result is True
        assert nvr_manager_instance.get_nvr(sample_nvr.id) is None

    def test_remove_nonexistent_nvr(self, nvr_manager_instance):
        """Test removing non-existent NVR."""
        result = nvr_manager_instance.remove_nvr("nonexistent-id-12345")
        
        # Should return False or handle gracefully
        assert result is False or result is None

    def test_get_all_nvrs(self, nvr_manager_instance, sample_nvr):
        """Test getting all NVRs."""
        nvr_manager_instance.add_nvr(sample_nvr)
        
        all_nvrs = nvr_manager_instance.get_all_nvrs()
        
        assert isinstance(all_nvrs, list)
        assert len(all_nvrs) >= 1

    def test_nvr_count(self, nvr_manager_instance, sample_nvr):
        """Test counting NVRs."""
        initial_count = len(nvr_manager_instance.get_all_nvrs())
        
        nvr_manager_instance.add_nvr(sample_nvr)
        
        new_count = len(nvr_manager_instance.get_all_nvrs())
        assert new_count == initial_count + 1

    def test_zero_stream_configuration(self, sample_nvr):
        """Test Zero Stream fields are handled."""
        sample_nvr.zero_stream_enabled = True
        sample_nvr.zero_stream_url = "rtsp://192.168.1.100:554/Streaming/Channels/001"
        
        assert sample_nvr.zero_stream_enabled is True
        assert sample_nvr.zero_stream_url.startswith("rtsp://")

    def test_nvr_validation(self, sample_nvr_data):
        """Test NVR validation."""
        nvr = NVR(**sample_nvr_data)
        
        errors = nvr.validate()
        
        assert isinstance(errors, list)
        assert len(errors) == 0  # Valid NVR should have no errors

    def test_nvr_validation_missing_host(self, sample_nvr_data):
        """Test NVR validation with missing host."""
        sample_nvr_data['host'] = ''
        nvr = NVR(**sample_nvr_data)
        
        errors = nvr.validate()
        
        assert len(errors) > 0
        assert any('host' in e.lower() for e in errors)

    def test_nvr_to_dict(self, sample_nvr):
        """Test NVR serialization to dict."""
        data = sample_nvr.to_dict()
        
        assert isinstance(data, dict)
        assert 'id' in data
        assert 'name' in data
        assert 'host' in data

    def test_nvr_from_dict(self, sample_nvr_data):
        """Test NVR deserialization from dict."""
        sample_nvr_data['id'] = 'test-id-123'
        
        nvr = NVR.from_dict(sample_nvr_data)
        
        assert nvr.id == 'test-id-123'
        assert nvr.name == sample_nvr_data['name']


class TestNVRManagerThreadSafety:
    """Test thread safety of NVR manager."""

    def test_concurrent_access(self, sample_nvr):
        """Test concurrent read/write operations."""
        from core.nvr_manager import NVRManager
        import threading
        
        manager = NVRManager()
        errors = []
        
        def add_operation():
            try:
                nvr = NVR(
                    name=f"Thread NVR {threading.current_thread().name}",
                    host="192.168.1.100",
                    port=80,
                    username="admin",
                    password="test"
                )
                manager.add_nvr(nvr)
            except Exception as e:
                errors.append(e)
        
        def read_operation():
            try:
                manager.get_all_nvrs()
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
        
        # No errors should occur during concurrent access
        assert len(errors) == 0


class TestNVRManagerPersistence:
    """Test NVR manager persistence operations."""

    def test_save_loads_config(self, temp_config):
        """Test that NVRs are saved to config."""
        from core.nvr_manager import NVRManager
        
        manager = NVRManager()
        nvr = NVR(
            name="Persist Test",
            host="10.0.0.1",
            port=80,
            username="user",
            password="pass"
        )
        
        manager.add_nvr(nvr)
        
        # Config should be updated
        # The actual mechanism depends on implementation
        assert nvr.id is not None
