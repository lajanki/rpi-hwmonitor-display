import json
import logging
from concurrent.futures import TimeoutError

from google.cloud import pubsub_v1

import pubsub_utils


client = pubsub_v1.SubscriberClient()
subscription_path = client.subscription_path(pubsub_utils.PROJECT_ID, pubsub_utils.SUBSCRIPTION_ID)

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


def pull_message():
    """Pull a single message from the subscription."""
    response = client.pull(
        request={
            "subscription": subscription_path,
            "max_messages": 1,
        },
        timeout=1.0
    )

    ack_ids = [msg.ack_id for msg in response.received_messages]
    client.acknowledge(
        request={
            "subscription": subscription_path,
            "ack_ids": ack_ids,
        }
    )
    data = response.received_messages[0].message.data.decode("utf-8")
    return json.loads(data)

def listen_for_messages(callback):
    """Asynchronous pull: keep listening for messages indefinitely."""
    streaming_pull_future = client.subscribe(subscription_path, callback=callback)
    logging.info(f"Listening for messages on {subscription_path}..\n")

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with client:
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
    listen_for_messages(_log_message)