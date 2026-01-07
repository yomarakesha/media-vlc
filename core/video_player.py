"""
MediaMTX VMS Client v2.0 - Qt Multimedia Video Player
GPU-accelerated video player using QMediaPlayer for hardware decoding.
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from models.camera import Camera
from models.stream import StreamStatus
from utils.logger import logger


class VideoPlayer(QObject):
    """
    Qt Multimedia-based video player with hardware acceleration.
    
    Wraps QMediaPlayer to provide VMS-specific functionality:
    - Stream URL management (main/sub-stream switching)
    - Status tracking and error handling
    - Automatic hardware acceleration via Qt backends
    
    Signals:
        status_changed: Emitted when player status changes
        error_occurred: Emitted when an error occurs
        stream_started: Emitted when stream playback begins
        stream_stopped: Emitted when stream playback stops
    """
    
    # Signals
    status_changed = pyqtSignal(StreamStatus)
    error_occurred = pyqtSignal(str)
    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize video player.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Player components
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._video_widget: Optional[QVideoWidget] = None
        
        # Configure player
        self._player.setAudioOutput(self._audio_output)
        
        # Camera and stream info
        self._camera: Optional[Camera] = None
        self._current_url: str = ""
        self._current_quality: str = "auto"
        
        # Status tracking
        self._status = StreamStatus.IDLE
        
        # Connect signals
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        logger.debug("VideoPlayer initialized")
    
    def set_video_output(self, video_widget: QVideoWidget) -> None:
        """
        Set video output widget.
        
        Args:
            video_widget: QVideoWidget to render video
        """
        self._video_widget = video_widget
        self._player.setVideoOutput(video_widget)
        logger.debug("Video output widget set")
    
    def set_camera(self, camera: Optional[Camera]) -> None:
        """
        Set camera for playback.
        
        Args:
            camera: Camera object or None to clear
        """
        # Stop current playback
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.stop()
        
        self._camera = camera
        
        if camera:
            logger.info(f"Camera set: {camera.name} (ID: {camera.id[:8]})")
        else:
            logger.info("Camera cleared")
    
    def get_camera(self) -> Optional[Camera]:
        """
        Get current camera.
        
        Returns:
            Camera object or None
        """
        return self._camera
    
    def play(self, quality: str = "auto", widget_size: Optional[tuple] = None) -> None:
        """
        Start stream playback.
        
        Args:
            quality: Stream quality ("auto", "high", "low")
            widget_size: Optional (width, height) for auto quality selection
        """
        if not self._camera:
            logger.warning("Cannot play: No camera set")
            return
        
        # Get appropriate stream URL
        stream_url = self._camera.get_stream_url(quality, widget_size)
        
        if not stream_url:
            error_msg = f"No stream URL available for camera {self._camera.name}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return
        
        # Check if URL changed
        if stream_url != self._current_url:
            self._current_url = stream_url
            self._current_quality = quality
            
            # Set media source
            media_url = QUrl(stream_url)
            self._player.setSource(media_url)
            
            logger.info(f"Playing stream: {stream_url} (quality: {quality})")
        
        # Start playback
        self._player.play()
        self._set_status(StreamStatus.CONNECTING)
    
    def stop(self) -> None:
        """Stop stream playback."""
        self._player.stop()
        self._current_url = ""
        self._set_status(StreamStatus.IDLE)
        logger.debug("Playback stopped")
    
    def pause(self) -> None:
        """Pause stream playback."""
        self._player.pause()
        logger.debug("Playback paused")
    
    def switch_quality(self, quality: str, widget_size: Optional[tuple] = None) -> None:
        """
        Switch stream quality on the fly.
        
        Args:
            quality: New quality setting ("auto", "high", "low")
            widget_size: Optional widget size for auto quality
        """
        if not self._camera:
            return
        
        # Get new URL
        new_url = self._camera.get_stream_url(quality, widget_size)
        
        # Only switch if URL actually changed
        if new_url != self._current_url:
            logger.info(f"Switching quality from {self._current_quality} to {quality}")
            
            # Save current playback state
            was_playing = self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            
            # Stop current stream
            self.stop()
            
            # Start new stream if we were playing
            if was_playing:
                self.play(quality, widget_size)
    
    def get_status(self) -> StreamStatus:
        """
        Get current stream status.
        
        Returns:
            Current StreamStatus
        """
        return self._status
    
    def is_playing(self) -> bool:
        """
        Check if currently playing.
        
        Returns:
            True if playing
        """
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    
    def set_volume(self, volume: float) -> None:
        """
        Set audio volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self._audio_output.setVolume(volume)
    
    def get_volume(self) -> float:
        """
        Get current audio volume.
        
        Returns:
            Volume level (0.0 to 1.0)
        """
        return self._audio_output.volume()
    
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """
        Handle playback state changes.
        
        Args:
            state: New playback state
        """
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._set_status(StreamStatus.CONNECTED)
            self.stream_started.emit()
            logger.debug("Playback started")
        
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._set_status(StreamStatus.IDLE)
            self.stream_stopped.emit()
            logger.debug("Playback stopped")
        
        elif state == QMediaPlayer.PlaybackState.PausedState:
            logger.debug("Playback paused")
    
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """
        Handle media status changes.
        
        Args:
            status: New media status
        """
        if status == QMediaPlayer.MediaStatus.LoadingMedia:
            self._set_status(StreamStatus.CONNECTING)
            logger.debug("Loading media...")
        
        elif status == QMediaPlayer.MediaStatus.LoadedMedia:
            logger.debug("Media loaded")
        
        elif status == QMediaPlayer.MediaStatus.BufferingMedia:
            logger.debug("Buffering...")
        
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            logger.debug("Buffered")
        
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            logger.debug("End of media reached")
            # For live streams, this shouldn't happen often
            # Try to reconnect
            if self._camera:
                logger.info("Stream ended, attempting reconnect...")
                self.play(self._current_quality)
        
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            error_msg = "Invalid media format or URL"
            logger.error(error_msg)
            self._set_status(StreamStatus.ERROR)
            self.error_occurred.emit(error_msg)
    
    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """
        Handle player errors.
        
        Args:
            error: Error code
            error_string: Error description
        """
        self._set_status(StreamStatus.ERROR)
        
        error_msg = f"Player error: {error_string}"
        logger.error(f"{error_msg} (Code: {error})")
        
        # Provide user-friendly error messages
        if error == QMediaPlayer.Error.ResourceError:
            error_msg = f"Cannot access stream: {self._current_url}"
        elif error == QMediaPlayer.Error.FormatError:
            error_msg = "Unsupported video format"
        elif error == QMediaPlayer.Error.NetworkError:
            error_msg = "Network connection failed"
        
        self.error_occurred.emit(error_msg)
    
    def _set_status(self, status: StreamStatus) -> None:
        """
        Set and emit status change.
        
        Args:
            status: New stream status
        """
        if self._status != status:
            self._status = status
            self.status_changed.emit(status)
            logger.debug(f"Status changed to: {status.value}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop()
        
        if self._player:
            self._player.setVideoOutput(None)
            self._player.setAudioOutput(None)
        
        logger.debug("VideoPlayer cleaned up")
