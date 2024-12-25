import argparse
import sys
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import hwmonitorGUI


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HWMonitor GUI")
    parser.add_argument("--fullscreen", action="store_true",
                        help="fullscreen mode")
    parser.add_argument("--debug", action="store_true",
                        help="debug mode")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    hw_monitor = hwmonitorGUI.MainWindow()
    
    with open("style.qss") as f:
        hw_monitor.setStyleSheet(f.read())

    if args.debug:
        logging.getLogger().setLevel("DEBUG")

    if args.fullscreen:
        hw_monitor.showFullScreen()
        hw_monitor.setCursor(Qt.BlankCursor)

    hw_monitor.show()


    res = app.exec_()
    sys.exit(res)
