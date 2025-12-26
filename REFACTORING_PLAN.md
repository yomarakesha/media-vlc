# MediaMTX VMS Client v2.0 - Modernization Plan

## Phase 1: Performance & Video Engine (High Priority)
**Objective**: Eliminate CPU bottlenecks by offloading decoding and rendering to the GPU.

### 1.1 Data Model Updates (`models/camera.py`)
- **Add `sub_stream_url`**: Add a field to store the secondary/low-resolution stream URL.
- **Validation**: Update validation to check optional stream URLs.

### 1.2 New Video Engine (`core/video/`)
- **`VideoPlayer` Class**: 
    - Wraps `PySide6.QtMultimedia.QMediaPlayer`.
    - Manages the playback state (Playing, Stopped, buffering).
    - Handles stream switching (`switch_stream(url)`).
    - Exposes signals for errors and media status.
- **Hardware Acceleration**: `QMediaPlayer` in Qt6 automatically uses the best available backend (FFmpeg/GStreamer/MediaFoundation) which supports hardware acceleration (NVDEC/DXVA2) by default.

### 1.3 UI Rendering Optimization (`ui/video_widget.py`)
- **Replace `QLabel` with `QVideoWidget`**:
    - `QVideoWidget` provides a zero-copy hardware-accelerated surface (Direct3D/OpenGL/Metal).
    - Removes the costly `cv2.imread` -> `numpy` -> `QImage` -> `QPixmap` -> `paint` pipeline.
- **Overlay Management**:
    - Implement a transparent `OverlayWidget` placed on top of `QVideoWidget` for drawing text (Camera Name, Timestamp, Status) and bounding boxes (Motion).
    - This ensures video rendering remains on the GPU while OSD (On-Screen Display) is lightweight.
- **Smart Stream Switching**:
    - Implement `set_quality(StreamQuality)` method.
    - `StreamQuality.LOW`: Plays `sub_stream_url` (fallback to main if missing).
    - `StreamQuality.HIGH`: Plays `url` (Main stream).
    - Logic to switch automatically based on widget size or explicit grid layout commands.

## Phase 2: Remote Archive & ONVIF
*(To be implemented after Phase 1)*
- **ONVIF Service**: Implement `onvif-zeep` or similar client for `FindRecordings`.
- **Timeline**: Custom `QGraphicsView` based timeline.

## Phase 3: Architecture & Data
*(To be implemented after Phase 2)*
- **SQLite Migration**: integrating `SQLAlchemy`.
- **AsyncIO**: Integrating `qasync` loop.

---

# Implementation: Phase 1 (Video Engine)

## Step 1: Update Camera Model
Modify `models/camera.py` to support dual streams.

## Step 2: Create Video Widget with GPU Support
Refactor `ui/video_widget.py` to use `QMediaPlayer` and `QVideoWidget`.

## Step 3: Integration
Update `GridWidget` to call `set_quality` based on layout changes.
