import argparse
import logging

import transport
import transport.local_network_publisher


logging.basicConfig(
    format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
    level="INFO"
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardware poller")
    parser.add_argument(
        "--transport",
        choices=["LAN", "Pub/Sub"],
        default="LAN",
        help="transport layer to use for publishing hardware readings.",
    )
    parser.add_argument("--host", type=str, help="Socket host and port number for LAN transport in host:port format.")
    args = parser.parse_args()

    # Override host config if provided
    if args.host:
        host, port = args.host.split(":")
        transport.CONFIG["transport"]["socket"] = {
            "host": host,
            "port": int(port)
        }

    TRANSPORT_PUBLISHER_MAP = {
        "LAN": transport.local_network_publisher.LocalNetworkPublisher
    }

    # Only try to import the pubsub module if requested
    if args.transport == "Pub/Sub":
        try:
            import transport.pubsub_publisher
            TRANSPORT_PUBLISHER_MAP["Pub/Sub"] = transport.pubsub_publisher.PubSubPublisher
        except ModuleNotFoundError as e:
            logging.critical("Unable to create a Pub/Sub client.")
            raise

    publisher = TRANSPORT_PUBLISHER_MAP[args.transport]()
    logging.info("Using %s message transport layer", args.transport)


    publisher.publish()
