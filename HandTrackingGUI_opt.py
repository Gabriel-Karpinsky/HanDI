import sys
import os
import cv2
import mediapipe as mp
import numpy as np
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal
import queue
import HandTrackingModule as htm  # Import your custom module

# Load environment variables
ENV_FILE = ".env"
load_dotenv(ENV_FILE)

class FrameCaptureThread(QThread):
    """Thread for capturing frames from the camera"""
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, camera_index):
        super().__init__()
        self.camera_index = camera_index
        self.running = True
        self.cap = cv2.VideoCapture(self.camera_index)

    def run(self):
        while self.running:
            success, frame = self.cap.read()
            if success:
                frame = cv2.flip(frame, 1)  # Flip for better UX
                self.frame_signal.emit(frame)  # Send frame to processing thread

    def stop(self):
        self.running = False
        self.cap.release()

class HandProcessingThread(QThread):
    """Thread for detecting and tracking hands"""
    processed_frame_signal = pyqtSignal(np.ndarray)
    volume_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.detector = htm.HandDetector(detectionConf=0.7)
        self.volume_controller = htm.VolumeController()
        self.frame_queue = queue.Queue(maxsize=2)  # Store only 2 frames at a time
        self.running = True

    def run(self):
        while self.running:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()  # Get latest frame

                # Process only every other frame for better performance
                if self.frame_queue.qsize() < 2:
                    frame = self.detector.findHands(frame)  # Full detection
                    lmList = self.detector.findPosition(frame, draw=False)

                    if lmList:
                        volume_percentage = self.volume_controller.set_volume_by_hand_distance(lmList)
                        if volume_percentage is not None:
                            self.volume_signal.emit(int(volume_percentage))

                self.processed_frame_signal.emit(frame)  # Send processed frame to GUI

    def add_frame(self, frame):
        """Add new frame to the queue for processing"""
        if self.frame_queue.full():
            self.frame_queue.get()  # Remove old frame
        self.frame_queue.put(frame)  # Add latest frame

    def stop(self):
        self.running = False

class HandTrackingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Tracking GUI")
        self.setGeometry(100, 100, 800, 600)

        # UI Elements
        self.video_label = QLabel(self)
        self.volume_label = QLabel("Volume: 100%")
        self.settings_button = QPushButton("Settings")

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.volume_label)
        layout.addWidget(self.settings_button)
        self.setLayout(layout)

        # Initialize Threads
        self.capture_thread = FrameCaptureThread(int(os.getenv("CAMERA_INDEX", 0)))
        self.processing_thread = HandProcessingThread()

        # Connect Signals
        self.capture_thread.frame_signal.connect(self.processing_thread.add_frame)
        self.processing_thread.processed_frame_signal.connect(self.display_frame)
        self.processing_thread.volume_signal.connect(self.update_volume_label)

        # Start Threads
        self.capture_thread.start()
        self.processing_thread.start()

    def display_frame(self, frame):
        """Update the video feed in the GUI"""
        h, w, ch = frame.shape
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert only once
        qt_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def update_volume_label(self, volume_percentage):
        """Update the volume label"""
        self.volume_label.setText(f"Volume: {volume_percentage}%")

    def closeEvent(self, event):
        """Ensure threads stop when the GUI is closed"""
        self.capture_thread.stop()
        self.processing_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HandTrackingGUI()
    window.show()
    sys.exit(app.exec())





