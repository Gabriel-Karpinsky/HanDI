import sys
import os
import cv2
import time
import numpy as np
from dotenv import load_dotenv, set_key
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QDialog, QSpinBox, QSlider, QComboBox
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import HandTrackingModule as htm  # Import the updated module
import pygrabber

# Load environment variables
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=ENV_FILE)

def update_env_variable(key, value):
    set_key(ENV_FILE, key, str(value))
    load_dotenv(ENV_FILE, override=True)

def get_available_cameras(max_index=10):
    available = []
    # Attempt to get friendly names on Windows using pygrabber
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()  # list of device names
        for i in range(min(len(devices), max_index)):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, devices[i]))
                cap.release()
    except Exception as e:
        # Fallback: just check the indices and use generic names
        print("pygrabber not available or error occurred, falling back to generic names.")
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, f"Camera {i}"))
                cap.release()
    return available

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
        self.init_camera()
        
    def init_camera(self):
        if hasattr(self, 'cap'):
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"⚠️ ERROR: Could not open camera {self.camera_index}")

    def run(self):
        while self.running:
            success, frame = self.cap.read()
            if not success:
                print("⚠️ ERROR: Failed to capture frame")
                continue

            frame = cv2.flip(frame, 1)
            frame = self.detector.findHands(frame)
            lmList, bbox = self.detector.findPosition(frame, draw=True)

            if lmList:
                volume_percentage = self.volume_controller.set_volume_by_hand_distance(lmList, frame, self.detector)
                if volume_percentage is not None:
                    self.volume_signal.emit(int(volume_percentage))

            self.frame_signal.emit(frame)

    def stop(self):
        self.running = False
        self.cap.release()

    def update_camera_index(self, new_index):
        self.camera_index = new_index
        self.init_camera()
    
    def update_detection_conf(self, new_conf):
        self.detection_conf = new_conf
        self.detector = htm.HandDetector(detectionConf=self.detection_conf)

from PyQt6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QDialog, QPushButton
from dotenv import set_key
from PyQt6.QtCore import Qt
import os
import cv2

# Assuming ENV_FILE is defined and load_dotenv has been called.

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 300, 200)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Camera Device Drop-down Setting
        self.cam_label = QLabel("Camera Device:")
        self.cam_combo = QComboBox()
        self.available_cams = get_available_cameras()  # returns list of tuples (index, name)
        for cam_index, cam_name in self.available_cams:
            # Display both index and name for clarity
            self.cam_combo.addItem(f"{cam_name} (Index {cam_index})", cam_index)
        
        # Set current camera based on .env setting
        current_cam = int(os.getenv("CAMERA_INDEX", 0))
        index = self.cam_combo.findData(current_cam)
        if index >= 0:
            self.cam_combo.setCurrentIndex(index)
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)

        layout.addWidget(self.cam_label)
        layout.addWidget(self.cam_combo)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def save_settings(self):
        """Save new settings to the .env file and reload them dynamically."""
        new_camera_index = self.cam_combo.currentData()
        set_key(ENV_FILE, "CAMERA_INDEX", str(new_camera_index))
        # Optionally reload environment variables if needed:
        # load_dotenv(ENV_FILE, override=True)
        print(f"Updated CAMERA_INDEX to: {new_camera_index}")
        self.parent().hand_tracking_thread.update_camera_index(new_camera_index)
        self.accept()  # Close the settings dialog


class HandTrackingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Tracking GUI")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(400, 300)
        
        # UI Elements
        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_label = QLabel("Volume: 100%")
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)

        # STOP Button
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.send_MIDI_stop)
        self.stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")

        # Detection Confidence Slider
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(1, 100)
        self.conf_slider.setValue(int(float(os.getenv("DETECTION_CONF", 70)) * 100))
        self.conf_slider.valueChanged.connect(self.update_detection_conf)
        self.conf_label = QLabel(f"Detection Confidence: {self.conf_slider.value()}%")
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)
        layout.addWidget(self.volume_label)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.conf_label)
        layout.addWidget(self.conf_slider)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

        # Start Hand Tracking in a separate thread
        self.hand_tracking_thread = HandTrackingThread(
            int(os.getenv("CAMERA_INDEX", 0)), float(os.getenv("DETECTION_CONF", 0.7))
        )
        self.hand_tracking_thread.frame_signal.connect(self.display_frame)
        self.hand_tracking_thread.volume_signal.connect(self.update_volume_label)
        self.hand_tracking_thread.start()
        self.pTime = 0
        self.cTime = 0

    def display_frame(self, frame):
        frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()), interpolation=cv2.INTER_AREA)
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #self.cTime = time.time()
        #self.fps = 1 / (self.cTime - self.pTime)
        #self.pTime = self.cTime

        #frame = cv2.putText(frame, f'FPS: {int(self.fps)}', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_volume_label(self, volume_percentage):
        self.volume_label.setText(f"Volume: {volume_percentage}%")

    def open_settings(self):
        settings_window = SettingsDialog(self)
        settings_window.exec()

    def update_detection_conf(self, value):
        new_conf = value / 100.0
        update_env_variable("DETECTION_CONF", new_conf)
        self.conf_label.setText(f"Detection Confidence: {value}%")
        self.hand_tracking_thread.update_detection_conf(new_conf)
    
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
