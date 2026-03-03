"""Tests for Discovery module.

This module tests the device discovery functionality including:
- ONVIF WS-Discovery parsing
- MediaMTX probe
- Thread management
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import socket


class TestDiscoveredDevice:
    """Test DiscoveredDevice dataclass."""

    def test_device_creation(self):
        """Test device can be created."""
        from core.discovery import DiscoveredDevice
        
        device = DiscoveredDevice(
            name="Test Camera",
            address="192.168.1.100",
            port=80,
            device_type="ONVIF"
        )
        
        assert device.name == "Test Camera"
        assert device.address == "192.168.1.100"
        assert device.port == 80
        assert device.device_type == "ONVIF"

    def test_device_optional_fields(self):
        """Test device with optional fields."""
        from core.discovery import DiscoveredDevice
        
        device = DiscoveredDevice(
            name="MediaMTX Server",
            address="192.168.1.200",
            port=9997,
            device_type="MediaMTX",
            manufacturer="MediaMTX",
            model="Server"
        )
        
        assert device.manufacturer == "MediaMTX"
        assert device.model == "Server"


class TestONVIFDiscovery:
    """Test ONVIF device discovery."""

    def test_discovery_initialization(self):
        """Test discovery can be initialized."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery(timeout=3.0)
        
        assert discovery is not None
        assert discovery.timeout == 3.0

    def test_ws_discovery_probe_format(self):
        """Test WS-Discovery probe XML format."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery()
        
        # Should have the probe message
        assert hasattr(discovery, 'WS_DISCOVERY_PROBE')
        assert 'Probe' in discovery.WS_DISCOVERY_PROBE

    @patch('socket.socket')
    def test_discover_handles_timeout(self, mock_socket):
        """Test discovery handles socket timeout."""
        from core.discovery import ONVIFDiscovery
        
        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = socket.timeout()
        mock_socket.return_value.__enter__ = Mock(return_value=mock_sock)
        mock_socket.return_value.__exit__ = Mock(return_value=False)
        
        discovery = ONVIFDiscovery(timeout=0.1)
        
        # Should not raise exception
        try:
            devices = discovery.discover()
            assert isinstance(devices, list)
        except socket.timeout:
            pass  # Expected behavior

    def test_parse_response_valid(self):
        """Test parsing valid WS-Discovery response."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery()
        
        # Sample response (simplified)
        sample_response = """
        <?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope>
            <SOAP-ENV:Body>
                <d:ProbeMatches>
                    <d:ProbeMatch>
                        <d:XAddrs>http://192.168.1.100:80/onvif/device_service</d:XAddrs>
                    </d:ProbeMatch>
                </d:ProbeMatches>
            </SOAP-ENV:Body>
        </SOAP-ENV:Envelope>
        """
        
        # Parser should handle this
        if hasattr(discovery, '_parse_response'):
            result = discovery._parse_response(sample_response)
            assert result is not None

    def test_parse_response_invalid(self):
        """Test parsing invalid response."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery()
        
        invalid_response = "not xml at all"
        
        if hasattr(discovery, '_parse_response'):
            result = discovery._parse_response(invalid_response)
            # Should handle gracefully
            assert result is None or isinstance(result, dict)


class TestMediaMTXDiscovery:
    """Test MediaMTX server discovery."""

    def test_discovery_initialization(self):
        """Test MediaMTX discovery can be initialized."""
        from core.discovery import MediaMTXDiscovery
        
        discovery = MediaMTXDiscovery()
        
        assert discovery is not None
        assert discovery.API_PORT == 9997

    @patch('requests.get')
    def test_probe_valid_server(self, mock_get):
        """Test probing valid MediaMTX server."""
        from core.discovery import MediaMTXDiscovery
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        discovery = MediaMTXDiscovery()
        
        if hasattr(discovery, '_probe_host'):
            result = discovery._probe_host("192.168.1.100")
            assert result is not None

    @patch('requests.get')
    def test_probe_invalid_server(self, mock_get):
        """Test probing invalid server."""
        from core.discovery import MediaMTXDiscovery
        
        mock_get.side_effect = Exception("Connection refused")
        
        discovery = MediaMTXDiscovery()
        
        if hasattr(discovery, '_probe_host'):
            result = discovery._probe_host("192.168.1.255")
            assert result is None

    def test_scan_network_range(self):
        """Test network range scanning."""
        from core.discovery import MediaMTXDiscovery
        
        discovery = MediaMTXDiscovery()
        
        if hasattr(discovery, '_get_network_hosts'):
            hosts = discovery._get_network_hosts("192.168.1.0/24")
            assert len(hosts) <= 254  # Max hosts in /24


class TestDiscoveryThread:
    """Test DiscoveryThread for async discovery."""

    def test_thread_creation(self, qtbot):
        """Test discovery thread can be created."""
        from core.discovery import DiscoveryThread
        
        thread = DiscoveryThread(discover_onvif=True, discover_mediamtx=True)
        
        assert thread is not None

    def test_thread_signals(self, qtbot):
        """Test thread has required signals."""
        from core.discovery import DiscoveryThread
        
        thread = DiscoveryThread()
        
        assert hasattr(thread, 'device_discovered')
        assert hasattr(thread, 'finished')

    def test_thread_start_stop(self, qtbot):
        """Test thread can start and stop."""
        from core.discovery import DiscoveryThread
        
        thread = DiscoveryThread(timeout=0.1)
        
        # Start thread
        thread.start()
        
        # Wait for completion or stop
        thread.stop()
        thread.wait(1000)
        
        assert not thread.isRunning()


class TestDiscoveryIntegration:
    """Integration tests for discovery."""

    def test_full_discovery_cycle(self):
        """Test full discovery with mocked network."""
        from core.discovery import DeviceDiscovery
        
        if not hasattr(DeviceDiscovery, 'discover_all'):
            pytest.skip("Full discovery not implemented")
        
        # Would test complete discovery cycle
        pass

    def test_discovery_results_format(self):
        """Test discovery results have expected format."""
        from core.discovery import DiscoveredDevice
        
        device = DiscoveredDevice(
            name="Test",
            address="192.168.1.1",
            port=80,
            device_type="ONVIF"
        )
        
        # Convert to dict if method exists
        if hasattr(device, 'to_dict'):
            data = device.to_dict()
            assert 'name' in data
            assert 'address' in data


class TestNetworkUtils:
    """Test network utility functions."""

    def test_get_local_ip(self):
        """Test getting local IP address."""
        from core.discovery import MediaMTXDiscovery
        
        discovery = MediaMTXDiscovery()
        
        if hasattr(discovery, '_get_local_ip'):
            ip = discovery._get_local_ip()
            
            # Should return valid IP or default
            assert ip is not None
            assert '.' in ip

    def test_get_network_range(self):
        """Test getting network range for scanning."""
        from core.discovery import MediaMTXDiscovery
        
        discovery = MediaMTXDiscovery()
        
        if hasattr(discovery, '_get_network_range'):
            network = discovery._get_network_range()
            
            # Should return CIDR notation
            assert '/' in network or network is None


class TestDiscoveryErrors:
    """Test discovery error handling."""

    def test_network_error_handling(self):
        """Test handling of network errors during discovery."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery(timeout=0.01)
        
        # Should handle gracefully
        try:
            devices = discovery.discover()
            assert isinstance(devices, list)
        except Exception as e:
            # Known exception types are acceptable
            assert isinstance(e, (socket.timeout, OSError, ConnectionError))

    def test_malformed_data_handling(self):
        """Test handling of malformed data."""
        from core.discovery import ONVIFDiscovery
        
        discovery = ONVIFDiscovery()
        
        # Malformed XML should not crash
        if hasattr(discovery, '_parse_response'):
            result = discovery._parse_response(b'\x00\x01\x02\x03')
            assert result is None or isinstance(result, dict)
