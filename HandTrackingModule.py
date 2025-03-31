import cv2
import mediapipe as mp
import math
import numpy as np
import os
from dotenv import load_dotenv
from mido import Message, open_output, get_output_names

# Load environment variable
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=ENV_FILE)
MIDI_PORT_NAME = os.getenv("MIDI_PORT", "Python to VCV 1")

class HandDetector:
    """
    Handles all low-level hand detection with MediaPipe, plus the actual
    geometry or logic for each gesture (bounding box volume, pinch, fist, etc.)
    """
    def __init__(self, mode=False, maxHands=2, detectionConf=0.5, trackConf=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionConf = detectionConf
        self.trackConf = trackConf

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            min_detection_confidence=self.detectionConf,
            min_tracking_confidence=self.trackConf
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.lmList = []  # landmarks for the current frame
        self.results = None
        self.prev_norm_length = None
        self.prev_length = None

    def findHands(self, img, draw=True):
        """
        Runs MediaPipe detection on the image, optionally drawing the
        connections on `img` in-place, then returns that same `img`.
        """
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img


    def fingersUp(self):
        fingers = []
        if not self.lmList:
            return []

        fingers.append(1 if self.lmList[self.tipIds[0]][1] < self.lmList[self.tipIds[0] - 1][1] else 0)

        for id in range(1, 5):
            fingers.append(1 if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2] else 0)

        return fingers

    def findDistance(self, p1, p2, img=None, draw=True):
        threshold = 0.1
        if not self.lmList or len(self.lmList) < 21:
            return None, img, None

        x1, y1 = self.lmList[p1][1:]
        x2, y2 = self.lmList[p2][1:]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        length = np.hypot(x2 - x1, y2 - y1)

        # Compute hand width for normalization
        x_values = [pt[1] for pt in self.lmList]
        hand_width = max(x_values) - min(x_values)


        # Ensure hand width is valid
        if hand_width < 50:
            return self.prev_length, img, None  # Return last known value

        # Normalize distance
        normalized_length = length / hand_width

        # Check if normalized length change is significant
        if self.prev_norm_length is None or abs(normalized_length - self.prev_norm_length) > threshold:
            self.prev_norm_length = normalized_length  # Update stored normalized length
            self.prev_length = length  # Update stored raw length
        else:
            length = self.prev_length  # Use previous value if change is small

        return length, img, (x1, y1, x2, y2, cx, cy)

    
    def findPosition(self, img, handNo=0, draw=True):
        """
        Populates self.lmList with all the landmarks for the `handNo`-th hand.
        Returns (lmList, bbox), where:
          - lmList is a list of [id, x, y]
          - bbox is (xmin, ymin, xmax, ymax)
        """
        self.lmList = []
        xList = []
        yList = []
        bbox = []
        if self.results and self.results.multi_hand_landmarks:
            if handNo < len(self.results.multi_hand_landmarks):
                myHand = self.results.multi_hand_landmarks[handNo]
                h, w, c = img.shape
                for idx, lm in enumerate(myHand.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    self.lmList.append([idx, cx, cy])
                    xList.append(cx)
                    yList.append(cy)
                    if draw:
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)
                if xList and yList:
                    xmin, xmax = min(xList), max(xList)
                    ymin, ymax = min(yList), max(yList)
                    bbox = (xmin, ymin, xmax, ymax)
                    if draw:
                        cv2.rectangle(img, (xmin - 20, ymin - 20),
                                      (xmax + 20, ymax + 20),
                                      (0, 255, 0), 2)
        return self.lmList, bbox

    # -----------------------------------------------------------------------
    #  GESTURE DETECTION FUNCTIONS
    # -----------------------------------------------------------------------

    def get_bounding_box_volume(self):
        """
        Continuous gesture:
          - Takes the bounding box area of the detected hand and maps it to [0..1].
          - Returns None if no hand found or area is out of a typical range.
        """
        if not self.lmList:
            return None
        xs = [pt[1] for pt in self.lmList]
        ys = [pt[2] for pt in self.lmList]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))

        # Simple range check to ignore extremely small or large detection
        if area < 1000 or area > 30000:
            return None

        # Map area range [1000..30000] to [0..1]
        # Adjust numbers as needed for your camera/distance
        value = np.interp(area, [1000, 30000], [0, 1])
        return value


    def is_fist(self) -> bool:
        """
        Binary gesture:
          - Returns True if all fingers are down.
        """
        if not self.lmList or len(self.lmList) < 21:
            return False
        # Simple finger check: if bounding box is tall but narrow => likely closed
        # Or you could do a more advanced method like finger counting:
        #   thumb tip x < something, etc.
        # For demonstration, let's do a quick 'finger up' approach:
        # Tip IDs: [4, 8, 12, 16, 20]
        # We'll say if the tip is above/below certain joints => 0 or 1
        # but here's a simpler bounding box approach:
        xs = [pt[1] for pt in self.lmList]
        ys = [pt[2] for pt in self.lmList]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        # If width is < some threshold relative to height => likely a fist
        # tune the threshold to your liking
        if w < (h * 0.5):
            return True
        return False


class MIDITransmiter:
    """
    Handles raw MIDI I/O. The rest of your code can call these methods
    (e.g., send volume, send a 'fist' message, etc.).
    """
    def __init__(self):
        self.connected = False
        self.midi_out = None
        self.connect()

    def connect(self):
        ports = get_output_names()
        print("Available MIDI Ports:", ports)
        for port in ports:
            if MIDI_PORT_NAME in port:
                try:
                    self.midi_out = open_output(port)
                    self.connected = True
                    print(f"Connected to MIDI port: {port}")
                    return
                except Exception as e:
                    print(f"Failed to open MIDI port: {e}")
        print("MIDI connection failed. Port not found.")

    def send_stop(self):
        if not self.connected:
            print("⚠️ Can't send stop — no connection.")
            return
        for ch in range(16):
            for note in range(128):
                self.midi_out.send(Message('note_off', note=note, velocity=0, channel=ch))
        print("🛑 Sent note_off to all notes on all channels.")


    def send_volume(self, fraction: float, channel=0):
        if not self.connected:
            print("⚠️ Can't send volume — no connection.")
            return
        vel = int(fraction * 127)
        self.midi_out.send(Message('control_change',control = 7, channel=channel, value=vel))
        print(f"🎵 Volume =>CC7, ch{channel} velocity={vel}")

    def send_octave(self, fraction: float, channel=0):
        # Convert fraction to a control value or note, e.g. 0..127
        val = int(fraction * 127)
        # For example, control=15 => "octave" in your synth
        self.midi_out.send(Message('control_change', control=15, channel=channel, value=val))
        print(f"Octave => CC15, ch{channel} value={val}")

    def send_modulation(self, fraction: float, channel=0):
        # Typically modulation wheel is CC=1
        val = int(fraction * 127)
        self.midi_out.send(Message('control_change',control=1, channel=channel, value=val))
        print(f"Modulation => CC1, value={val}")
    
    def send_cc(self, fraction: float, control: int, channel=0):
        if not self.connected:
            print(f"⚠️ Can't send CC{control} — no connection.")
            return
        value = int(fraction * 127)
        self.midi_out.send(Message('control_change', control=control, channel=channel, value=value))
        print(f"🎛️ CC{control}, ch{channel} => value={value}")


    def send_fist(self):
        """
        Example binary message for a 'fist' gesture.
        """
        if not self.connected:
            print("⚠️ Can't send fist — no connection.")
            return
        self.send_stop()
        print("👊 Fist => note=61, velocity=127")


# ------------------------------------------------------------------------
#  GESTURE CLASSES: BINARY & CONTINUOUS
# ------------------------------------------------------------------------

class BinaryGesture:
    def __init__(self, detector_func, on_trigger):
        self.detector_func = detector_func
        self.on_trigger = on_trigger
        self.old_state = False

    def update(self, lmList):
        current_state = self.detector_func(lmList)
        if current_state and not self.old_state:
            self.on_trigger()
        self.old_state = current_state


class ContinuousGesture:
    def __init__(self, detector_func, on_value):
        self.detector_func = detector_func
        self.on_value = on_value

    def update(self, lmList):
        value = self.detector_func(lmList)
        if value is not None:
            self.on_value(value)



class GestureCollection:
    """
    Maintains a list of arbitrary gesture objects (BinaryGesture or ContinuousGesture).
    You call .update(lmList) each frame, and each gesture object checks if it should send MIDI.
    """
    def __init__(self, gesture_list):
        self.gestures = gesture_list

    def update(self, lmList):
        for gesture in self.gestures:
            gesture.update(lmList)
