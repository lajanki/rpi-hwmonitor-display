from transport import pubsub_publisher


if __name__ == "__main__":
    publisher = pubsub_publisher.PubSubPublisher()
    publisher.publish()
