import json
import logging
from concurrent.futures import TimeoutError

from google.cloud import pubsub_v1

import pubsub_utils


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


class Subscriber:

    def __init__(self):
        self.client = pubsub_v1.SubscriberClient()
        self.subscription_path = self.client.subscription_path(pubsub_utils.PROJECT_ID, pubsub_utils.SUBSCRIPTION_ID)

    def setup_streaming_pull(self, callback):
        """Stream pull messages from the topic. Keep listening for messages indefinitely.
        https://cloud.google.com/pubsub/docs/pull#python
        Args:
            callback (callable): the callback to process the messages
        """
        self.streaming_pull_future = self.client.subscribe(self.subscription_path, callback=callback)
        logging.info(f"Listening for messages on topic {self.subscription_path}...\n")

        with self.client:
            try:
                # When `timeout` is not set, result() will block indefinitely,
                # unless an exception is encountered first.
                self.streaming_pull_future.result(timeout=None)
            except TimeoutError as e:
                self.streaming_pull_future.cancel()  # Trigger the shutdown.
                self.streaming_pull_future.result()  # Block until the shutdown is complete.

    def seek_to_time(self, time):
        """Seek the subscription to a given timestamp in seconds."""
        params = {
            "subscription": self.subscription_path,
            "time": {
                "seconds": time
            }
        }
        seek_request = pubsub_v1.types.SeekRequest(params)
        self.client.seek(seek_request)
