# MediaMTX VMS Client - Testing Guide

## Overview
This guide explains how to run automated tests for the MediaMTX VMS Client.

## Installation

### Install Test Dependencies
```bash
pip install pytest pytest-qt pytest-cov pytest-timeout
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/models/test_camera.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

### Run with Output
```bash
pytest tests/ -v -s
```

## Test Structure

```
tests/
├── conftest.py          # Pytest configuration and fixtures
├── models/
│   ├── __init__.py
│   └── test_camera.py   # Camera model tests (30+ tests)
├── utils/
│   └── test_config.py   # Config manager tests (planned)
└── ui/
    └── test_video_widget.py  # UI tests (planned)
```

## Available Fixtures

### From conftest.py
- `sample_camera` - Camera with full configuration
- `sample_camera_no_substream` - Simple camera without sub-stream
- `sample_nvr` - NVR instance
- `config_manager` - Fresh ConfigManager instance
- `qtbot` - Qt widget testing helper

### Example Usage
```python
def test_camera_validation(sample_camera):
    is_valid, msg = sample_camera.validate()
    assert is_valid is True
```

## Test Categories

### Unit Tests
Test individual components in isolation.

**Location**: `tests/models/`, `tests/utils/`

**Run**:
```bash
pytest tests/models/ tests/utils/ -v
```

### Integration Tests
Test component interactions.

**Location**: `tests/integration/` (planned)

**Run**:
```bash
pytest tests/integration/ -v -m integration
```

### UI Tests
Test PyQt6 widgets.

**Location**: `tests/ui/` (planned)

**Run**:
```bash
pytest tests/ui/ -v
```

## Writing Tests

### Test Camera Model
```python
from models.camera import Camera

def test_camera_creation():
    camera = Camera(name="Test", url="rtsp://test")
    assert camera.name == "Test"
    assert camera.url == "rtsp://test"
```

### Test with Fixtures
```python
def test_with_fixture(sample_camera):
    # Fixture provides pre-configured camera
    assert sample_camera.name == "Test Camera"
    assert sample_camera.has_sub_stream() is True
```

### Test UI Components
```python
def test_video_widget(qtbot):
    from ui.video_widget import VideoWidget
    
    widget = VideoWidget()
    qtbot.addWidget(widget)
    
    # Test widget state
    assert widget.is_streaming() is False
```

## Continuous Integration

### GitHub Actions (Recommended)
Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=.
```

## Performance Testing

### CPU Usage Benchmark
```python
# tests/performance/test_cpu_usage.py
import psutil
import pytest

@pytest.mark.performance
def test_cpu_usage_9_cameras():
    # Start 9 streams
    # Measure CPU for 60 seconds
    # Assert average < 20%
    pass
```

**Run**:
```bash
pytest tests/performance/ -v -m performance
```

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Models | 90% | 85% |
| Core | 80% | 0% |
| UI | 60% | 0% |
| Utils | 80% | 0% |
| **Overall** | **70%** | **30%** |

## Debugging Tests

### Run Single Test
```bash
pytest tests/models/test_camera.py::TestCameraValidation::test_valid_rtsp_camera -v
```

### Enable Debug Logging
```bash
pytest tests/ -v --log-cli-level=DEBUG
```

### Use PDB Debugger
```python
def test_something():
    import pdb; pdb.set_trace()
    # Your test code
```

## Common Issues

### Qt Platform Plugin Error
```
qt.qpa.plugin: Could not find the Qt platform plugin
```

**Solution**: Install Qt dependencies
```bash
# Linux
sudo apt-get install qt6-base-dev

# Windows
# Qt is bundled with PyQt6
```

### Import Errors
```
ModuleNotFoundError: No module named 'models'
```

**Solution**: Run from project root
```bash
cd c:\Users\Windows 11 Pro\Desktop\clint2
pytest tests/ -v
```

## Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names**
3. **Isolate tests** (no dependencies between tests)
4. **Use fixtures** for common setup
5. **Mark slow tests** with `@pytest.mark.slow`
6. **Mock external dependencies** (network, files)

## Next Steps

1. Run existing tests: `pytest tests/models/ -v`
2. Check coverage: `pytest tests/ --cov=. --cov-report=html`
3. Add tests for your changes
4. Aim for >70% overall coverage

---

**Updated**: 2026-01-07
