import cv2
import mediapipe as mp
import time
import numpy as np
import math
import os
from dotenv import load_dotenv
from mido import Message, open_output, get_output_names
from cvzone.ClassificationModule import Classifier

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

        # Load classifier
        self.classifier = Classifier("Model/keras_model.h5", "Model/labels.txt")
        self.labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "4", "5"]
        self.offset = 20
        self.imgSize = 300

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

    def classify_gesture(self, img):
        hands = []
        imgOutput = img.copy()
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                xList = [int(lm.x * img.shape[1]) for lm in handLms.landmark]
                yList = [int(lm.y * img.shape[0]) for lm in handLms.landmark]
                bbox = min(xList), min(yList), max(xList) - min(xList), max(yList) - min(yList)

                x, y, w, h = bbox
                imgWhite = np.ones((self.imgSize, self.imgSize, 3), np.uint8) * 255
                imgCrop = img[y - self.offset: y + h + self.offset, x - self.offset: x + w + self.offset]

                aspectRatio = h / w

                if aspectRatio > 1:
                    k = self.imgSize / h
                    wCal = math.ceil(k * w)
                    imgResize = cv2.resize(imgCrop, (wCal, self.imgSize))
                    wGap = math.ceil((self.imgSize - wCal) / 2)
                    imgWhite[:, wGap: wCal + wGap] = imgResize
                else:
                    k = self.imgSize / w
                    hCal = math.ceil(k * h)
                    imgResize = cv2.resize(imgCrop, (self.imgSize, hCal))
                    hGap = math.ceil((self.imgSize - hCal) / 2)
                    imgWhite[hGap: hCal + hGap, :] = imgResize

                prediction, index = self.classifier.getPrediction(imgWhite, draw=False)
                cv2.putText(imgOutput, self.labels[index], (x, y - 25), cv2.FONT_HERSHEY_COMPLEX, 2, (255, 0, 255), 2)
                cv2.rectangle(imgOutput, (x - self.offset, y - self.offset), 
                              (x + w + self.offset, y + h + self.offset), (255, 0, 255), 4)

                hands.append({"bbox": bbox, "label": self.labels[index]})

        return imgOutput, hands


# Example usage
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    detector = HandDetector(maxHands=1)

    while True:
        success, img = cap.read()
        if not success:
            break

        img, hands = detector.classify_gesture(img)
        cv2.imshow("Hand Gesture Classification", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()