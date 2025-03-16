import sys
import os
import cv2
import numpy as np
from dotenv import load_dotenv, set_key
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QDialog, QSpinBox, QSlider
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import HandTrackingModule as htm  # Import the updated module

# Load environment variables
ENV_FILE = ".env"
load_dotenv(ENV_FILE)

def update_env_variable(key, value):
    set_key(ENV_FILE, key, str(value))
    load_dotenv(ENV_FILE, override=True)

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
            lmList = self.detector.findPosition(frame, draw=False)
            
            volume_percentage = self.volume_controller.set_volume_by_hand_distance(lmList)
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

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 300, 200)
        
        layout = QVBoxLayout()

        # Camera Index Setting
        self.cam_index_label = QLabel("Camera Index:")
        self.cam_index_spinbox = QSpinBox()
        self.cam_index_spinbox.setRange(0, 10)
        self.cam_index_spinbox.setValue(int(os.getenv("CAMERA_INDEX", 0)))  # Load value from .env

        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)

        layout.addWidget(self.cam_index_label)
        layout.addWidget(self.cam_index_spinbox)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def save_settings(self):
        """Save new settings to the .env file and reload them dynamically."""
        new_camera_index = self.cam_index_spinbox.value()

        # Write to .env file
        set_key(ENV_FILE, "CAMERA_INDEX", str(new_camera_index))

        # Reload environment variables
        load_dotenv(ENV_FILE, override=True)

        print(f"Updated CAMERA_INDEX to: {new_camera_index}")
        self.parent().hand_tracking_thread.update_camera_index(new_camera_index)
        self.accept()  # Close the settings dialog

class HandTrackingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Tracking GUI")
        self.setGeometry(100, 100, 800, 600)

        # UI Elements
        self.video_label = QLabel(self)
        self.volume_label = QLabel("Volume: 100%")
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)

        # Detection Confidence Slider
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(1, 100)
        self.conf_slider.setValue(int(float(os.getenv("DETECTION_CONF", 70)) * 100))  # Convert to integer percentage
        self.conf_slider.valueChanged.connect(self.update_detection_conf)
        self.conf_label = QLabel(f"Detection Confidence: {self.conf_slider.value()}%")
        
        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.volume_label)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.conf_label)
        layout.addWidget(self.conf_slider)
        self.setLayout(layout)

        # Start Hand Tracking in a separate thread
        self.hand_tracking_thread = HandTrackingThread(
            int(os.getenv("CAMERA_INDEX", 0)), float(os.getenv("DETECTION_CONF", 0.7))
        )
        self.hand_tracking_thread.frame_signal.connect(self.display_frame)
        self.hand_tracking_thread.volume_signal.connect(self.update_volume_label)
        self.hand_tracking_thread.start()

    def display_frame(self, frame):
        """Update the video feed in the GUI."""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_volume_label(self, volume_percentage):
        """Update the volume label in the UI."""
        self.volume_label.setText(f"Volume: {volume_percentage}%")

    def open_settings(self):
        settings_window = SettingsDialog(self)
        settings_window.exec()

    def update_detection_conf(self, value):
        """Update detection confidence dynamically."""
        new_conf = value / 100.0  # Convert back to float for module usage
        update_env_variable("DETECTION_CONF", new_conf)
        self.conf_label.setText(f"Detection Confidence: {value}%")
        self.hand_tracking_thread.update_detection_conf(new_conf)

    def closeEvent(self, event):
        """Ensure the hand tracking thread stops when the GUI is closed."""
        self.hand_tracking_thread.stop()
        self.hand_tracking_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HandTrackingGUI()
    window.show()
    sys.exit(app.exec())
