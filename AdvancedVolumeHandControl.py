import cv2
import time
import numpy as np
import HandTrackingModule as htm
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

wCam, hCam = 640, 480

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

detector = htm.handDetector(detectionConf = 0.7, maxHands = 1)

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
# volume.GetMute()
# volume.GetMasterVolumeLevel()
volRange = volume.GetVolumeRange()
minVol = volRange[0]
maxVol = volRange[1]
vol = 0
volBar = 400
volPercent = 100
area = 0
volColor = (255, 0, 0)

while True:
    success, img = cap.read()

    # Find hand
    img = detector.findHands(img)
    lmList, bBox = detector.findPosition(img, draw = True)
    if len(lmList) != 0:

        # Filter based on size
        area = (bBox[2] - bBox[0]) * (bBox[3] - bBox[1]) // 100
        # print(bBox)
        if 250 < area < 1000:
            # print("Yes")

            # Find the distance between the index and the thumb
            length, img, lineInfo = detector.findDistance(4, 8, img)
            print(length)

            # Convert the volume
            volBar = np.interp(length, [45, 200], [400, 150])
            volPercent = np.interp(length, [45, 200], [0, 100])

            # Reduce the resolution to make it smoother
            smoothness = 2
            volPercent = smoothness * (round(volPercent / smoothness))

            # Check if the relevant fingers are up
            fingers = detector.fingersUp()
            # print(fingers)

            # If the pinky is down, change the volume
            if not fingers[4]:
                volume.SetMasterVolumeLevel(volPercent / 100, None)
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 10, (0, 255, 0), cv2.FILLED)
                volColor = (0, 255, 0)
            else:
                volColor = (255, 0, 0)

    # Drawings
    # cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)
    # cv2.rectangle(img, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)
    # cv2.putText(img, f'{int(volPercent)}%', (40, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    currVol = int(volume.GetMasterVolumeLevelScalar() * 100)
    cv2.putText(img, f'Volume: {int(currVol)}', (400, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, volColor, 3)

    # Frame rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime

    cv2.putText(img, f'FPS: {int(fps)}', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

    cv2.imshow('Image', img)
    cv2.waitKey(1)