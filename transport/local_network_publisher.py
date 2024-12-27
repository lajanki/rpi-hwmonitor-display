import json
import logging
import time
import socket
import sys

import transport
from transport import hw_stats
from transport.base_publisher import BasePublisher

import utils



logger = logging.getLogger()


class LocalNetworkPublisher(BasePublisher):

    def __init__(self):
        pass
    
    def publish(self):
        """Periodically send hardware metrics to a socket."""
        HOST = "192.168.100.19"
        PORT = 65432

        logger.info("Polling started...")
        logger.info("Ctrl-C to exit")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))

                while True:
                    readings = hw_stats.get_stats()
                    readings["timestamp"] = time.time()

                    data = json.dumps(readings).encode("utf-8")
                    s.send(data)
                
                    # Print statistics overwriting previous line
                    print(f"bytes sent: {len(data)}", end="\r")
                    time.sleep(transport.UPDATE_INTERVAL)
        except KeyboardInterrupt:
            # Send an empty message to clear static visuals.
            # The utilization graph history will remain visible. (TODO?)
            print()
            logger.info("Stopping publish")
            logger.debug("Sending empty message...")
            data = json.dumps(utils.DEFAULT_MESSAGE).encode("utf-8")
            s.send(data)

            logger.info("Exiting")
            sys.exit()