import time
import json

from PyQt5.QtCore import (
    QObject,
    pyqtSignal
)

from transport.pubsub_subscriber import Subscriber


class PubSubWorker(QObject):
    """Worker class for Pub/Sub thread."""
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.subscriber = Subscriber()

    def process_response(self, message):
        """Callback for streaming pull: emit message back to the main thread."""
        readings = json.loads(message.data.decode("utf-8"))
        readings["timestamp"] = message.publish_time.timestamp()
        self.update.emit(readings)
        message.ack()

    def run(self):
        self.subscriber.seek_to_time(int(time.time()))
        self.subscriber.setup_streaming_pull(self.process_response)