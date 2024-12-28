import argparse
import logging

import transport.local_network_publisher
import transport.pubsub_publisher


logging.basicConfig(format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", level="INFO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardware poller")
    parser.add_argument(
        "--transport",
        choices=["LAN", "Pub/Sub"],
        default="LAN",
        help="transport layer to use for publishing hardware readings.",
    )

    args = parser.parse_args()


    TRANSPORT_PUBLISHER_MAP = {
        "Pub/Sub": transport.pubsub_publisher.PubSubPublisher,
        "LAN": transport.local_network_publisher.LocalNetworkPublisher
    }

    publisher = TRANSPORT_PUBLISHER_MAP[args.transport]()
    logging.info("Using %s message transport layer", args.transport)


    publisher.publish()
