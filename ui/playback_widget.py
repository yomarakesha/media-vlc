"""
MediaMTX VMS Client v2.0 - Playback Widget
Widget for browsing and playing back recorded video files.
"""

import os
import cv2
import time
import numpy as np
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QSlider, QStyle, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QMutex, QTimer
from PyQt6.QtGui import QImage, QPixmap, QIcon

from utils.logger import logger
from utils.config import config


class VideoPlayerThread(QThread):
    """Thread for playing video files."""
    frame_ready = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    position_changed = pyqtSignal(int)  # Current frame index
    duration_changed = pyqtSignal(int)  # Total frames
    
    def __init__(self):
        super().__init__()
        self._filename = None
        self._running = False
        self._paused = False
        self._cap = None
        self._mutex = QMutex()
        self._seek_requested = -1
        
    def load_file(self, filename: str) -> bool:
        """Load a video file."""
        self._filename = filename
        self._cap = cv2.VideoCapture(filename)
        if not self._cap.isOpened():
            return False
            
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_changed.emit(total_frames)
        return True
        
    def play(self):
        """Start or resume playback."""
        self._running = True
        self._paused = False
        if not self.isRunning():
            self.start()
            
    def pause(self):
        """Pause playback."""
        self._paused = True
        
    def stop(self):
        """Stop playback."""
        self._running = False
        self.wait()
        
    def seek(self, frame_index: int):
        """Seek to specific frame."""
        self._seek_requested = frame_index
        
    def run(self):
        """Main playback loop."""
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 25
        interval = 1.0 / fps
        
        while self._running and self._cap.isOpened():
            if self._seek_requested >= 0:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._seek_requested)
                self._seek_requested = -1
            
            if self._paused:
                time.sleep(0.1)
                continue
                
            start_time = time.time()
            
            ret, frame = self._cap.read()
            if not ret:
                break
                
            self.frame_ready.emit(frame)
            
            current_frame = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.position_changed.emit(current_frame)
            
            # Maintain FPS
            elapsed = time.time() - start_time
            delay = max(0, interval - elapsed)
            time.sleep(delay)
            
        self.finished.emit()
        self._running = False


class PlaybackWidget(QWidget):
    """
    Widget for playback interface.
    Contains file browser and video player.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player_thread = VideoPlayerThread()
        self._player_thread.frame_ready.connect(self._update_frame)
        self._player_thread.position_changed.connect(self._on_position_changed)
        self._player_thread.duration_changed.connect(self._on_duration_changed)
        self._player_thread.finished.connect(self._on_playback_finished)
        
        self._init_ui()
        self._refresh_file_list()
        
    def _init_ui(self):
        """Initialize user interface."""
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # File Browser (Left)
        browser_group = QGroupBox("Recordings")
        browser_layout = QVBoxLayout(browser_group)
        
        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderLabels(["Date / Camera", "File"])
        self._file_tree.itemDoubleClicked.connect(self._on_file_selected)
        browser_layout.addWidget(self._file_tree)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self._refresh_file_list)
        browser_layout.addWidget(refresh_btn)
        
        splitter.addWidget(browser_group)
        
        # Video Player (Right)
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video Display
        self._video_label = QLabel()
        self._video_label.setStyleSheet("background-color: black; border: 1px solid #444;")
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setMinimumSize(640, 360)
        self._video_label.setSizePolicy(
            self._video_label.sizePolicy().Policy.Expanding,
            self._video_label.sizePolicy().Policy.Expanding
        )
        player_layout.addWidget(self._video_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self._play_btn = QPushButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_btn.clicked.connect(self._toggle_playback)
        self._play_btn.setEnabled(False)
        controls_layout.addWidget(self._play_btn)
        
        self._stop_btn = QPushButton()
        self._stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._stop_btn.clicked.connect(self._stop_playback)
        self._stop_btn.setEnabled(False)
        controls_layout.addWidget(self._stop_btn)
        
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setEnabled(False)
        self._slider.sliderMoved.connect(self._seek_video)
        controls_layout.addWidget(self._slider)
        
        self._time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self._time_label)
        
        player_layout.addLayout(controls_layout)
        splitter.addWidget(player_container)
        
        # Set splitter ratio
        splitter.setStretchFactor(1, 4)
        
    def _refresh_file_list(self):
        """Scan recordings directory and populate tree."""
        self._file_tree.clear()
        
        recordings_dir = "recordings"
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)
            return
            
        # Group by Date -> Camera
        # Files are named: CameraName_YYYYMMDD_HHMMSS.mp4
        
        files_map = {}  # Date -> Camera -> [files]
        
        try:
            for filename in os.listdir(recordings_dir):
                if not filename.endswith(".mp4"):
                    continue
                    
                path = os.path.join(recordings_dir, filename)
                
                # Parse filename
                # Expected: Name_20251208_120000.mp4
                parts = filename.rsplit('_', 2)
                if len(parts) < 3:
                    continue
                    
                name = parts[0]
                date_str = parts[1] # YYYYMMDD
                
                try:
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    display_date = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    display_date = "Unknown Date"
                    
                if display_date not in files_map:
                    files_map[display_date] = {}
                if name not in files_map[display_date]:
                    files_map[display_date][name] = []
                    
                files_map[display_date][name].append({
                    'path': path,
                    'filename': filename,
                    'time': parts[2].replace('.mp4', '')
                })
                
            # Build Tree
            for date_key in sorted(files_map.keys(), reverse=True):
                date_item = QTreeWidgetItem(self._file_tree)
                date_item.setText(0, date_key)
                
                cameras = files_map[date_key]
                for cam_name in sorted(cameras.keys()):
                    cam_item = QTreeWidgetItem(date_item)
                    cam_item.setText(0, cam_name)
                    
                    for file_data in sorted(cameras[cam_name], key=lambda x: x['time']):
                        file_item = QTreeWidgetItem(cam_item)
                        # Format time: HHMMSS -> HH:MM:SS
                        time_str = file_data['time']
                        formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                        
                        file_item.setText(0, formatted_time)
                        file_item.setText(1, file_data['filename'])
                        file_item.setData(0, Qt.ItemDataRole.UserRole, file_data['path'])
                        
            self._file_tree.expandAll()
            
        except Exception as e:
            logger.error(f"Error checking recordings: {e}")
            
    def _on_file_selected(self, item: QTreeWidgetItem, column: int):
        """Handle file selection."""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            return
            
        if self._player_thread.isRunning():
            self._player_thread.stop()
            
        if self._player_thread.load_file(file_path):
            self._play_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
            self._slider.setEnabled(True)
            self._toggle_playback() # Auto play
        else:
            QMessageBox.warning(self, "Error", "Failed to load video file.")

    def _toggle_playback(self):
        """Play or Pause video."""
        if self._player_thread._paused or not self._player_thread.isRunning():
            self._player_thread.play()
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self._player_thread.pause()
            self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            
    def _stop_playback(self):
        """Stop playback."""
        self._player_thread.stop()
        self._video_label.clear()
        self._video_label.setText("Stopped")
        self._slider.setValue(0)
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        
    def _seek_video(self, position: int):
        """Seek video."""
        self._player_thread.seek(position)
        
    def _update_frame(self, frame: np.ndarray):
        """Update video display."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        scaled_pixmap = pixmap.scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._video_label.setPixmap(scaled_pixmap)
        
    def _on_position_changed(self, frame_index: int):
        """Update slider position."""
        if not self._slider.isSliderDown():
            self._slider.setValue(frame_index)
            
    def _on_duration_changed(self, total_frames: int):
        """Update slider range."""
        self._slider.setRange(0, total_frames)
        
    def _on_playback_finished(self):
        """Handle playback end."""
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        
    def closeEvent(self, event):
        """Cleanup."""
        self._player_thread.stop()
        super().closeEvent(event)
