"""
MediaMTX VMS Client v2.0 - Main Entry Point
Professional Video Management System for Windows

Features:
- Multi-camera grid (up to 100 cameras)
- RTSP & HLS streaming
- ONVIF NVR integration  
- Motion detection & recording
- Auto-reconnection
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from ui.main_window import MainWindow
from utils.logger import logger
from utils.config import config


def set_environment_variables():
    """Set environment variables for third-party libraries."""
    # Set OpenCV/FFmpeg timeout to 3 seconds (value in microseconds)
    # This loop prevents the UI from freezing during long connection attempts
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "stimeout;3000000"
    
    # Force FFmpeg backend on Windows (disable Media Foundation which can be slow)
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

def load_stylesheet(app: QApplication) -> None:
    """
    Load and apply QSS stylesheet.
    
    Args:
        app: QApplication instance
    """
    stylesheet_path = "assets/style.qss"
    
    if os.path.exists(stylesheet_path):
        try:
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
                logger.info("Stylesheet loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load stylesheet: {e}")
    else:
        logger.warning(f"Stylesheet not found: {stylesheet_path}")


def create_splash_screen() -> QSplashScreen:
    """
    Create splash screen.
    
    Returns:
        QSplashScreen instance
    """
    # Create a simple colored splash screen
    # In production, replace with actual logo image
    splash_pix = QPixmap(600, 400)
    splash_pix.fill(Qt.GlobalColor.black)
    
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    
    # Add text
    font = QFont("Segoe UI", 24, QFont.Weight.Bold)
    splash.setFont(font)
    splash.showMessage(
        "MediaMTX VMS Client v2.0\n\nLoading...",
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
        Qt.GlobalColor.white
    )
    
    return splash


def main():
    """Main application entry point."""
    # Set environment variables
    set_environment_variables()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("MediaMTX VMS Client")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("MediaMTX VMS")
    
    # Show splash screen
    splash = create_splash_screen()
    splash.show()
    app.processEvents()
    
    logger.info("="*80)
    logger.info("MediaMTX VMS Client v2.0 - Starting")
    logger.info("="*80)
    
    # Load stylesheet
    load_stylesheet(app)
    
    # Create main window
    main_window = MainWindow()
    
    # Close splash and show main window
    def show_main_window():
        splash.finish(main_window)
        main_window.show()
        logger.info("Main window displayed")
    
    # Show main window after 1.5 seconds
    QTimer.singleShot(1500, show_main_window)
    
    # Run event loop
    exit_code = app.exec()
    
    logger.info("Application exiting with code: {}".format(exit_code))
    logger.info("="*80)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
