import os
import json
import logging
import time
import sys

from google.cloud import pubsub_v1

import pubsub_utils
from pubsub_utils import hw_stats


publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(pubsub_utils.PROJECT_ID, pubsub_utils.TOPIC_ID)

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


def get_stats():
    """Gather various CPU, GPU and RAM statistics to a dict to be sent
    as pubsub message.
    """
    stats = hw_stats.EMPTY_TEMPLATE.copy()

    if os.name == "nt":
        import pythoncom
        pythoncom.CoInitialize()

        cpu_gpu = hw_stats._get_cpu_and_gpu_info_wmi()
        stats.update({
            "cpu": cpu_gpu["cpu"],
            "gpu": cpu_gpu["gpu"],
            "ram": hw_stats.get_ram_info()
        })

    else:
        stats.update({
            "cpu": hw_stats._get_cpu_info_psutil(),
            "ram": hw_stats.get_ram_info(),
            "gpu": hw_stats.get_gpu_info()
        })
        
    return stats

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
            future = publisher.publish(topic_path, data)

            bytes_generated += len(data)
            bytes_processed += MIN_PROCESS_SIZE  
            time.sleep(pubsub_utils.UPDATE_INTERVAL)
        
            messages_published = int(bytes_processed/MIN_PROCESS_SIZE)
            megabytes_published = round(bytes_processed/1000**2, 2)
            megabytes_generated = round(bytes_generated/1000**2, 2)

            # Print statistics overwriting previous line
            print(f"Messages published: {messages_published} Megabytes published: {megabytes_published}MB (generated: {megabytes_generated}MB)", end="\r")
    except KeyboardInterrupt:
        print()
        logging.info("Exiting")
        sys.exit()