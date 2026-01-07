"""
MediaMTX VMS Client v2.0 - Advanced Motion Detector
MOG2-based motion detection with configurable zones and improved accuracy.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class DetectionZone:
    """
    Rectangular detection zone.
    
    Attributes:
        x: Top-left X coordinate (0-1, relative to frame width)
        y: Top-left Y coordinate (0-1, relative to frame height)
        width: Zone width (0-1, relative to frame width)
        height: Zone height (0-1, relative to frame height)
        enabled: Whether zone is active
        name: Zone name
    """
    x: float
    y: float
    width: float
    height: float
    enabled: bool = True
    name: str = "Zone"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'enabled': self.enabled,
            'name': self.name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DetectionZone':
        """Create from dictionary."""
        return cls(**data)
    
    def get_absolute_rect(self, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """
        Get absolute pixel coordinates.
        
        Args:
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            
        Returns:
            Tuple of (x, y, width, height) in pixels
        """
        x = int(self.x * frame_width)
        y = int(self.y * frame_height)
        w = int(self.width * frame_width)
        h = int(self.height * frame_height)
        return (x, y, w, h)


class MotionDetector:
    """
    Advanced motion detector using MOG2 background subtraction.
    
    Features:
    - Adaptive background modeling (handles lighting changes)
    - Shadow detection and removal
    - Configurable detection zones
    - Minimum motion area threshold
    - Motion history tracking
    """
    
    def __init__(
        self,
        sensitivity: int = 30,
        min_area: int = 500,
        history: int = 500,
        detect_shadows: bool = True
    ):
        """
        Initialize motion detector.
        
        Args:
            sensitivity: Detection threshold (lower = more sensitive, 10-100)
            min_area: Minimum contour area in pixels
            history: Number of frames for background learning
            detect_shadows: Whether to detect and remove shadows
        """
        self._sensitivity = sensitivity
        self._min_area = min_area
        self._detect_shadows = detect_shadows
        
        # MOG2 background subtractor
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=sensitivity,
            detectShadows=detect_shadows
        )
        
        # Detection zones (empty = entire frame)
        self._zones: List[DetectionZone] = []
        
        # Morphological kernel for noise reduction
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # Statistics
        self._total_detections = 0
        self._false_positives = 0  # For testing
        
        logger.debug(f"MotionDetector initialized (sensitivity={sensitivity}, min_area={min_area})")
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]]]:
        """
        Detect motion in frame.
        
        Args:
            frame: Video frame (BGR format)
            
        Returns:
            Tuple of (motion_detected, motion_regions)
            motion_regions: List of (x, y, width, height) bounding boxes
        """
        if frame is None or frame.size == 0:
            return False, []
        
        # Apply background subtraction
        fg_mask = self._bg_subtractor.apply(frame)
        
        # Remove shadows (appear as gray in mask)
        if self._detect_shadows:
            fg_mask[fg_mask == 127] = 0
        
        # Apply morphological operations to reduce noise
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._kernel)
        
        # Find contours
        contours, _ = cv2.findContours(
            fg_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter contours by area and zones
        motion_regions = []
        frame_height, frame_width = frame.shape[:2]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by minimum area
            if area < self._min_area:
                continue
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check if in any detection zone
            if self._zones and not self._in_detection_zone(x, y, w, h, frame_width, frame_height):
                continue
            
            motion_regions.append((x, y, w, h))
        
        motion_detected = len(motion_regions) > 0
        
        if motion_detected:
            self._total_detections += 1
            logger.debug(f"Motion detected: {len(motion_regions)} region(s)")
        
        return motion_detected, motion_regions
    
    def _in_detection_zone(
        self,
        x: int, y: int, w: int, h: int,
        frame_width: int, frame_height: int
    ) -> bool:
        """
        Check if motion region intersects with any detection zone.
        
        Args:
            x, y, w, h: Motion region bounding box
            frame_width: Frame width
            frame_height: Frame height
            
        Returns:
            True if region is within at least one enabled zone
        """
        if not self._zones:
            return True  # No zones = entire frame is detection zone
        
        # Center point of motion region
        cx = x + w // 2
        cy = y + h // 2
        
        for zone in self._zones:
            if not zone.enabled:
                continue
            
            # Get zone rectangle in pixels
            zx, zy, zw, zh = zone.get_absolute_rect(frame_width, frame_height)
            
            # Check if center point is within zone
            if zx <= cx <= zx + zw and zy <= cy <= zy + zh:
                return True
        
        return False
    
    def set_zones(self, zones: List[DetectionZone]) -> None:
        """
        Set detection zones.
        
        Args:
            zones: List of DetectionZone objects
        """
        self._zones = zones
        logger.info(f"Detection zones updated: {len(zones)} zone(s)")
    
    def get_zones(self) -> List[DetectionZone]:
        """Get current detection zones."""
        return self._zones.copy()
    
    def add_zone(self, zone: DetectionZone) -> None:
        """
        Add detection zone.
        
        Args:
            zone: DetectionZone to add
        """
        self._zones.append(zone)
        logger.debug(f"Added detection zone: {zone.name}")
    
    def remove_zone(self, index: int) -> bool:
        """
        Remove detection zone by index.
        
        Args:
            index: Zone index
            
        Returns:
            True if successful
        """
        if 0 <= index < len(self._zones):
            removed = self._zones.pop(index)
            logger.debug(f"Removed detection zone: {removed.name}")
            return True
        return False
    
    def clear_zones(self) -> None:
        """Clear all detection zones."""
        self._zones.clear()
        logger.debug("Cleared all detection zones")
    
    def set_sensitivity(self, sensitivity: int) -> None:
        """
        Update detection sensitivity.
        
        Args:
            sensitivity: Threshold value (10-100, lower = more sensitive)
        """
        self._sensitivity = sensitivity
        # Recreate background subtractor with new sensitivity
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=sensitivity,
            detectShadows=self._detect_shadows
        )
        logger.info(f"Motion sensitivity updated to {sensitivity}")
    
    def set_min_area(self, min_area: int) -> None:
        """
        Update minimum motion area.
        
        Args:
            min_area: Minimum contour area in pixels
        """
        self._min_area = min_area
        logger.info(f"Minimum motion area updated to {min_area} pixels")
    
    def get_statistics(self) -> dict:
        """
        Get detection statistics.
        
        Returns:
            Dictionary with detection stats
        """
        return {
            'total_detections': self._total_detections,
            'false_positives': self._false_positives,
            'zones_count': len(self._zones),
            'sensitivity': self._sensitivity,
            'min_area': self._min_area
        }
    
    def reset(self) -> None:
        """Reset background model and statistics."""
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=self._sensitivity,
            detectShadows=self._detect_shadows
        )
        self._total_detections = 0
        self._false_positives = 0
        logger.info("Motion detector reset")
    
    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection zones on frame for visualization.
        
        Args:
            frame: Video frame
            
        Returns:
            Frame with drawn zones
        """
        if not self._zones:
            return frame
        
        frame_copy = frame.copy()
        height, width = frame.shape[:2]
        
        for i, zone in enumerate(self._zones):
            if not zone.enabled:
                continue
            
            x, y, w, h = zone.get_absolute_rect(width, height)
            
            # Draw rectangle
            color = (0, 255, 0)  # Green for active zone
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), color, 2)
            
            # Draw zone name
            cv2.putText(
                frame_copy,
                zone.name,
                (x + 5, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )
        
        return frame_copy
    
    def draw_motion_regions(
        self,
        frame: np.ndarray,
        regions: List[Tuple[int, int, int, int]]
    ) -> np.ndarray:
        """
        Draw motion regions on frame for visualization.
        
        Args:
            frame: Video frame
            regions: List of (x, y, width, height) bounding boxes
            
        Returns:
            Frame with drawn motion regions
        """
        if not regions:
            return frame
        
        frame_copy = frame.copy()
        
        for x, y, w, h in regions:
            # Draw red rectangle around motion
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 0, 255), 2)
            
            # Draw area text
            area = w * h
            cv2.putText(
                frame_copy,
                f"{area}px",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1
            )
        
        return frame_copy
