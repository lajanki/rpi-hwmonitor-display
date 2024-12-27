import logging
import json
import socket
import time

from PyQt5.QtCore import (
    QObject,
    pyqtSignal
)

import transport
from transport.pubsub_subscriber import Subscriber


logger = logging.getLogger()


class PubSubWorker(QObject):
    """Worker class for Pub/Sub message thread."""
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.subscriber = Subscriber()

    def process_response(self, message):
        """Callback for streaming pull: decode the raw pubsub message
        and emit hardware readings back to the main thread.
        """
        readings = json.loads(message.data.decode("utf-8"))

        # Add pubsub provided message timestamp
        readings["timestamp"] = message.publish_time.timestamp()
        self.update.emit(readings)
        message.ack()

    def run(self):
        self.subscriber.seek_to_time(int(time.time()))
        self.subscriber.setup_streaming_pull(self.process_response)


class LocalNetworkWorker(QObject):
    """Worker class for socket based message thread."""
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    def run(self):
        HOST = transport.CONFIG["transport"]["socket"]["host"]
        PORT = transport.CONFIG["transport"]["socket"]["port"]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen(0)
            conn, addr = s.accept()
            with conn:
                logger.info("Connected by %s", addr)
                while True:
                    data = conn.recv(1024)
                    readings = json.loads(data.decode("utf-8"))
                    self.update.emit(readings)

                    if not data:
                        break
