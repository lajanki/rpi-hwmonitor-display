import json
import logging
import time
import sys

from google.cloud import pubsub_v1

import pubsub_utils
from pubsub_utils import hw_stats
import utils


publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(pubsub_utils.PROJECT_ID, pubsub_utils.TOPIC_ID)

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


def get_stats():
    """Gather various CPU, GPU and RAM statistics to a dict to be sent
    as pubsub message.
    """
    return {
        "cpu": hw_stats.get_cpu_info(),
        "ram": hw_stats.get_ram_info(),
        "gpu": hw_stats.get_gpu_info()
    }
        
def publish_stats():
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
            data = json.dumps(get_stats()).encode("utf-8")
            publisher.publish(topic_path, data)

            bytes_generated += len(data)
            bytes_processed += MIN_PROCESS_SIZE  
            time.sleep(pubsub_utils.UPDATE_INTERVAL)
        
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
        time.sleep(pubsub_utils.UPDATE_INTERVAL)

        logging.info("Sending empty message...")
        data = json.dumps(utils.DEFAULT_MESSAGE).encode("utf-8")
        future = publisher.publish(topic_path, data)
        future.result()

        logging.info("Exiting")
        sys.exit()