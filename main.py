import argparse
import sys
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import hwmonitorGUI
import message_workers


logging.basicConfig(format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HWMonitor GUI")
    parser.add_argument("--fullscreen", action="store_true", help="fullscreen mode")
    parser.add_argument("--debug", action="store_true", help="debug mode")
    parser.add_argument(
        "--transport-worker",
        nargs="?",
        choices=["LocalNetworkWorker", "PubSubWorker"],
        default="PubSubWorker",
        help="transport layer to use for passing hardware measurements",
    )

    args = parser.parse_args()

    app = QApplication(sys.argv)
    transport_class = getattr(message_workers, args.transport_worker)
    logging.info("Using %s message transport worker", args.transport_worker)
    hw_monitor = hwmonitorGUI.MainWindow(transport_class)

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
