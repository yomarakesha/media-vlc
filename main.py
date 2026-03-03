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
            _apply_fallback_style(app)
    else:
        logger.warning(f"Stylesheet not found: {stylesheet_path}")
        _apply_fallback_style(app)


def _apply_fallback_style(app: QApplication) -> None:
    """Apply minimal fallback style when QSS file is unavailable."""
    fallback = """
    * { font-family: "Segoe UI", Arial; font-size: 9pt; color: #D4D4D4; }
    QMainWindow, QWidget { background-color: #1E1E1E; }
    QPushButton { background-color: #2D2D30; border: 1px solid #3E3E42; padding: 6px 12px; }
    QPushButton:hover { border-color: #007ACC; }
    """
    app.setStyleSheet(fallback)
    logger.info("Fallback stylesheet applied")


def create_splash_screen() -> QSplashScreen:
    """
    Create professional splash screen with gradient.
    
    Returns:
        QSplashScreen instance
    """
    from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QBrush, QPen
    
    # Create pixmap
    splash_pix = QPixmap(600, 400)
    
    # Draw gradient background
    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Purple-violet gradient (matching main theme)
    gradient = QLinearGradient(0, 0, 600, 400)
    gradient.setColorAt(0.0, QColor("#0d1117"))
    gradient.setColorAt(0.3, QColor("#161b22"))
    gradient.setColorAt(0.7, QColor("#1a1f2e"))
    gradient.setColorAt(1.0, QColor("#0d1117"))
    painter.fillRect(0, 0, 600, 400, QBrush(gradient))
    
    # Draw accent line at top
    accent_gradient = QLinearGradient(0, 0, 600, 0)
    accent_gradient.setColorAt(0.0, QColor("#667eea"))
    accent_gradient.setColorAt(0.5, QColor("#00d4aa"))
    accent_gradient.setColorAt(1.0, QColor("#764ba2"))
    painter.fillRect(0, 0, 600, 4, QBrush(accent_gradient))
    
    # Draw title
    title_font = QFont("Segoe UI", 32, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(QPen(QColor("#ffffff")))
    painter.drawText(0, 120, 600, 50, Qt.AlignmentFlag.AlignCenter, "MediaMTX VMS")
    
    # Draw version
    version_font = QFont("Segoe UI", 14, QFont.Weight.Normal)
    painter.setFont(version_font)
    painter.setPen(QPen(QColor("#00d4aa")))
    painter.drawText(0, 170, 600, 30, Qt.AlignmentFlag.AlignCenter, "v2.1 Professional")
    
    # Draw subtitle
    subtitle_font = QFont("Segoe UI", 11, QFont.Weight.Normal)
    painter.setFont(subtitle_font)
    painter.setPen(QPen(QColor("#8b949e")))
    painter.drawText(0, 210, 600, 30, Qt.AlignmentFlag.AlignCenter, 
                     "Video Management System for Windows")
    
    # Draw loading bar background
    painter.fillRect(150, 320, 300, 6, QColor("#21262d"))
    
    # Draw loading bar (animated in real app)
    loading_gradient = QLinearGradient(150, 0, 450, 0)
    loading_gradient.setColorAt(0.0, QColor("#667eea"))
    loading_gradient.setColorAt(1.0, QColor("#764ba2"))
    painter.fillRect(150, 320, 200, 6, QBrush(loading_gradient))
    
    # Draw loading text
    loading_font = QFont("Segoe UI", 9)
    painter.setFont(loading_font)
    painter.setPen(QPen(QColor("#8b949e")))
    painter.drawText(0, 340, 600, 25, Qt.AlignmentFlag.AlignCenter, "Initializing...")
    
    # Draw copyright
    painter.drawText(0, 370, 600, 20, Qt.AlignmentFlag.AlignCenter, 
                     "© 2024 MediaMTX VMS. All rights reserved.")
    
    painter.end()
    
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
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
