import cv2
import threading
import time

class CameraStream:
    def __init__(self, src, width=640, height=480):
        self.capture = cv2.VideoCapture(src)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        #self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ret, self.frame = self.capture.read()  
        #self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            self.ret, self.frame = self.capture.read()

    def get_frame(self):
        return self.ret, self.frame

    #def stop(self):
        #self.running = False
        #self.thread.join()
        #self.capture.release()



camera1 = CameraStream(0)  
camera2 = CameraStream(1)

startTime = time.time()
dtav = 0

while True:
    ret1, frame1 = camera1.get_frame()
    ret2, frame2 = camera2.get_frame()

    if ret1 or ret2:
        dt = time.time() - startTime
        startTime = time.time()
        dtav=.9*dtav+.1*dt
        if dtav > 0:
            fps=1/dtav
        #else:
            #fps=0
        cv2.imshow("Camera 1", frame1)
        cv2.imshow("Camera 2", frame2)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break


camera1.capture.release()
camera2.capture.release()
cv2.destroyAllWindows()