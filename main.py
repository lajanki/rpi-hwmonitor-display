import argparse
import sys
import logging

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
    res = app.exec_()

    sys.exit(res)
