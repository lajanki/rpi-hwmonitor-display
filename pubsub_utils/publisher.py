import os
import json
import threading
import logging

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
    if os.name == "nt":
        get_cpu_info = hw_stats._get_cpu_info_wmi
    else:
        get_cpu_info = hw_stats._get_cpu_info_psutil

    return {
        "cpu": get_cpu_info(),
        "ram": hw_stats.get_ram_info(),
        "gpu": hw_stats.get_gpu_info()
    }

def publish_stats():
    """Continuously fetch current statistics and publish as message.
    Publish a new message every UPDATE_INTERVAL seconds.
    """
    data = json.dumps(get_stats()).encode("utf-8")
    # When you publish a message, the client returns a future.
    future = publisher.publish(topic_path, data)
    logging.info(future.result())

    poll()

def poll():
    threading.Timer(pubsub_utils.UPDATE_INTERVAL, publish_stats).start()



if __name__ == "__main__":
    publish_stats()
