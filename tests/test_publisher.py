import json
import time
from unittest.mock import patch, Mock

from freezegun import freeze_time
from pytest_schema import schema

from transport import hw_stats, local_network_publisher
from utils import DEFAULT_MESSAGE


@freeze_time("2022-05-13T00:00:00")
@patch("transport.hw_stats.get_stats")
@patch("time.sleep")
@patch("socket.socket")
def test_local_network_publish(mock_socket, mock_sleep, mock_get_stats):
    """Check messages sent to the socket by a LocalNetworkPublisher."""
    # raise a KeyboardInterrut on the sleep call to break the infinite loop
    mock_sleep.side_effect = KeyboardInterrupt()

    # Mock the hw stats call with a dummy dict data
    mock_get_stats.return_value = {"a": 1}

    p = local_network_publisher.LocalNetworkPublisher()
    p.publish()

    s = mock_socket.return_value.__enter__.return_value

    # socket connect
    s.connect.assert_called()

    # true message with timestamp
    msg = json.dumps({"a": 1, "timestamp": time.time()}).encode()
    s.send.assert_any_call(msg)

    # KeyboardInterrupt should send an empty message (without the timestamp)
    final_msg = json.dumps(DEFAULT_MESSAGE).encode()
    s.send.assert_any_call(final_msg)

    # socket close
    s.close.assert_called()

@patch("transport.hw_stats.psutil")
@patch("transport.hw_stats.pynvml")
def test_get_stats_schema(mock_pynvml, mock_psutil):
    """Validate the schema of the main hardware statistics extract function."""
    # Mock pynvml calls
    mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = Mock(used=2*10**6, total=3*10**6)
    mock_pynvml.nvmlDeviceGetUtilizationRates.return_value = Mock(gpu=52)
    mock_pynvml.nvmlDeviceGetTemperature.return_value = 40

    # Mock psutil calls
    mock_psutil.sensors_temperatures.return_value = {
        "coretemp": [Mock(label="#1", current=26), Mock(label="#2", current=28), Mock(label="#3", current=28)]
    }
    mock_psutil.virtual_memory.return_value = Mock(total=5000, used=601, available=2000)
    mock_psutil.getloadavg.return_value = [0.28]


    stats = hw_stats.get_stats()
    expected_schema = schema(
        {
            "cpu": {
                "utilization": int,
                "frequency": int,
                "temperature": int,
                "1_min_load_average": float,
                "num_high_load_cores": int, 
                "cores": {
                    "utilization": list,
                    "frequency": list,
                    "temperature": list
                }
            },
            "ram": {
                "total": int,
                "used": int,
                "available": int
            },
            "gpu": {
                "memory.used": int,
                "memory.total": int,
                "utilization": int,
                "temperature": int
            }
        }
    )
    assert expected_schema.is_valid(stats)
