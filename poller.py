import logging

from transport import pubsub_publisher


logging.basicConfig(format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", level="INFO")


if __name__ == "__main__":
    publisher = pubsub_publisher.PubSubPublisher()
    publisher.publish()
