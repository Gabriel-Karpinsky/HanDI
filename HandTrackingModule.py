import cv2
import mediapipe as mp
import time
import numpy as np
import math
import os
from dotenv import load_dotenv
from mido import Message, open_output, get_output_names

# Load environment variables
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=ENV_FILE)
MIDI_PORT_NAME = os.getenv("MIDI_PORT", "Python to VCV 1")

class HandDetector:
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
        self.tipIds = [4, 8, 12, 16, 20]

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)

        return img

    def findPosition(self, img, handNo=0, draw=True):
        self.lmList = []
        xList = []
        yList = []
        bbox = []

        if hasattr(self, "results") and self.results.multi_hand_landmarks:
            if handNo < len(self.results.multi_hand_landmarks):
                myHand = self.results.multi_hand_landmarks[handNo]
                for id, lm in enumerate(myHand.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    xList.append(cx)
                    yList.append(cy)
                    self.lmList.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

                xmin, xmax = min(xList), max(xList)
                ymin, ymax = min(yList), max(yList)
                bbox = (xmin, ymin, xmax, ymax)

                if draw:
                    cv2.rectangle(img, (xmin - 20, ymin - 20), (xmax + 20, ymax + 20), (0, 255, 0), 2)

        return self.lmList, bbox

    def fingersUp(self):
        fingers = []
        if not self.lmList:
            return []

        fingers.append(1 if self.lmList[self.tipIds[0]][1] < self.lmList[self.tipIds[0] - 1][1] else 0)

        for id in range(1, 5):
            fingers.append(1 if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2] else 0)

        return fingers

    def findDistance(self, p1, p2, img=None, draw=True):
        x1, y1 = self.lmList[p1][1:]
        x2, y2 = self.lmList[p2][1:]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw and img is not None:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), 10, (0, 255, 0), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, (x1, y1, x2, y2, cx, cy)

class VolumeController:
    def __init__(self):
        self.volBar = 400
        self.volPercent = 100
        self.color = (255, 0, 0)
        self.midi = MIDITransmiter()

    def set_volume_by_hand_distance(self, lmList, img, detector):
        if len(lmList) >= 21:
            area = (max([pt[1] for pt in lmList]) - min([pt[1] for pt in lmList])) * \
                   (max([pt[2] for pt in lmList]) - min([pt[2] for pt in lmList])) // 100
            if 250 < area < 1000:
                length, img, lineInfo = detector.findDistance(4, 8, img)
                volPercent = np.interp(length, [45, 200], [0, 100])
                volPercent = 2 * round(volPercent / 2)

                fingers = detector.fingersUp()
                if fingers and not fingers[4]:
                    self.midi.send_MIDI_volume(volPercent)
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 10, (0, 255, 0), cv2.FILLED)
                    self.color = (0, 255, 0)
                else:
                    self.color = (255, 0, 0)
                    return None

                self.volBar = np.interp(length, [45, 200], [400, 150])
                self.volPercent = volPercent
                return volPercent

        return None

class MIDITransmiter:
    def __init__(self):
        self.note = 60
        self.playing_notes = set()
        self.midi_out = None
        self.connected = False
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
        self.connected = False

    def send_MIDI_volume(self, MIDI_velocity):
        if not self.connected:
            print("⚠️ Cannot send MIDI — no connection.")
            return
        velocity = int(MIDI_velocity * 126+1)
        self.midi_out.send(Message('note_on', note=self.note, velocity=velocity))
        self.playing_notes.add(self.note)
        print(f"🎵 Playing note {self.note} with velocity {velocity}")

    def send_MIDI_stop(self):
        if not self.connected:
            print("⚠️ Cannot stop MIDI — not connected.")
            return
        for n in self.playing_notes:
            self.midi_out.send(Message('note_on', note=n, velocity=0))
        self.playing_notes.clear()
        self.midi_out.send(Message('control_change', control=123, value=0))
        print("🛑 All notes stopped.")