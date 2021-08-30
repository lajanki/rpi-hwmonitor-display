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

    def pull_message(self):
        """Pull a single message from the subscription."""
        response = self.client.pull(
            request={
                "subscription": self.subscription_path,
                "max_messages": 1,
            },
            timeout=2.0
        )

        ack_ids = [msg.ack_id for msg in response.received_messages]
        self.client.acknowledge(
            request={
                "subscription": self.subscription_path,
                "ack_ids": ack_ids,
            }
        )
        data = response.received_messages[0].message.data.decode("utf-8")
        return json.loads(data)

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


    def listen_for_messages(self, callback):
        """Asynchronous pull: keep listening for messages indefinitely."""
        streaming_pull_future = self.client.subscribe(self.subscription_path, callback=callback)
        logging.info(f"Listening for messages on topic {self.subscription_path}..\n")

        with self.client:
            try:
                # When `timeout` is not set, result() will block indefinitely,
                # unless an exception is encountered first.
                streaming_pull_future.result(timeout=None)
            except TimeoutError:
                streaming_pull_future.cancel()

    def _log_message(message):
        data = json.loads(message.data.decode("utf-8"))
        logging.info(data)
        message.ack()



if __name__ == "__main__":
    s = Subscriber()
    s.listen_for_messages(s._log_message)