"""
MediaMTX VMS Client v2.0 - Theme Manager
Handles application styling and themes.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPalette

from utils.config import config
from utils.logger import logger

class ThemeManager:
    """Manages application themes (Dark/Light)."""
    
    THEME_DARK = "Dark"
    THEME_LIGHT = "Light"
    
    # Modern Dark Theme
    STYLESHEET_DARK = """
    QMainWindow, QWidget {
        background-color: #1E1E1E;
        color: #FFFFFF;
        font-family: 'Segoe UI', sans-serif;
    }
    
    QDockWidget {
        titlebar-close-icon: url(close.png);
        titlebar-normal-icon: url(float.png);
        border: 1px solid #333333;
    }
    QDockWidget::title {
        background: #252526;
        padding-left: 5px;
        padding-top: 2px;
    }

    QTreeWidget, QListWidget {
        background-color: #252526;
        border: 1px solid #3E3E42;
        color: #CCCCCC;
    }
    QTreeWidget::item:hover {
        background-color: #2A2D2E;
    }
    QTreeWidget::item:selected {
        background-color: #094771;
        color: #FFFFFF;
    }
    
    QPushButton {
        background-color: #3E3E42;
        border: 1px solid #3E3E42;
        color: #FFFFFF;
        padding: 5px 15px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #4E4E52;
    }
    QPushButton:pressed {
        background-color: #007ACC;
        border-color: #007ACC;
    }
    QPushButton:disabled {
        background-color: #2D2D30;
        color: #6D6D6D;
    }
    
    QLabel {
        color: #FFFFFF;
    }
    
    QGroupBox {
        border: 1px solid #3E3E42;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: #007ACC;
    }
    
    QStatusBar {
        background-color: #007ACC;
        color: #FFFFFF;
    }
    
    QMenuBar {
        background-color: #1E1E1E;
        border-bottom: 1px solid #333333;
    }
    QMenuBar::item:selected {
        background-color: #3E3E42;
    }
    QMenu {
        background-color: #252526;
        border: 1px solid #333333;
    }
    QMenu::item:selected {
        background-color: #094771;
    }
    
    QTabWidget::pane { 
        border: 1.5px solid #007ACC; 
        background: #1E1E1E;
    }
    QTabBar::tab {
        background: #2D2D30;
        color: #CCCCCC;
        padding: 8px 20px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #1E1E1E;
        color: #007ACC;
        border-top: 2px solid #007ACC;
    }
    """
    
    # Clean Light Theme
    STYLESHEET_LIGHT = """
    QMainWindow, QWidget {
        background-color: #F3F3F3;
        color: #000000;
        font-family: 'Segoe UI', sans-serif;
    }
    
    QDockWidget {
        border: 1px solid #CCCCCC;
    }
    QDockWidget::title {
        background: #E1E1E1;
        padding-left: 5px;
    }

    QTreeWidget, QListWidget {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        color: #000000;
    }
    QTreeWidget::item:hover {
        background-color: #E8E8E8;
    }
    QTreeWidget::item:selected {
        background-color: #CCE8FF;
        color: #000000;
        border: 1px solid #99D1FF;
    }
    
    QPushButton {
        background-color: #E1E1E1;
        border: 1px solid #ADADAD;
        color: #000000;
        padding: 5px 15px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #E5F1FB;
        border-color: #0078D4;
    }
    QPushButton:pressed {
        background-color: #CCE8FF;
    }
    
    QGroupBox {
        border: 1px solid #D0D0D0;
        margin-top: 10px;
    }
    QGroupBox::title {
        color: #0078D4;
    }
    
    QStatusBar {
        background-color: #0078D4;
        color: #FFFFFF;
    }
    
    QMenuBar {
        background-color: #F3F3F3;
        border-bottom: 1px solid #CCCCCC;
    }
    QMenuBar::item:selected {
        background-color: #E1E1E1;
    }
    QMenu {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
    }
    QMenu::item:selected {
        background-color: #CCE8FF;
    }
    
    QTabWidget::pane { 
        border: 1px solid #CCCCCC;
    }
    QTabBar::tab {
        background: #E1E1E1;
        color: #333333;
        padding: 8px 20px;
    }
    QTabBar::tab:selected {
        background: #FFFFFF;
        color: #0078D4;
        border-top: 2px solid #0078D4;
    }
    """
    
    def __init__(self, app: QApplication):
        self._app = app
        self._current_theme = config.get("settings.theme", self.THEME_DARK)
        self.apply_theme(self._current_theme)
        
    def apply_theme(self, theme_name: str) -> None:
        """Apply selected theme."""
        if theme_name == self.THEME_LIGHT:
            self._app.setStyleSheet(self.STYLESHEET_LIGHT)
            self._set_palette_light()
        else:
            self._app.setStyleSheet(self.STYLESHEET_DARK)
            self._set_palette_dark()
            
        self._current_theme = theme_name
        config.set("settings.theme", theme_name, save=True)
        logger.info(f"Theme set to: {theme_name}")

    def toggle_theme(self) -> str:
        """Toggle between Dark and Light."""
        new_theme = self.THEME_LIGHT if self._current_theme == self.THEME_DARK else self.THEME_DARK
        self.apply_theme(new_theme)
        return new_theme

    def _set_palette_dark(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self._app.setPalette(palette)

    def _set_palette_light(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(243, 243, 243))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        self._app.setPalette(palette)
