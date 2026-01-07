"""  
MediaMTX VMS Client v2.0 - Recording Schedule Dialog
Configure recording schedules for cameras.
"""

from typing import List
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QListWidget, QListWidgetItem, QLabel, QComboBox,
                              QTimeEdit, QCheckBox, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt, QTime

from core.recording_manager import RecordingSchedule
from utils.logger import logger


class RecordingScheduleDialog(QDialog):
    """
    Dialog for configuring recording schedules.
    """
    
    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    def __init__(self, parent=None):
        """Initialize schedule dialog."""
        super().__init__(parent)
        
        self._schedules: List[RecordingSchedule] = []
        
        self.setWindowTitle("Recording Schedules")
        self.setMinimumSize(600, 500)
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "Configure time-based recording schedules. "
            "Recording will automatically start/stop based on these rules."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Schedule list
        list_group = QGroupBox("Schedules")
        list_layout = QVBoxLayout()
        
        self._schedule_list = QListWidget()
        self._schedule_list.currentRowChanged.connect(self._on_schedule_selected)
        list_layout.addWidget(self._schedule_list)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Schedule editor
        editor_group = QGroupBox("Schedule Configuration")
        editor_layout = QVBoxLayout()
        
        # Days selection
        days_label = QLabel("Days:")
        editor_layout.addWidget(days_label)
        
        days_layout = QHBoxLayout()
        self._day_checks = {}
        for day in self.WEEKDAYS:
            check = QCheckBox(day[:3])  # Mon, Tue, etc.
            check.setToolTip(day)
            self._day_checks[day] = check
            days_layout.addWidget(check)
        editor_layout.addLayout(days_layout)
        
        # Time range
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("From:"))
        
        self._start_time = QTimeEdit()
        self._start_time.setDisplayFormat("HH:mm")
        self._start_time.setTime(QTime(8, 0))
        time_layout.addWidget(self._start_time)
        
        time_layout.addWidget(QLabel("To:"))
        
        self._end_time = QTimeEdit()
        self._end_time.setDisplayFormat("HH:mm")
        self._end_time.setTime(QTime(18, 0))
        time_layout.addWidget(self._end_time)
        
        editor_layout.addLayout(time_layout)
        
        # Enabled checkbox
        self._enabled_check = QCheckBox("Enabled")
        self._enabled_check.setChecked(True)
        editor_layout.addWidget(self._enabled_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Schedule")
        add_btn.clicked.connect(self._add_schedule)
        button_layout.addWidget(add_btn)
        
        update_btn = QPushButton("Update Selected")
        update_btn.clicked.connect(self._update_schedule)
        button_layout.addWidget(update_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_schedule)
        button_layout.addWidget(remove_btn)
        
        editor_layout.addLayout(button_layout)
        
        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)
        
        # Quick presets
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QHBoxLayout()
        
        weekdays_btn = QPushButton("Weekdays 8-18")
        weekdays_btn.clicked.connect(lambda: self._apply_preset("weekdays"))
        preset_layout.addWidget(weekdays_btn)
        
        weekend_btn = QPushButton("Weekend 24/7")
        weekend_btn.clicked.connect(lambda: self._apply_preset("weekend"))
        preset_layout.addWidget(weekend_btn)
        
        night_btn = QPushButton("Nights 18-8")
        night_btn.clicked.connect(lambda: self._apply_preset("night"))
        preset_layout.addWidget(night_btn)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Dialog buttons
        dialog_button_layout = QHBoxLayout()
        dialog_button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        dialog_button_layout.addWidget(save_btn)
        
        layout.addLayout(dialog_button_layout)
    
    def set_schedules(self, schedules: List[RecordingSchedule]) -> None:
        """
        Load existing schedules.
        
        Args:
            schedules: List of RecordingSchedule objects
        """
        self._schedules = schedules.copy()
        self._refresh_list()
    
    def get_schedules(self) -> List[RecordingSchedule]:
        """Get configured schedules."""
        return self._schedules.copy()
    
    def _add_schedule(self) -> None:
        """Add new schedule from current editor values."""
        schedule = self._create_from_editor()
        if schedule:
            self._schedules.append(schedule)
            self._refresh_list()
            self._schedule_list.setCurrentRow(len(self._schedules) - 1)
    
    def _update_schedule(self) -> None:
        """Update currently selected schedule."""
        index = self._schedule_list.currentRow()
        if 0 <= index < len(self._schedules):
            schedule = self._create_from_editor()
            if schedule:
                self._schedules[index] = schedule
                self._refresh_list()
                self._schedule_list.setCurrentRow(index)
    
    def _remove_schedule(self) -> None:
        """Remove currently selected schedule."""
        index = self._schedule_list.currentRow()
        if 0 <= index < len(self._schedules):
            self._schedules.pop(index)
            self._refresh_list()
    
    def _create_from_editor(self) -> Optional[RecordingSchedule]:
        """
        Create schedule from editor values.
        
        Returns:
            RecordingSchedule or None if invalid
        """
        # Get selected days
        days = [day for day, check in self._day_checks.items() if check.isChecked()]
        
        if not days:
            QMessageBox.warning(self, "Invalid Schedule", "Please select at least one day.")
            return None
        
        # Get times
        start_time = self._start_time.time().toString("HH:mm")
        end_time = self._end_time.time().toString("HH:mm")
        
        return RecordingSchedule(
            days=days,
            start_time=start_time,
            end_time=end_time,
            enabled=self._enabled_check.isChecked()
        )
    
    def _on_schedule_selected(self, index: int) -> None:
        """Load selected schedule into editor."""
        if 0 <= index < len(self._schedules):
            schedule = self._schedules[index]
            
            # Set days
            for day, check in self._day_checks.items():
                check.setChecked(day in schedule.days)
            
            # Set times
            start_h, start_m = map(int, schedule.start_time.split(":"))
            self._start_time.setTime(QTime(start_h, start_m))
            
            end_h, end_m = map(int, schedule.end_time.split(":"))
            self._end_time.setTime(QTime(end_h, end_m))
            
            # Set enabled
            self._enabled_check.setChecked(schedule.enabled)
    
    def _apply_preset(self, preset: str) -> None:
        """
        Apply quick preset.
        
        Args:
            preset: Preset name ('weekdays', 'weekend', 'night')
        """
        # Clear current days
        for check in self._day_checks.values():
            check.setChecked(False)
        
        if preset == "weekdays":
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
                self._day_checks[day].setChecked(True)
            self._start_time.setTime(QTime(8, 0))
            self._end_time.setTime(QTime(18, 0))
        
        elif preset == "weekend":
            for day in ["Saturday", "Sunday"]:
                self._day_checks[day].setChecked(True)
            self._start_time.setTime(QTime(0, 0))
            self._end_time.setTime(QTime(23, 59))
        
        elif preset == "night":
            for check in self._day_checks.values():
                check.setChecked(True)
            self._start_time.setTime(QTime(18, 0))
            self._end_time.setTime(QTime(8, 0))
    
    def _refresh_list(self) -> None:
        """Refresh schedule list."""
        current_row = self._schedule_list.currentRow()
        self._schedule_list.clear()
        
        for schedule in self._schedules:
            status = "✓" if schedule.enabled else "✗"
            days_text = ", ".join([d[:3] for d in schedule.days])
            text = f"{status} {days_text} {schedule.start_time}-{schedule.end_time}"
            self._schedule_list.addItem(text)
        
        if 0 <= current_row < len(self._schedules):
            self._schedule_list.setCurrentRow(current_row)
