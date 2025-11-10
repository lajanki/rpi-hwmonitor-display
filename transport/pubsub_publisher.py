import logging
import time

from google.cloud import pubsub_v1

import transport
from transport import hw_stats
from transport.base_publisher import BasePublisher
from message_models import MessageModel


logger = logging.getLogger()
REFRESH_INTERVAL = transport.CONFIG["transport"]["refresh_interval"]


class PubSubPublisher(BasePublisher):

    def __init__(self):
        self.client = pubsub_v1.PublisherClient()
        self.topic_path = self.client.topic_path(
            transport.CONFIG["transport"]["pubsub"]["project_id"],
            transport.CONFIG["transport"]["pubsub"]["topic_id"]
        )
    
    def publish(self):
        """Continuously fetch current statistics and publish as message.
        Publish a new message every REFRESH_INTERVAL seconds.
        """
        bytes_generated = 0
        bytes_processed = 0

        # Pub/Sub processes a minimum of 1 000 bytes per push and pull
        # https://cloud.google.com/pubsub/quotas#throughput_quota_units
        MIN_PROCESS_SIZE = 1000

        logger.info("Polling started...")
        logger.info("Ctrl-C to exit")
        try:
            while True:
                data = hw_stats.get_stats().model_dump_json().encode()
                self.client.publish(self.topic_path, data)

                bytes_generated += len(data)
                bytes_processed += MIN_PROCESS_SIZE
                time.sleep(REFRESH_INTERVAL)
            
                messages_published = int(bytes_processed/MIN_PROCESS_SIZE)
                megabytes_published = round(bytes_processed/10**6, 2)
                megabytes_generated = round(bytes_generated/10**6, 2)

                # Print statistics overwriting previous line
                print(f"Messages published: {messages_published} ### MB published/generated: {megabytes_published}/{megabytes_generated}", end="\r")
        except KeyboardInterrupt:
            # Send an empty message to clear static visuals.
            print()
            logger.info("Stopping publish")
            # Wait a while to give Pub/Sub time to process recent messages
            time.sleep(REFRESH_INTERVAL)

            logger.debug("Sending empty message...")
            data = MessageModel().model_dump_json().encode()
            future = self.client.publish(self.topic_path, data)
            future.result()

            logger.info("Exiting")
