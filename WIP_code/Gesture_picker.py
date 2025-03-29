from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QCheckBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

# Define available gestures and their corresponding MIDI command options.
AVAILABLE_GESTURES = ["Pinch", "Fist"]
MIDI_OPTIONS_MAPPING = {
    "Pinch": ["Volume Control", "Modulation"],
    "Fist": ["Mute", "Play/Pause"]
}

class GestureSettingRow(QWidget):
    def __init__(self, available_gestures, midi_options_mapping, parent=None):
        super().__init__(parent)
        self.available_gestures = available_gestures
        self.midi_options_mapping = midi_options_mapping
        
        # Create horizontal layout for the row.
        layout = QHBoxLayout()
        
        # Gesture dropdown.
        self.gesture_combo = QComboBox()
        self.gesture_combo.addItems(self.available_gestures)
        layout.addWidget(self.gesture_combo)
        
        # MIDI command dropdown.
        self.midi_combo = QComboBox()
        # Populate MIDI commands based on the first gesture.
        self.midi_combo.addItems(self.midi_options_mapping[self.gesture_combo.currentText()])
        layout.addWidget(self.midi_combo)
        
        # ON/OFF toggle using a QCheckBox.
        self.active_checkbox = QCheckBox("ON/OFF")
        self.active_checkbox.setChecked(True)
        layout.addWidget(self.active_checkbox)
        
        self.setLayout(layout)
        
        # Update the MIDI options when the gesture selection changes.
        self.gesture_combo.currentTextChanged.connect(self.update_midi_options)
    
    def update_midi_options(self, gesture):
        self.midi_combo.clear()
        self.midi_combo.addItems(self.midi_options_mapping.get(gesture, []))
    
    def get_settings(self):
        return {
            "gesture": self.gesture_combo.currentText(),
            "midi": self.midi_combo.currentText(),
            "active": self.active_checkbox.isChecked()
        }

class GestureSettingsDialog(QDialog):
    def __init__(self, available_gestures, midi_options_mapping, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gesture Settings")
        self.available_gestures = available_gestures
        self.midi_options_mapping = midi_options_mapping
        self.rows = []
        
        self.main_layout = QVBoxLayout()
        
        # Container layout for the gesture rows.
        self.rows_layout = QVBoxLayout()
        self.main_layout.addLayout(self.rows_layout)
        
        # Initially add one row.
        self.add_row()
        
        # Button to add new gesture settings row.
        self.add_button = QPushButton("+ Add New Gesture")
        self.add_button.clicked.connect(self.add_row)
        self.main_layout.addWidget(self.add_button)
        
        # OK and Cancel buttons.
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(button_layout)
        
        self.setLayout(self.main_layout)
    
    def add_row(self):
        row = GestureSettingRow(self.available_gestures, self.midi_options_mapping)
        self.rows.append(row)
        self.rows_layout.addWidget(row)
    
    def get_all_settings(self):
        return [row.get_settings() for row in self.rows]

# Example usage: launch the gesture settings dialog.
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    dialog = GestureSettingsDialog(AVAILABLE_GESTURES, MIDI_OPTIONS_MAPPING)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Retrieve settings from all rows.
        settings = dialog.get_all_settings()
        print("Gesture Settings:")
        for setting in settings:
            print(setting)
    sys.exit(app.exec())
