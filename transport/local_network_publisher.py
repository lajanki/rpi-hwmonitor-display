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
        """Periodically send hardware metrics, reconnecting after socket failures."""
        HOST = transport.CONFIG["transport"]["socket"]["host"]
        PORT = transport.CONFIG["transport"]["socket"]["port"]

        logger.info("Polling started...")
        logger.info("Ctrl-C to exit")
        try:
            while True:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                        connected = False
                        client.settimeout(5)
                        try:
                            client.connect((HOST, PORT))
                            connected = True
                            logger.info("Connected to %s:%s", HOST, PORT)

                            while True:
                                data = hw_stats.get_stats().model_dump_json().encode()
                                client.sendall(data)
                                time.sleep(REFRESH_INTERVAL)
                        except KeyboardInterrupt:
                            if connected:
                                logger.debug("Sending empty message...")
                                try:
                                    client.sendall(MessageModel().model_dump_json().encode())
                                except OSError:
                                    logger.debug("Unable to clear display: connection unavailable")
                            raise
                except OSError as error:
                    logger.warning(
                        "Connection to %s:%s failed: %s. Retrying in %s seconds",
                        HOST, PORT, error, REFRESH_INTERVAL,
                    )
                time.sleep(REFRESH_INTERVAL)
        except KeyboardInterrupt:
            print()
            logger.info("Stopping publish")
            logger.info("Exiting")
