"""
MediaMTX VMS Client v2.0 - Device Discovery
ONVIF WS-Discovery and MediaMTX server discovery.
"""

import socket
import struct
import threading
import requests
import os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal
from onvif import ONVIFCamera

from utils.logger import logger


@dataclass
class DiscoveredDevice:
    """Represents a discovered device."""
    device_type: str  # "ONVIF", "MediaMTX"
    name: str
    address: str
    port: int
    manufacturer: str = ""
    model: str = ""
    hardware_id: str = ""
    scopes: List[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []


class ONVIFDiscovery:
    """
    ONVIF device discovery using WS-Discovery protocol.
    Sends multicast probe and collects responses.
    """
    
    MULTICAST_ADDRESS = "239.255.255.250"
    MULTICAST_PORT = 3702
    
    WS_DISCOVERY_PROBE = '''<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
    <e:Header>
        <w:MessageID>uuid:NetworkVideoTransmitter</w:MessageID>
        <w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
        <w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
    </e:Header>
    <e:Body>
        <d:Probe>
            <d:Types>dn:NetworkVideoTransmitter</d:Types>
        </d:Probe>
    </e:Body>
</e:Envelope>'''
    
    def __init__(self, timeout: float = 5.0):
        """
        Initialize ONVIF discovery.
        
        Args:
            timeout: Discovery timeout in seconds
        """
        self.timeout = timeout
        self._devices: List[DiscoveredDevice] = []
    
    def discover(self) -> List[DiscoveredDevice]:
        """
        Perform ONVIF device discovery.
        
        Returns:
            List of discovered ONVIF devices
        """
        self._devices = []
        
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
            sock.settimeout(self.timeout)
            
            # Send discovery probe
            logger.info("Sending ONVIF WS-Discovery probe...")
            sock.sendto(
                self.WS_DISCOVERY_PROBE.encode('utf-8'),
                (self.MULTICAST_ADDRESS, self.MULTICAST_PORT)
            )
            
            # Collect responses
            start_time = socket.getdefaulttimeout()
            
            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                    self._parse_response(data.decode('utf-8'), addr)
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"Error receiving response: {e}")
                    continue
            
            sock.close()
            
        except Exception as e:
            logger.error(f"ONVIF discovery error: {e}")
        
        logger.info(f"ONVIF discovery complete. Found {len(self._devices)} devices.")
        return self._devices
    
    def _parse_response(self, response: str, addr: tuple) -> None:
        """
        Parse WS-Discovery response.
        
        Args:
            response: XML response string
            addr: Source address tuple (ip, port)
        """
        try:
            import re
            
            # Extract XAddrs (service addresses)
            xaddrs_match = re.search(r'<[^:]*:XAddrs>([^<]+)</[^:]*:XAddrs>', response)
            if not xaddrs_match:
                return
            
            xaddrs = xaddrs_match.group(1).split()
            
            # Extract scopes
            scopes = []
            scopes_match = re.search(r'<[^:]*:Scopes>([^<]+)</[^:]*:Scopes>', response)
            if scopes_match:
                scopes = scopes_match.group(1).split()
            
            # Parse scope information
            name = ""
            manufacturer = ""
            model = ""
            hardware_id = ""
            
            for scope in scopes:
                if "name/" in scope.lower():
                    name = scope.split("/")[-1]
                elif "hardware/" in scope.lower():
                    hardware_id = scope.split("/")[-1]
                elif "manufacturer/" in scope.lower() or "mfr/" in scope.lower():
                    manufacturer = scope.split("/")[-1]
                elif "model/" in scope.lower():
                    model = scope.split("/")[-1]
            
            # Create device for each XAddr
            for xaddr in xaddrs:
                # Parse address
                match = re.match(r'https?://([^:/]+):?(\d+)?', xaddr)
                if match:
                    ip = match.group(1)
                    port = int(match.group(2)) if match.group(2) else 80
                    
                    # Check if already discovered
                    if any(d.address == ip and d.port == port for d in self._devices):
                        continue
                    
                    device = DiscoveredDevice(
                        device_type="ONVIF",
                        name=name or f"ONVIF Device ({ip})",
                        address=ip,
                        port=port,
                        manufacturer=manufacturer,
                        model=model,
                        hardware_id=hardware_id,
                        scopes=scopes
                    )
                    
                    self._devices.append(device)
                    logger.info(f"Discovered ONVIF device: {device.name} at {ip}:{port}")
        
        except Exception as e:
            logger.debug(f"Failed to parse discovery response: {e}")


class MediaMTXDiscovery:
    """
    MediaMTX server discovery.
    Probes known ports for MediaMTX API.
    """
    
    DEFAULT_PORTS = [8554, 8888, 9997]  # RTSP, HLS, API
    API_PORT = 9997
    
    def __init__(self, network_prefix: str = "192.168.1", timeout: float = 1.0):
        """
        Initialize MediaMTX discovery.
        
        Args:
            network_prefix: Network prefix to scan (e.g., "192.168.1")
            timeout: Connection timeout per host
        """
        self.network_prefix = network_prefix
        self.timeout = timeout
        self._devices: List[DiscoveredDevice] = []

    def _get_local_network_prefix(self) -> str:
        """
        Get local network prefix (e.g. '192.168.1').
        
        Returns:
            Network prefix string
        """
        try:
            # Create a dummy socket to find local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Return first 3 octets
            return ".".join(local_ip.split(".")[:3])
        except Exception:
            return "192.168.1"
    
    def discover(self, hosts: List[str] = None, scan_subnet: bool = False) -> List[DiscoveredDevice]:
        """
        Discover MediaMTX servers using parallel probing.
        
        Args:
            hosts: List of specific hosts to probe
            scan_subnet: Whether to scan the local subnet
            
        Returns:
            List of discovered MediaMTX servers
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self._devices = []
        
        # Prepare list of hosts to scan
        hosts_to_scan = set()
        
        # Add specific hosts
        if hosts:
            for host in hosts:
                hosts_to_scan.add(host)
        
        # Add localhost defaults always
        hosts_to_scan.add("localhost")
        hosts_to_scan.add("127.0.0.1")
        
        # Add subnet hosts if enabled
        if scan_subnet:
            prefix = self._get_local_network_prefix()
            logger.info(f"Scanning subnet {prefix}.0/24...")
            for i in range(1, 255):
                hosts_to_scan.add(f"{prefix}.{i}")
        
        # Convert to list
        final_hosts = list(hosts_to_scan)
        
        logger.info(f"Scanning for MediaMTX servers ({len(final_hosts)} hosts) using parallel probing...")
        
        # Use ThreadPoolExecutor for parallel probing (HUGE performance improvement)
        max_workers = min(50, len(final_hosts))  # Cap at 50 threads
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._probe_host, host): host for host in final_hosts}
            
            for future in as_completed(futures):
                try:
                    future.result()  # Get result to trigger any exceptions
                except Exception as e:
                    logger.debug(f"Probe failed: {e}")
        
        logger.info(f"MediaMTX discovery complete. Found {len(self._devices)} servers.")
        return self._devices
    
    def discover_single(self, host: str) -> Optional[DiscoveredDevice]:
        """
        Probe a single host for MediaMTX.
        
        Args:
            host: Host to probe
            
        Returns:
            DiscoveredDevice or None
        """
        try:
            return self._probe_host(host)
        except Exception as e:
            logger.debug(f"Failed to probe {host}: {e}")
            return None
    
    def _probe_host(self, host: str) -> Optional[DiscoveredDevice]:
        """
        Probe a host for MediaMTX API.
        
        Args:
            host: Host to probe
            
        Returns:
            DiscoveredDevice if found, None otherwise
        """
        # Try API endpoint
        api_url = f"http://{host}:{self.API_PORT}/v3/config/global/get"
        
        try:
            response = requests.get(api_url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                device = DiscoveredDevice(
                    device_type="MediaMTX",
                    name=f"MediaMTX Server ({host})",
                    address=host,
                    port=self.API_PORT,
                    manufacturer="MediaMTX",
                    model="MediaMTX Server"
                )
                
                self._devices.append(device)
                logger.info(f"Discovered MediaMTX server at {host}:{self.API_PORT}")
                return device
        
        except requests.exceptions.RequestException:
            pass
        
        # Try RTSP port (basic connectivity check)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, 8554))
            sock.close()
            
            if result == 0:
                device = DiscoveredDevice(
                    device_type="MediaMTX",
                    name=f"RTSP Server ({host})",
                    address=host,
                    port=8554,
                    manufacturer="Unknown",
                    model="RTSP Server"
                )
                
                # Check if already added via API
                if not any(d.address == host for d in self._devices):
                    self._devices.append(device)
                    logger.info(f"Discovered RTSP server at {host}:8554")
                    return device
        
        except socket.error:
            pass
        
        return None


        return None


def get_onvif_stream_uri(ip: str, port: int, username: str, password: str) -> Optional[str]:
    """
    Connect to ONVIF device and retrieve RTSP stream URI.
    
    Args:
        ip: Device IP address
        port: Device port (usually 80)
        username: Username
        password: Password
        
    Returns:
        RTSP URL or None if failed
    """
    try:
        # Connect to camera
        # Note: We might need to handle wsdl_dir if not found automatically
        mycam = ONVIFCamera(ip, port, username, password)
        
        # Create media service
        media = mycam.create_media_service()
        
        # Get profiles
        profiles = media.GetProfiles()
        if not profiles:
            logger.error(f"No profiles found for ONVIF device at {ip}")
            return None
            
        # Use first profile
        profile_token = profiles[0].token
        
        # Get stream URI
        # info = media.GetStreamUri({'StreamSetup': {'Stream': 'ONVIF-Media-Stream-URI'}, 'ProfileToken': profile_token})
        # The argument structure depends on zeep version, but usually:
        req = {
            'StreamSetup': {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'
                }
            },
            'ProfileToken': profile_token
        }
        
        res = media.GetStreamUri(req)
        return res.Uri
        
    except Exception as e:
        logger.error(f"Failed to get ONVIF stream URI for {ip}: {e}")
        return None


class DiscoveryThread(QThread):
    """
    Background thread for device discovery.
    Emits signals for progress and results.
    """
    
    # Signals
    device_found = pyqtSignal(object)  # DiscoveredDevice
    progress = pyqtSignal(int, str)  # percentage, message
    finished = pyqtSignal(list)  # List of all devices
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, discover_onvif: bool = True, discover_mediamtx: bool = True,
                 mediamtx_hosts: List[str] = None, scan_subnet: bool = False):
        """
        Initialize discovery thread.
        
        Args:
            discover_onvif: Enable ONVIF discovery
            discover_mediamtx: Enable MediaMTX discovery
            mediamtx_hosts: Optional list of hosts to probe for MediaMTX
            scan_subnet: Whether to scan the local subnet for MediaMTX
        """
        super().__init__()
        
        self.discover_onvif = discover_onvif
        self.discover_mediamtx = discover_mediamtx
        self.mediamtx_hosts = mediamtx_hosts or []
        self.scan_subnet = scan_subnet
        
        self._devices: List[DiscoveredDevice] = []
        self._cancelled = False
    
    def run(self) -> None:
        """Run discovery in background."""
        self._devices = []
        
        try:
            total_steps = (1 if self.discover_onvif else 0) + (1 if self.discover_mediamtx else 0)
            current_step = 0
            
            # ONVIF Discovery
            if self.discover_onvif and not self._cancelled:
                self.progress.emit(int((current_step / total_steps) * 100), "Discovering ONVIF devices...")
                
                onvif = ONVIFDiscovery(timeout=3.0)
                onvif_devices = onvif.discover()
                
                for device in onvif_devices:
                    self._devices.append(device)
                    self.device_found.emit(device)
                
                current_step += 1
            
            # MediaMTX Discovery
            if self.discover_mediamtx and not self._cancelled:
                self.progress.emit(int((current_step / total_steps) * 100), "Discovering MediaMTX servers...")
                
                mediamtx = MediaMTXDiscovery(timeout=0.5)  # Fast timeout for network scan
                mediamtx_devices = mediamtx.discover(self.mediamtx_hosts, self.scan_subnet)
                
                for device in mediamtx_devices:
                    self._devices.append(device)
                    self.device_found.emit(device)
                
                current_step += 1
            
            self.progress.emit(100, f"Discovery complete. Found {len(self._devices)} devices.")
            self.finished.emit(self._devices)
        
        except Exception as e:
            logger.error(f"Discovery error: {e}")
            self.error.emit(str(e))
    
    def cancel(self) -> None:
        """Cancel discovery."""
        self._cancelled = True
