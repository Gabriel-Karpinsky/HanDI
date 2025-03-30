import sys
import os
import cv2
import numpy as np
from dotenv import load_dotenv, set_key
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QCheckBox, QSlider
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import HandTrackingModule as htm

# Load environment variables from .env
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=ENV_FILE)

def update_env_variable(key, value):
    set_key(ENV_FILE, key, str(value))
    load_dotenv(ENV_FILE, override=True)

def get_available_cameras(max_index=10):
    """
    Returns a list of (index, name) for each camera that can be opened.
    Uses pygrabber on Windows if possible for friendly names, else fallback.
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
    except:
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, f"Camera {i}"))
                cap.release()
    return available

# -----------------------------------------------------------------------
#  GESTURE SETTINGS UI
# -----------------------------------------------------------------------
AVAILABLE_GESTURES = ["Bounding Box", "Pinch", "Fist"]
AVAILABLE_CONTINUOUS_MIDI_PARAMS = ["Volume", "Octave", "Modulation"]

class GestureSettingRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout()

        self.gesture_combo = QComboBox()
        self.gesture_combo.addItems(AVAILABLE_GESTURES)
        self.gesture_combo.currentTextChanged.connect(self.on_gesture_changed)
        self.layout.addWidget(self.gesture_combo)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems([str(i) for i in range(1, 17)])
        self.layout.addWidget(QLabel("Ch:"))
        self.layout.addWidget(self.channel_combo)

        self.continuous_param_combo = QComboBox()
        self.continuous_param_combo.addItems(AVAILABLE_CONTINUOUS_MIDI_PARAMS)
        self.layout.addWidget(self.continuous_param_combo)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        self.layout.addWidget(self.active_checkbox)

        self.remove_button = QPushButton("Remove")
        self.layout.addWidget(self.remove_button)

        self.setLayout(self.layout)
        self.on_gesture_changed(self.gesture_combo.currentText())

    def on_gesture_changed(self, gesture):
        if gesture in ["Bounding Box", "Pinch"]:
            self.continuous_param_combo.show()
        else:
            self.continuous_param_combo.hide()

    def get_settings(self):
        gesture_name = self.gesture_combo.currentText()
        if gesture_name in ["Bounding Box", "Pinch"]:
            midi_param = self.continuous_param_combo.currentText()
        else:
            midi_param = None
        return {
            "gesture": gesture_name,
            "active": self.active_checkbox.isChecked(),
            "midi_param": midi_param,
            "channel": int(self.channel_combo.currentText()) - 1
        }

class GestureSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.rows = []

        self.add_button = QPushButton("+ Add Gesture")
        self.add_button.clicked.connect(self.add_row)

        self.add_row()
        self.layout.addWidget(self.add_button)

    def add_row(self):
        row = GestureSettingRow()
        row.remove_button.clicked.connect(lambda: self.remove_row(row))
        self.rows.append(row)
        idx = self.layout.indexOf(self.add_button)
        self.layout.insertWidget(idx, row)

    def remove_row(self, row):
        if row in self.rows:
            self.rows.remove(row)
            row.setParent(None)

    def get_all_settings(self):
        return [r.get_settings() for r in self.rows]

# -----------------------------------------------------------------------
#  HAND TRACKING THREAD
# -----------------------------------------------------------------------

class HandTrackingThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, camera_index=0, detection_conf=0.7, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.detection_conf = detection_conf
        self.detector = htm.HandDetector(detectionConf=self.detection_conf)
        self.midi = htm.MIDITransmiter()
        self.gesture_collection = htm.GestureCollection([])
        self.running = True
        self.cap = None
        self.init_camera()

    def init_camera(self):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"\u26a0\ufe0f ERROR: Could not open camera index {self.camera_index}")

    def set_gesture_collection(self, gesture_collection: htm.GestureCollection):
        self.gesture_collection = gesture_collection

    def update_camera_index(self, new_index):
        self.camera_index = new_index
        update_env_variable("CAMERA_INDEX", new_index)
        self.init_camera()

    def set_detection_conf(self, new_conf):
        self.detection_conf = new_conf
        update_env_variable("DETECTION_CONF", new_conf)
        self.detector = htm.HandDetector(detectionConf=new_conf)
        print(f"Updated detection confidence to {new_conf}")

    def run(self):
        while self.running:
            try:
                success, frame = self.cap.read()
                if not success:
                    print("\u26a0\ufe0f ERROR: Failed to capture frame. Reinitializing camera...")
                    self.init_camera()
                    continue

                frame = cv2.flip(frame, 1)
                frame = self.detector.findHands(frame, draw=True)
                lmList, _ = self.detector.findPosition(frame, draw=True)

                if len(lmList) >= 21:
                    dist, frame, _ = self.detector.findDistance(4, 8, frame, draw=True)

                self.gesture_collection.update(lmList)
                self.frame_signal.emit(frame)
            except Exception as e:
                print(f"❌ Exception in hand tracking thread: {e}")
                self.init_camera()
        self.cap.release()

    def stop(self):
        self.running = False

# -----------------------------------------------------------------------
#  MAIN GUI
# -----------------------------------------------------------------------

class HandTrackingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hand Tracking MIDI Controller")
        self.setGeometry(100, 100, 900, 700)

        self.video_label = QLabel("Video Feed")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)

        # Dynamic feedback layout
        self.feedback_layout = QHBoxLayout()
        self.feedback_labels = {}

        self.camera_combo = QComboBox()
        cameras = get_available_cameras()
        for idx, name in cameras:
            self.camera_combo.addItem(f"{name} (Index {idx})", idx)
        current_cam = int(os.getenv("CAMERA_INDEX", 0))
        i_cam = self.camera_combo.findData(current_cam)
        if i_cam >= 0:
            self.camera_combo.setCurrentIndex(i_cam)
        self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)

        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(1, 100)
        slider_val = int(float(os.getenv("DETECTION_CONF", 0.7)) * 100)
        self.conf_slider.setValue(slider_val)
        self.conf_slider.valueChanged.connect(self.on_conf_changed)
        self.conf_label = QLabel(f"Detection Confidence: {slider_val}%")

        self.gesture_settings_widget = GestureSettingsWidget()
        self.apply_button = QPushButton("Apply Gesture Settings")
        self.apply_button.clicked.connect(self.on_apply_gestures)

        self.stop_button = QPushButton("MIDI STOP")
        self.stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.stop_button.clicked.connect(self.on_midi_stop)

        layout = QVBoxLayout()
        cam_layout = QHBoxLayout()
        cam_layout.addWidget(QLabel("Camera:"))
        cam_layout.addWidget(self.camera_combo)
        cam_layout.addWidget(self.conf_label)
        cam_layout.addWidget(self.conf_slider)
        layout.addLayout(cam_layout)

        layout.addWidget(self.video_label)
        layout.addLayout(self.feedback_layout)
        layout.addWidget(self.gesture_settings_widget)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

        self.hand_tracking_thread = HandTrackingThread(
            camera_index=current_cam,
            detection_conf=slider_val / 100.0
        )
        self.hand_tracking_thread.frame_signal.connect(self.display_frame)
        self.hand_tracking_thread.start()

    def on_camera_changed(self):
        new_idx = self.camera_combo.currentData()
        self.hand_tracking_thread.update_camera_index(new_idx)

    def on_conf_changed(self, value):
        new_conf = value / 100.0
        self.conf_label.setText(f"Detection Confidence: {value}%")
        self.hand_tracking_thread.set_detection_conf(new_conf)

    def on_apply_gestures(self):
        settings_list = self.gesture_settings_widget.get_all_settings()
        print("Applying gesture settings:", settings_list)

        while self.feedback_layout.count():
            item = self.feedback_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.feedback_labels = {}

        new_gestures = []
        detector = self.hand_tracking_thread.detector
        midi = self.hand_tracking_thread.midi

        for s in settings_list:
            if not s["active"]:
                continue
            name = s["gesture"]
            param = s["midi_param"]
            chan = s["channel"]

            if name == "Bounding Box":
                def bounding_box_func(lmList):
                    detector.lmList = lmList
                    return detector.get_bounding_box_volume()

                feedback_key = f"{name}_{param}_ch{chan}"
                label = QLabel(f"{name} {param}: ???")
                self.feedback_labels[feedback_key] = label
                self.feedback_layout.addWidget(label)

                def bounding_box_callback(value, ch=chan, key=feedback_key, name=name, param=param):
                    cc_map = {"Volume": 7, "Octave": 15, "Modulation": 1}
                    midi.send_cc(value, control=cc_map[param], channel=ch)
                    self.feedback_labels[key].setText(f"{name} {param}: {int(value * 100)}%")


                gesture_obj = htm.ContinuousGesture(bounding_box_func, bounding_box_callback)
                new_gestures.append(gesture_obj)

            elif name == "Pinch":
                def pinch_func(lmList):
                    detector.lmList = lmList
                    if len(lmList) < 21:
                        return None
                    dist, _, _ = detector.findDistance(4, 8, None, draw=False)
                    if dist < 20 or dist > 220:
                        return None
                    val = np.interp(dist, [20, 220], [0, 1])
                    return val

                feedback_key = f"{name}_{param}_ch{chan}"
                label = QLabel(f"{name} {param}: ???")
                self.feedback_labels[feedback_key] = label
                self.feedback_layout.addWidget(label)

                def pinch_callback(value, ch=chan, key=feedback_key, name=name, param=param):
                    cc_map = {"Volume": 7, "Octave": 15, "Modulation": 1}
                    midi.send_cc(value, control=cc_map[param], channel=ch)
                    self.feedback_labels[key].setText(f"{name} {param}: {int(value * 100)}%")

                gesture_obj = htm.ContinuousGesture(pinch_func, pinch_callback)
                new_gestures.append(gesture_obj)

            elif name == "Fist":
                def fist_bool(lmList):
                    detector.lmList = lmList
                    return detector.is_fist()

                def fist_trigger():
                    midi.send_fist()
                    print("Fist Triggered!")

                gesture_obj = htm.BinaryGesture(fist_bool, fist_trigger)
                new_gestures.append(gesture_obj)

        collection = htm.GestureCollection(new_gestures)
        self.hand_tracking_thread.set_gesture_collection(collection)

    def on_midi_stop(self):
        self.hand_tracking_thread.midi.send_stop()

    def display_frame(self, frame):
        frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = w * ch
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    def closeEvent(self, event):
        self.hand_tracking_thread.stop()
        self.hand_tracking_thread.wait()
        event.accept()

# -----------------------------------------------------------------------
#  MAIN
# -----------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = HandTrackingGUI()
    win.show()
    sys.exit(app.exec())