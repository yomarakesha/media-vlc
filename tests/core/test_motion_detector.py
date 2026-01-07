"""Tests for MotionDetector class."""

import pytest
import numpy as np
import cv2
from core.motion_detector import MotionDetector, DetectionZone


class TestDetectionZone:
    """Test DetectionZone dataclass."""
    
    def test_zone_creation(self):
        """Test zone creation with default values."""
        zone = DetectionZone(x=0.1, y=0.1, width=0.5, height=0.5)
        
        assert zone.x == 0.1
        assert zone.y == 0.1
        assert zone.width == 0.5
        assert zone.height == 0.5
        assert zone.enabled is True
        assert zone.name == "Zone"
    
    def test_zone_to_dict(self):
        """Test zone serialization."""
        zone = DetectionZone(x=0.2, y=0.3, width=0.4, height=0.5, name="Test Zone")
        data = zone.to_dict()
        
        assert data['x'] == 0.2
        assert data['y'] == 0.3
        assert data['width'] == 0.4
        assert data['height'] == 0.5
        assert data['name'] == "Test Zone"
    
    def test_zone_from_dict(self):
        """Test zone deserialization."""
        data = {
            'x': 0.1,
            'y': 0.2,
            'width': 0.3,
            'height': 0.4,
            'enabled': False,
            'name': "Custom"
        }
        zone = DetectionZone.from_dict(data)
        
        assert zone.x == 0.1
        assert zone.enabled is False
        assert zone.name == "Custom"
    
    def test_get_absolute_rect(self):
        """Test conversion to absolute coordinates."""
        zone = DetectionZone(x=0.5, y=0.5, width=0.25, height=0.25)
        x, y, w, h = zone.get_absolute_rect(1920, 1080)
        
        assert x == 960
        assert y == 540
        assert w == 480
        assert h == 270


class TestMotionDetector:
    """Test MotionDetector class."""
    
    def test_detector_initialization(self):
        """Test detector creation."""
        detector = MotionDetector(sensitivity=30, min_area=500)
        
        assert detector._sensitivity == 30
        assert detector._min_area == 500
        assert len(detector._zones) == 0
    
    def test_detect_no_motion(self):
        """Test detection with static frames."""
        detector = MotionDetector()
        
        # Create static frame
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # First frame initializes background
        detector.detect(frame1)
        
        # Second identical frame should detect no motion
        motion, regions = detector.detect(frame2)
        
        assert motion is False
        assert len(regions) == 0
    
    def test_detect_with_motion(self):
        """Test detection with moving object."""
        detector = MotionDetector(min_area=100)
        
        # Black frame
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        detector.detect(frame1)
        
        # Allow background to settle
        for _ in range(10):
            detector.detect(frame1)
        
        # Frame with white rectangle (simulating motion)
        frame2 = frame1.copy()
        cv2.rectangle(frame2, (100, 100), (200, 200), (255, 255, 255), -1)
        
        motion, regions = detector.detect(frame2)
        
        assert motion is True
        assert len(regions) > 0
    
    def test_min_area_filtering(self):
        """Test minimum area threshold."""
        detector = MotionDetector(min_area=5000)  # Large threshold
        
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(10):
            detector.detect(frame1)
        
        # Small object (50x50 = 2500 pixels)
        frame2 = frame1.copy()
        cv2.rectangle(frame2, (100, 100), (150, 150), (255, 255, 255), -1)
        
        motion, regions = detector.detect(frame2)
        
        # Should not detect due to min_area threshold
        assert motion is False
    
    def test_zone_management(self):
        """Test adding/removing zones."""
        detector = MotionDetector()
        
        zone1 = DetectionZone(x=0.0, y=0.0, width=0.5, height=0.5, name="Zone 1")
        zone2 = DetectionZone(x=0.5, y=0.5, width=0.5, height=0.5, name="Zone 2")
        
        detector.add_zone(zone1)
        detector.add_zone(zone2)
        
        assert len(detector.get_zones()) == 2
        
        detector.remove_zone(0)
        assert len(detector.get_zones()) == 1
        
        detector.clear_zones()
        assert len(detector.get_zones()) == 0
    
    def test_sensitivity_update(self):
        """Test sensitivity adjustment."""
        detector = MotionDetector(sensitivity=30)
        
        assert detector._sensitivity == 30
        
        detector.set_sensitivity(50)
        assert detector._sensitivity == 50
    
    def test_statistics(self):
        """Test statistics collection."""
        detector = MotionDetector()
        
        stats = detector.get_statistics()
        
        assert 'total_detections' in stats
        assert 'zones_count' in stats
        assert stats['sensitivity'] == 30
    
    def test_reset(self):
        """Test detector reset."""
        detector = MotionDetector()
        detector._total_detections = 100
        
        detector.reset()
        
        stats = detector.get_statistics()
        assert stats['total_detections'] == 0
    
    def test_draw_zones(self):
        """Test zone visualization."""
        detector = MotionDetector()
        zone = DetectionZone(x=0.25, y=0.25, width=0.5, height=0.5, name="Test")
        detector.add_zone(zone)
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.draw_zones(frame)
        
        # Check that frame was modified (has drawn zone)
        assert not np.array_equal(frame, result)
    
    def test_draw_motion_regions(self):
        """Test motion region visualization."""
        detector = MotionDetector()
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        regions = [(100, 100, 50, 50), (200, 200, 75, 75)]
        
        result = detector.draw_motion_regions(frame, regions)
        
        # Check that frame was modified
        assert not np.array_equal(frame, result)
