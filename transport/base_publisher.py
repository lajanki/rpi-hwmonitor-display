# Abstract base class for message publishers.

class BasePublisher:

    def publish(self):
        raise NotImplementedError

