import json
from unittest.mock import patch, Mock

import pytest
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
    sent_msg_data = json.loads(s.sendall.call_args_list[0][0][0].decode())
    sent_msg_timestamp = sent_msg_data.pop("timestamp")

    expected_msg_data = mock_msg.model_dump()
    expected_msg_timestamp = expected_msg_data.pop("timestamp")

    assert sent_msg_data == expected_msg_data
    assert int(sent_msg_timestamp) == int(expected_msg_timestamp)

    # final data send:
    # KeyboardInterrupt should send a default message
    sent_msg_data = json.loads(s.sendall.call_args_list[1][0][0].decode())
    sent_msg_timestamp = sent_msg_data.pop("timestamp")

    default_msg_data = MessageModel().model_dump()
    default_msg_timestamp = default_msg_data.pop("timestamp")

    assert sent_msg_data == default_msg_data
    assert int(sent_msg_timestamp) == int(default_msg_timestamp)

    # socket close
    mock_socket.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("error", [ConnectionRefusedError, BrokenPipeError, ConnectionResetError, TimeoutError])
@patch("transport.hw_stats.get_stats")
@patch("time.sleep")
@patch("socket.socket")
def test_local_network_publish_reconnects(mock_socket, mock_sleep, mock_get_stats, mock_msg_data, error):
    failed_context = Mock()
    failed_context.__enter__ = Mock(return_value=Mock())
    failed_context.__exit__ = Mock(return_value=False)
    connected_context = Mock()
    connected_context.__enter__ = Mock(return_value=Mock())
    connected_context.__exit__ = Mock(return_value=False)
    mock_socket.side_effect = [failed_context, connected_context]
    failed_socket = failed_context.__enter__.return_value
    connected_socket = connected_context.__enter__.return_value
    if error is ConnectionRefusedError:
        failed_socket.connect.side_effect = error()
    else:
        failed_socket.sendall.side_effect = error()
    mock_get_stats.return_value = MessageModel(**mock_msg_data)
    mock_sleep.side_effect = [None, KeyboardInterrupt()]

    local_network_publisher.LocalNetworkPublisher().publish()

    assert mock_socket.call_count == 2
    failed_context.__exit__.assert_called_once()
    connected_context.__exit__.assert_called_once()
    connected_socket.connect.assert_called_once()
    connected_socket.settimeout.assert_called_once_with(5)
    assert connected_socket.sendall.call_count == 2
    mock_sleep.assert_any_call(local_network_publisher.REFRESH_INTERVAL)


@patch("time.sleep", side_effect=KeyboardInterrupt())
@patch("socket.socket")
def test_local_network_publish_interrupts_retry(mock_socket, mock_sleep):
    client = mock_socket.return_value.__enter__.return_value
    client.connect.side_effect = ConnectionRefusedError()

    local_network_publisher.LocalNetworkPublisher().publish()

    mock_sleep.assert_called_once_with(local_network_publisher.REFRESH_INTERVAL)
    client.sendall.assert_not_called()
    mock_socket.return_value.__exit__.assert_called_once()


@patch("transport.hw_stats.get_stats")
@patch("time.sleep", side_effect=KeyboardInterrupt())
@patch("socket.socket")
def test_local_network_publish_ignores_disconnect_on_shutdown(mock_socket, mock_sleep, mock_get_stats):
    client = mock_socket.return_value.__enter__.return_value
    client.sendall.side_effect = [None, BrokenPipeError()]
    mock_get_stats.return_value = MessageModel()

    local_network_publisher.LocalNetworkPublisher().publish()

    assert client.sendall.call_count == 2
    mock_socket.return_value.__exit__.assert_called_once()
