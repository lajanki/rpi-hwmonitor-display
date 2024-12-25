import json
import logging
import time
import sys

from google.cloud import pubsub_v1

import transport
from transport import hw_stats
from transport.base_publisher import BasePublisher

import utils



logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


class PubSubPublisher(BasePublisher):

    def __init__(self):
        self.client = pubsub_v1.PublisherClient()
        self.topic_path = self.client.topic_path(transport.PROJECT_ID, transport.TOPIC_ID)
    
    def publish(self):
        """Continuously fetch current statistics and publish as message.
        Publish a new message every UPDATE_INTERVAL seconds.
        """
        bytes_generated = 0
        bytes_processed = 0

        # Pub/Sub processes a minimum of 1 000 bytes per push and pull
        # https://cloud.google.com/pubsub/pricing#:~:text=A%20minimum%20of%201000%20bytes,assessed%20regardless%20of%20message%20size
        MIN_PROCESS_SIZE = 1000

        logging.info("Polling started...")
        logging.info("Ctrl-C to exit")
        try:
            while True:
                data = json.dumps(hw_stats.get_stats()).encode("utf-8")
                self.client.publish(self.topic_path, data)

                bytes_generated += len(data)
                bytes_processed += MIN_PROCESS_SIZE  
                time.sleep(transport.UPDATE_INTERVAL)
            
                messages_published = int(bytes_processed/MIN_PROCESS_SIZE)
                megabytes_published = round(bytes_processed/10**6, 2)
                megabytes_generated = round(bytes_generated/10**6, 2)

                # Print statistics overwriting previous line
                print(f"Messages published: {messages_published} ### MB published/generated: {megabytes_published}/{megabytes_generated}", end="\r")
        except KeyboardInterrupt:
            # Send an empty message to clear (static) visuals.
            # Note: the utilization graph history will remain visible.
            print()
            logging.info("Stopping publish")
            # Wait a while to give Pub/Sub time to process recent messages
            time.sleep(transport.UPDATE_INTERVAL)

            logging.info("Sending empty message...")
            data = json.dumps(utils.DEFAULT_MESSAGE).encode("utf-8")
            future = self.client.publish(self.topic_path, data)
            future.result()

            logging.info("Exiting")
            sys.exit()