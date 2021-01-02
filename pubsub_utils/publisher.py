import json
import threading
import argparse
import logging

import psutil
import gpustat
from google.cloud import pubsub_v1
import pynvml

import pubsub_utils


publisher = pubsub_v1.PublisherClient()
# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{PROJECT_ID}/topics/{TOPIC_ID}`
topic_path = publisher.topic_path(pubsub_utils.PROJECT_ID, pubsub_utils.TOPIC_ID)

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")

# GPU statistics is based on NVIDIA library, disable if unable to load nvml
IGNORE_GPU = False
try:
    pynvml.nvmlInit()
except pynvml.NVMLError_LibraryNotFound:
    logging.warning("NVML library not found, disabling GPU statistics")
    IGNORE_GPU = True


def get_stats():
    """Gather various CPU, GPU and RAM statistics to a dict to be sent
    as pubsub message.
    """
    stats = {
        "cpu": {"utilization": [], "freq": [], "temperature": []},
        "ram": {},
        "gpu": {}
    }

    # CPU statistics per core
    cpu_percent = psutil.cpu_percent(percpu=True)
    cpu_freq = psutil.cpu_freq(percpu=True)

    cpu_temps = psutil.sensors_temperatures()
    core_temps = [item.current for item in cpu_temps["coretemp"] if "Core" in item.label]

    for i, core in enumerate(cpu_percent):
        stats["cpu"]["utilization"].append(int(cpu_percent[i]))
        stats["cpu"]["freq"].append(int(cpu_freq[i].current))
        stats["cpu"]["temperature"].append(int(core_temps[i]))

    # RAM (in megabytes)
    mem = psutil.virtual_memory()
    stats["ram"] = {
        "total": int(mem.total / 1000**2),
        "used": int(mem.used / 1000**2),
        "available": int(mem.available / 1000**2)
    }

    # GPU
    if not IGNORE_GPU:
        gpustats = gpustat.GPUStatCollection.new_query().jsonify()
        stats["gpu"] = {
            "memory.used": gpustats["gpus"][0]["memory.used"],
            "memory.total": gpustats["gpus"][0]["memory.total"],
            "utilization": gpustats["gpus"][0]["utilization.gpu"],
            "temperature": gpustats["gpus"][0]["temperature.gpu"]
        }

    else:
        stats["gpu"] = {
            "memory.used": 0,
            "memory.total": 1, # non zero value to avoid division by zero
            "utilization": 0,
            "temperature": 0
        }

    return stats

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
