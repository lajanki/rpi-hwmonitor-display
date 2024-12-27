import argparse
import sys
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import hwmonitorGUI
import message_workers


logging.basicConfig(format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardware monitor")
    parser.add_argument("--fullscreen", action="store_true", help="fullscreen mode")
    parser.add_argument("--debug", action="store_true", help="debug mode")
    parser.add_argument(
        "--transport",
        choices=["LAN", "Pub/Sub"],
        default="Pub/Sub",
        help="transport layer to use for passing hardware readings between client and server.",
    )

    args = parser.parse_args()

    app = QApplication(sys.argv)

    TRANSPORT_WORKER_MAP = {
        "Pub/Sub": message_workers.PubSubWorker,
        "LAN": message_workers.LocalNetworkWorker
    }

    transport_class = TRANSPORT_WORKER_MAP[args.transport]
    logging.info("Using %s message transport layer", args.transport)
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
