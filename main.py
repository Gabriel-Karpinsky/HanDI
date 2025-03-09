import sys
from PyQt6.QtWidgets import QApplication
from HandTrackingGUI import HandTrackingGUI  # Import the GUI class

def main():
    app = QApplication(sys.argv)
    window = HandTrackingGUI()  # Start the GUI
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()