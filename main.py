import argparse
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import hwmonitorGUI


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HWMonitor GUI")
    parser.add_argument("--fullscreen", action="store_true",
                        help="fullscreen mode")
    parser.add_argument("--debug", action="store_true",
                        help="debug mode")
    args = parser.parse_args()
    kwargs = {"fullscreen": args.fullscreen, "debug": args.debug}

    app = QApplication(sys.argv)
    hw_monitor = hwmonitorGUI.MainWindow()

    if args.fullscreen:
        hw_monitor.showFullScreen()
        hw_monitor.setCursor(Qt.BlankCursor)

    res = app.exec_()
    sys.exit(res)
