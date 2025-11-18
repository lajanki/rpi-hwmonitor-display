import json
import logging
import time
import socket

import transport
from transport import hw_stats
from transport.base_publisher import BasePublisher
from message_models import MessageModel


logger = logging.getLogger()
REFRESH_INTERVAL = transport.CONFIG["transport"]["refresh_interval"]


class LocalNetworkPublisher(BasePublisher):

    def __init__(self):
        pass
    
    def publish(self):
        """Periodically send hardware metrics to a socket."""
        HOST = transport.CONFIG["transport"]["socket"]["host"]
        PORT = transport.CONFIG["transport"]["socket"]["port"]

        logger.info("Polling started...")
        logger.info("Ctrl-C to exit")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))

                while True:
                    data = hw_stats.get_stats().model_dump_json().encode()
                    s.send(data)
                    time.sleep(REFRESH_INTERVAL)

            except KeyboardInterrupt:
                # Send an empty message to clear static visuals.
                # The utilization graph history will remain visible. (TODO?)
                print()
                logger.info("Stopping publish")
                logger.debug("Sending empty message...")
                data = MessageModel().model_dump_json().encode()
                s.send(data)
                s.close()

                logger.info("Exiting")
            # server socket was closed
            except BrokenPipeError:
                logger.critical("Connection closed")
                logger.info("Exiting")
            # server is not ready to accept connections
            except ConnectionRefusedError:
                logger.critical("Connection refused. Is the server running?")
