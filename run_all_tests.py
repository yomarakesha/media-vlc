#!/usr/bin/env python
"""
MediaMTX VMS Client v2.1 - Integration Test Runner

This script runs all tests and generates a comprehensive report.
It detects tracebacks, measures coverage, and validates the application.

Usage:
    python run_all_tests.py          # Run all tests
    python run_all_tests.py --quick  # Run quick smoke tests only
    python run_all_tests.py --cov    # Run with coverage report
"""

import sys
import os
import subprocess
import argparse
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """Comprehensive test runner with traceback detection."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.tests_dir = self.project_root / "tests"
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'tracebacks': []
        }
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self, with_coverage: bool = False) -> int:
        """Run all pytest tests.
        
        Args:
            with_coverage: Whether to generate coverage report
            
        Returns:
            Exit code (0 = success, 1 = failures)
        """
        print("\n" + "=" * 70)
        print("MediaMTX VMS Client v2.1 - Integration Test Suite")
        print("=" * 70 + "\n")
        
        self.start_time = datetime.now()
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.tests_dir),
            "-v",
            "--tb=long",  # Full traceback
            "-x",  # Stop on first failure for quick feedback
        ]
        
        if with_coverage:
            cmd.extend([
                "--cov=core",
                "--cov=models",
                "--cov=ui",
                "--cov=utils",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov"
            ])
        
        print(f"Running: {' '.join(cmd)}\n")
        print("-" * 70)
        
        # Run tests and capture output
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Print output
            print(result.stdout)
            
            if result.stderr:
                print("\n--- STDERR ---")
                print(result.stderr)
            
            # Parse results
            self._parse_pytest_output(result.stdout)
            
            # Check for tracebacks
            self._detect_tracebacks(result.stdout + result.stderr)
            
            self.end_time = datetime.now()
            
            return result.returncode
            
        except subprocess.TimeoutExpired:
            print("ERROR: Tests timed out after 5 minutes!")
            return 1
        except Exception as e:
            print(f"ERROR running tests: {e}")
            traceback.print_exc()
            return 1
    
    def run_smoke_tests(self) -> int:
        """Run quick smoke tests to validate basic functionality.
        
        Returns:
            Exit code (0 = success, 1 = failures)
        """
        print("\n" + "=" * 70)
        print("Running Quick Smoke Tests")
        print("=" * 70 + "\n")
        
        errors = []
        
        # Test 1: Import all modules
        print("1. Testing module imports...")
        import_tests = [
            ("main", "Main application"),
            ("core.stream_manager", "Stream Manager"),
            ("core.camera_manager", "Camera Manager"),
            ("core.nvr_manager", "NVR Manager"),
            ("core.motion_detector", "Motion Detector"),
            ("core.discovery", "Device Discovery"),
            ("models.camera", "Camera Model"),
            ("models.nvr", "NVR Model"),
            ("ui.main_window", "Main Window"),
            ("ui.video_widget", "Video Widget"),
            ("utils.config", "Config Manager"),
            ("utils.logger", "Logger"),
        ]
        
        for module_name, description in import_tests:
            try:
                __import__(module_name)
                print(f"   ✓ {description}")
            except Exception as e:
                print(f"   ✗ {description}: {e}")
                errors.append(f"Import {module_name}: {e}")
        
        # Test 2: Configuration loading
        print("\n2. Testing configuration...")
        try:
            from utils.config import config
            cameras = config.get('cameras', [])
            nvrs = config.get('nvrs', [])
            print(f"   ✓ Config loaded ({len(cameras)} cameras, {len(nvrs)} NVRs)")
        except Exception as e:
            print(f"   ✗ Config loading: {e}")
            errors.append(f"Config: {e}")
        
        # Test 3: Model creation
        print("\n3. Testing model creation...")
        try:
            from models.camera import Camera
            from models.nvr import NVR
            
            camera = Camera(
                name="Test Camera",
                url="rtsp://test:554/stream",
                username="admin",
                password="test"
            )
            print(f"   ✓ Camera created: {camera.id}")
            
            nvr = NVR(
                name="Test NVR",
                host="192.168.1.100",
                port=80,
                username="admin",
                password="test"
            )
            print(f"   ✓ NVR created: {nvr.id}")
        except Exception as e:
            print(f"   ✗ Model creation: {e}")
            errors.append(f"Models: {e}")
            traceback.print_exc()
        
        # Test 4: Motion detector
        print("\n4. Testing motion detector...")
        try:
            from core.motion_detector import MotionDetector
            import numpy as np
            
            detector = MotionDetector()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            motion, regions = detector.detect(frame)
            print(f"   ✓ Motion detector works (motion={motion})")
        except Exception as e:
            print(f"   ✗ Motion detector: {e}")
            errors.append(f"Motion detector: {e}")
        
        # Test 5: Discovery module
        print("\n5. Testing discovery module...")
        try:
            from core.discovery import DiscoveredDevice, ONVIFDiscovery, MediaMTXDiscovery
            
            device = DiscoveredDevice(
                name="Test",
                address="192.168.1.1",
                port=80,
                device_type="ONVIF"
            )
            print(f"   ✓ DiscoveredDevice created")
            
            onvif = ONVIFDiscovery(timeout=0.1)
            print(f"   ✓ ONVIFDiscovery initialized")
            
            mtx = MediaMTXDiscovery(timeout=0.1)
            print(f"   ✓ MediaMTXDiscovery initialized")
        except Exception as e:
            print(f"   ✗ Discovery module: {e}")
            errors.append(f"Discovery: {e}")
        
        # Summary
        print("\n" + "=" * 70)
        if errors:
            print(f"SMOKE TESTS FAILED: {len(errors)} error(s)")
            print("\nErrors:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("SMOKE TESTS PASSED: All basic functionality works!")
            return 0
    
    def _parse_pytest_output(self, output: str) -> None:
        """Parse pytest output to count results."""
        lines = output.split('\n')
        
        for line in lines:
            if 'passed' in line:
                # Extract number of passed tests
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed':
                            self.results['passed'] = int(parts[i-1])
                        elif part == 'failed':
                            self.results['failed'] = int(parts[i-1])
                        elif part == 'error' or part == 'errors':
                            self.results['errors'] = int(parts[i-1])
                        elif part == 'skipped':
                            self.results['skipped'] = int(parts[i-1])
                except (ValueError, IndexError):
                    pass
    
    def _detect_tracebacks(self, output: str) -> None:
        """Detect and collect tracebacks from output."""
        lines = output.split('\n')
        in_traceback = False
        current_traceback = []
        
        for line in lines:
            if 'Traceback (most recent call last)' in line:
                in_traceback = True
                current_traceback = [line]
            elif in_traceback:
                current_traceback.append(line)
                # End of traceback - usually after an exception line
                if line.strip() and not line.startswith(' ') and ':' in line:
                    self.results['tracebacks'].append('\n'.join(current_traceback))
                    in_traceback = False
                    current_traceback = []
    
    def print_report(self) -> None:
        """Print final test report."""
        print("\n" + "=" * 70)
        print("TEST REPORT")
        print("=" * 70)
        
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"Duration: {duration:.2f} seconds")
        
        print(f"\nResults:")
        print(f"  Passed:  {self.results['passed']}")
        print(f"  Failed:  {self.results['failed']}")
        print(f"  Errors:  {self.results['errors']}")
        print(f"  Skipped: {self.results['skipped']}")
        
        if self.results['tracebacks']:
            print(f"\n⚠️  Found {len(self.results['tracebacks'])} traceback(s):")
            for i, tb in enumerate(self.results['tracebacks'], 1):
                print(f"\n--- Traceback {i} ---")
                print(tb[:500] + "..." if len(tb) > 500 else tb)
        
        print("\n" + "=" * 70)
        
        if self.results['failed'] == 0 and self.results['errors'] == 0:
            print("✅ ALL TESTS PASSED - Ready for production!")
        else:
            print("❌ TESTS FAILED - Please fix issues before deployment")
        
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MediaMTX VMS Client Test Runner"
    )
    parser.add_argument(
        '--quick', 
        action='store_true',
        help='Run quick smoke tests only'
    )
    parser.add_argument(
        '--cov', 
        action='store_true',
        help='Generate coverage report'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.quick:
        exit_code = runner.run_smoke_tests()
    else:
        exit_code = runner.run_all_tests(with_coverage=args.cov)
        runner.print_report()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
