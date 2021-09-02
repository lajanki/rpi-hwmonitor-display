import os
import json
import logging
import time

from google.cloud import pubsub_v1

import pubsub_utils
from pubsub_utils import hw_stats


publisher = pubsub_v1.PublisherClient()
# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{PROJECT_ID}/topics/{TOPIC_ID}`
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
    total_bytes_generated = 0
    total_bytes_processed = 0

    # pub/sub processes a minimum of 1000B per push and pull
    # https://cloud.google.com/pubsub/pricing#:~:text=A%20minimum%20of%201000%20bytes,assessed%20regardless%20of%20message%20size
    MIN_PROCESS_SIZE = 1000

    logging.info("Polling started...")
    while True:
        message_sizes = []
        for i in range(10):
            data = json.dumps(get_stats()).encode("utf-8")
            future = publisher.publish(topic_path, data)
            message_sizes.append(len(data))

            total_bytes_generated += len(data)
            total_bytes_processed += MIN_PROCESS_SIZE  
            time.sleep(pubsub_utils.UPDATE_INTERVAL)
        
        # Log publish statistics every 10th publish
        avg_size = int(sum(message_sizes) / len(message_sizes))
        total_messages_published = total_bytes_processed/MIN_PROCESS_SIZE
        total_megabytes_published = round(total_bytes_processed/MIN_PROCESS_SIZE**2, 2)

        logging.info("Published a total of %d messages with average size %dB", total_messages_published, avg_size)
        logging.info("Bytes generated: %dB. Megabytes published: %sMB", total_bytes_generated, total_megabytes_published)

