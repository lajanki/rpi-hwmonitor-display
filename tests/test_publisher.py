import json
from unittest.mock import patch, Mock

from freezegun import freeze_time

from transport import hw_stats, local_network_publisher
from message_models import MessageModel



@freeze_time("2022-05-13T00:00:00")
@patch("transport.hw_stats.get_stats")
@patch("time.sleep")
@patch("socket.socket")
def test_local_network_publish(mock_socket, mock_sleep, mock_get_stats, mock_msg_data):
    """Check messages sent to the socket by a LocalNetworkPublisher."""
    # raise a KeyboardInterrut on the sleep call to break the infinite loop
    mock_sleep.side_effect = KeyboardInterrupt()

    mock_msg = MessageModel(**mock_msg_data)
    mock_get_stats.return_value = mock_msg

    p = local_network_publisher.LocalNetworkPublisher()
    p.publish()

    s = mock_socket.return_value.__enter__.return_value

    # socket connect
    s.connect.assert_called()

    # 1st data send
    # Compare messages without the timestamp as the fractional part might not match
    # TODO: use time_ns and nanoseconds instead?
    sent_msg_data = json.loads(s.send.call_args_list[0][0][0].decode())
    sent_msg_timestamp = sent_msg_data.pop("timestamp")

    expected_msg_data = mock_msg.model_dump()
    expected_msg_timestamp = expected_msg_data.pop("timestamp")

    assert sent_msg_data == expected_msg_data
    assert int(sent_msg_timestamp) == int(expected_msg_timestamp)

    # final data send:
    # KeyboardInterrupt should send a default message
    sent_msg_data = json.loads(s.send.call_args_list[1][0][0].decode())
    sent_msg_timestamp = sent_msg_data.pop("timestamp")

    default_msg_data = MessageModel().model_dump()
    default_msg_timestamp = default_msg_data.pop("timestamp")

    assert sent_msg_data == default_msg_data
    assert int(sent_msg_timestamp) == int(default_msg_timestamp)

    # socket close
    s.close.assert_called()
