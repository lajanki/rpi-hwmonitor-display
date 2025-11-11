import argparse
import sys
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

import hwmonitorGUI
import message_workers
import transport


logging.basicConfig(
    format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    level="INFO"
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardware monitor")
    parser.add_argument("--fullscreen", action="store_true", help="fullscreen mode")
    parser.add_argument("--debug", action="store_true", help="debug mode")
    parser.add_argument(
        "--transport",
        choices=["LAN", "Pub/Sub"],
        default="LAN",
        help="transport layer to use for passing hardware readings between client and server. Defaults to LAN",
    )
    parser.add_argument("--host", type=str, help="Socket host config ip value for LAN transport")

    args = parser.parse_args()

    app = QApplication(sys.argv)

    # Override config host value if provided
    if args.host:
        transport.CONFIG["transport"]["socket"]["host"] = args.host

    TRANSPORT_WORKER_MAP = {
        "LAN": message_workers.LocalNetworkWorker
    }

    # Only try to import the pubsub module if requested
    if args.transport == "Pub/Sub":
        try:
            from google.cloud import pubsub_v1
            TRANSPORT_WORKER_MAP["Pub/Sub"] = message_workers.PubSubWorker
        except ModuleNotFoundError as e:
            logging.critical("Unable to create a Pub/Sub client.")
            raise

    transport_class = TRANSPORT_WORKER_MAP[args.transport]
    logging.info("Using %s message transport layer", args.transport)
    window = hwmonitorGUI.MainWindow(transport_class)
    window.start_worker_threads()

    with open("style.qss") as f:
        window.setStyleSheet(f.read())

    if args.debug:
        logging.getLogger().setLevel("DEBUG")

    if args.fullscreen:
        window.showFullScreen()
        window.setCursor(Qt.BlankCursor)

    window.show()

    res = app.exec_()
    sys.exit(res)
