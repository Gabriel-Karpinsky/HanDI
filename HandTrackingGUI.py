import sys
import os
import cv2
import time
import numpy as np
from dotenv import load_dotenv, set_key
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QCheckBox, QSlider
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import HandTrackingModule as htm  # Ensure your HandTrackingModule.py is in the same folder

# Load environment variables
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=ENV_FILE)

def update_env_variable(key, value):
    set_key(ENV_FILE, key, str(value))
    load_dotenv(ENV_FILE, override=True)

def get_available_cameras(max_index=10):
    """
    Returns a list of tuples (index, friendly_name) for each camera that can be opened.
    Attempts to use pygrabber (on Windows) to get friendly names; falls back to generic names.
    """
    available = []
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()
        for i in range(min(len(devices), max_index)):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, devices[i]))
                cap.release()
    except Exception as e:
        print("pygrabber not available or error occurred, falling back to generic names.")
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, f"Camera {i}"))
                cap.release()
    return available

# -------------------- Gesture Settings UI Elements -------------------- #

# Define available gestures and corresponding MIDI command options.
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
        
        self.layout = QHBoxLayout()
        
        # Gesture dropdown.
        self.gesture_combo = QComboBox()
        self.gesture_combo.addItems(self.available_gestures)
        self.layout.addWidget(self.gesture_combo)
        
        # MIDI command dropdown.
        self.midi_combo = QComboBox()
        self.midi_combo.addItems(self.midi_options_mapping[self.gesture_combo.currentText()])
        self.layout.addWidget(self.midi_combo)
        
        # ON/OFF toggle.
        self.active_checkbox = QCheckBox("ON/OFF")
        self.active_checkbox.setChecked(True)
        self.layout.addWidget(self.active_checkbox)
        
        # Remove button.
        self.remove_button = QPushButton("Remove")
        self.layout.addWidget(self.remove_button)
        
        self.setLayout(self.layout)
        
        # Update MIDI options when gesture selection changes.
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

class GestureSettingsWidget(QWidget):
    def __init__(self, available_gestures, midi_options_mapping, parent=None):
        super().__init__(parent)
        self.available_gestures = available_gestures
        self.midi_options_mapping = midi_options_mapping
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.rows = []
        
        # Button to add new gesture settings row.
        self.add_button = QPushButton("+ Add New Gesture")
        self.add_button.clicked.connect(self.add_row)
        
        # Add an initial row.
        self.add_row()
        
        self.layout.addWidget(self.add_button)
    
    def add_row(self):
        row = GestureSettingRow(self.available_gestures, self.midi_options_mapping)
        # Connect the remove button to remove the row.
        row.remove_button.clicked.connect(lambda: self.remove_row(row))
        self.rows.append(row)
        # Insert the new row above the add button.
        index = self.layout.indexOf(self.add_button)
        self.layout.insertWidget(index, row)
    
    def remove_row(self, row):
        if row in self.rows:
            self.rows.remove(row)
            row.setParent(None)
    
    def get_all_settings(self):
        return [row.get_settings() for row in self.rows]

# -------------------- Hand Tracking Thread -------------------- #

class HandTrackingThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    volume_signal = pyqtSignal(int)
    
    def __init__(self, camera_index, detection_conf):
        super().__init__()
        self.camera_index = camera_index
        self.detection_conf = detection_conf
        self.detector = htm.HandDetector(detectionConf=self.detection_conf)
        self.volume_controller = htm.VolumeController()
        self.running = True
        self.selected_gesture_settings = []  # List of gesture settings (dictionaries)
        self.fist_triggered = False  # For fist edge detection
        self.init_camera()

    def init_camera(self):
        if hasattr(self, 'cap'):
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"⚠️ ERROR: Could not open camera {self.camera_index}")

    def update_gesture_settings(self, settings):
        """Update the thread with gesture-to-MIDI mappings from the UI."""
        self.selected_gesture_settings = settings
        print("Updated gesture settings:", settings)
    
    def update_camera_index(self, new_index):
        self.camera_index = new_index
        update_env_variable("CAMERA_INDEX", new_index)
        self.init_camera()

    def run(self):
        while self.running:
            # Capture a frame from the camera
            success, frame = self.cap.read()
            if not success:
                print("⚠️ ERROR: Failed to capture frame. Reinitializing camera...")
                self.init_camera()
                continue

            # Process the frame
            frame = cv2.flip(frame, 1)
            frame = self.detector.findHands(frame)
            lmList, bbox = self.detector.findPosition(frame, draw=True)

            if lmList:
                # Process each active gesture mapping
                for setting in self.selected_gesture_settings:
                    if not setting["active"]:
                        continue
                    if setting["gesture"] == "Pinch":
                        volume_percentage = self.volume_controller.set_volume_by_hand_distance(lmList, frame, self.detector)
                        if volume_percentage is not None and setting["midi"] == "Volume Control":
                            self.volume_signal.emit(int(volume_percentage))
                        # You can add additional behavior for other Pinch-related MIDI commands
                    elif setting["gesture"] == "Fist":
                        fingers = self.detector.fingersUp()
                        if fingers and sum(fingers) == 0:
                            if not self.fist_triggered:
                                if setting["midi"] == "Mute":
                                    self.volume_controller.midi.send_MIDI_fist()
                                elif setting["midi"] == "Play/Pause":
                                    self.volume_controller.midi.send_MIDI_play_pause()
                                self.fist_triggered = True
                        else:
                            self.fist_triggered = False

            self.frame_signal.emit(frame)

    def stop(self):
        self.running = False
        self.cap.release()

# -------------------- Main GUI -------------------- #

class HandTrackingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Tracking GUI")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(400, 300)
        
        # Video display label.
        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Volume label.
        self.volume_label = QLabel("Volume: 100%")
        
        # Camera selection dropdown.
        self.camera_label = QLabel("Camera Device:")
        self.camera_combo = QComboBox()
        self.available_cams = get_available_cameras()
        for cam_index, cam_name in self.available_cams:
            self.camera_combo.addItem(f"{cam_name} (Index {cam_index})", cam_index)
        # Set current camera from .env (default is 0)
        current_cam = int(os.getenv("CAMERA_INDEX", 0))
        index = self.camera_combo.findData(current_cam)
        if index >= 0:
            self.camera_combo.setCurrentIndex(index)
        self.camera_combo.currentIndexChanged.connect(self.update_camera_index)
        
        # Detection Confidence Slider.
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(1, 100)
        self.conf_slider.setValue(int(float(os.getenv("DETECTION_CONF", 70)) * 100))
        self.conf_slider.valueChanged.connect(self.update_detection_conf)
        self.conf_label = QLabel(f"Detection Confidence: {self.conf_slider.value()}%")
        
        # Gesture Settings integrated directly into main UI.
        self.gesture_settings_widget = GestureSettingsWidget(AVAILABLE_GESTURES, MIDI_OPTIONS_MAPPING)
        # Button to apply gesture settings to the tracking thread.
        self.apply_gesture_settings_button = QPushButton("Apply Gesture Settings")
        self.apply_gesture_settings_button.clicked.connect(self.apply_gesture_settings)
        
        # STOP button.
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.send_MIDI_stop)
        self.stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        
        # Layout assembly.
        layout = QVBoxLayout()
        # Camera selection at the top.
        layout.addWidget(self.camera_label)
        layout.addWidget(self.camera_combo)
        layout.addWidget(self.video_label)
        layout.addWidget(self.volume_label)
        layout.addWidget(self.conf_label)
        layout.addWidget(self.conf_slider)
        layout.addWidget(QLabel("Gesture to MIDI Mappings:"))
        layout.addWidget(self.gesture_settings_widget)
        layout.addWidget(self.apply_gesture_settings_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)
        
        # Start Hand Tracking in a separate thread.
        self.hand_tracking_thread = HandTrackingThread(
            int(os.getenv("CAMERA_INDEX", 0)), float(os.getenv("DETECTION_CONF", 0.7))
        )
        self.hand_tracking_thread.frame_signal.connect(self.display_frame)
        self.hand_tracking_thread.volume_signal.connect(self.update_volume_label)
        self.hand_tracking_thread.start()
        self.pTime = 0
        self.cTime = 0

    def update_camera_index(self):
        new_index = self.camera_combo.currentData()
        self.hand_tracking_thread.update_camera_index(new_index)

    def apply_gesture_settings(self):
        settings = self.gesture_settings_widget.get_all_settings()
        self.hand_tracking_thread.update_gesture_settings(settings)
    
    def display_frame(self, frame):
        frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()), interpolation=cv2.INTER_AREA)
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #self.cTime = time.time()
        #self.fps = 1 / (self.cTime - self.pTime) if self.pTime != 0 else 0
        #self.pTime = self.cTime
        #frame = cv2.putText(frame, f'FPS: {int(self.fps)}', (40, 50),
        #                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_volume_label(self, volume_percentage):
        self.volume_label.setText(f"Volume: {volume_percentage}%")
    
    def update_detection_conf(self, value):
        new_conf = value / 100.0
        update_env_variable("DETECTION_CONF", new_conf)
        self.conf_label.setText(f"Detection Confidence: {value}%")
        self.hand_tracking_thread.detection_conf = new_conf
        self.hand_tracking_thread.detector = htm.HandDetector(detectionConf=new_conf)
    
    def send_MIDI_stop(self):
        self.hand_tracking_thread.volume_controller.midi.send_MIDI_stop()

    def closeEvent(self, event):
        self.hand_tracking_thread.volume_controller.midi.send_MIDI_stop()
        self.hand_tracking_thread.stop()
        self.hand_tracking_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HandTrackingGUI()
    window.show()
    sys.exit(app.exec())
