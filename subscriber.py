import os
import json
import logging
from concurrent.futures import TimeoutError

from dotenv import load_dotenv
from google.cloud import pubsub_v1


load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")

logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")

subscriber = pubsub_v1.SubscriberClient()
# The `subscription_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/subscriptions/{subscription_id}`
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

def log_message(message):
    #print(f"Received {message}.")
    data = json.loads(message.data.decode("utf-8"))
    logging.info(data)
    message.ack()

def listen_for_messages(callback):
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logging.info(f"Listening for messages on {subscription_path}..\n")

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result(timeout=None)
        except TimeoutError:
            streaming_pull_future.cancel()


if __name__ == "__main__":
    listen_for_messages(log_message)