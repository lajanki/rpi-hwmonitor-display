import logging
import time
import socket

import transport
from transport import hw_stats
from transport.base_publisher import BasePublisher
from message_models import MessageModel


logger = logging.getLogger()
REFRESH_INTERVAL = transport.CONFIG["transport"]["refresh_interval"]
RETRY_INTERVAL = 3


class LocalNetworkPublisher(BasePublisher):

    def __init__(self):
        pass
    
    def publish(self):
        """Send metrics, stopping after the configured consecutive failure limit."""
        HOST = transport.CONFIG["transport"]["socket"]["host"]
        PORT = transport.CONFIG["transport"]["socket"]["port"]
        max_consecutive_failures = transport.CONFIG["transport"]["socket"].get(
            "max_consecutive_failures", 5
        )
        if type(max_consecutive_failures) is not int or max_consecutive_failures < 1:
            raise ValueError("transport.socket.max_consecutive_failures must be a positive integer")
        consecutive_failures = 0

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
                                consecutive_failures = 0
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
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(
                            "Connection to %s:%s failed: %s. Stopping publish after %s consecutive failures",
                            HOST, PORT, error, consecutive_failures,
                        )
                        return
                    logger.warning(
                        "Connection to %s:%s failed: %s (%s/%s consecutive failures). Retrying in %s seconds",
                        HOST, PORT, error, consecutive_failures, max_consecutive_failures, RETRY_INTERVAL,
                    )
                    time.sleep(RETRY_INTERVAL)
        except KeyboardInterrupt:
            print()
            logger.info("Stopping publish")
            logger.info("Exiting")
