import pytest
from unittest.mock import patch, Mock

from pytest_schema import schema

from transport import hw_stats


@patch("psutil.sensors_temperatures")
@patch("transport.hw_stats.pynvml")
def test_get_stats_schema(mock_pynvml, mock_sensors_temperatures):
    """Validate the schema of the main hardware statistics extract function."""
    # Mock pynvml calls
    mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = Mock(used=2*10**6, total=3*10**6)
    mock_pynvml.nvmlDeviceGetUtilizationRates.return_value = Mock(gpu=52)
    mock_pynvml.nvmlDeviceGetTemperature.return_value = 40

    # Mock cpu temp call, this would return an empty dict on unsupported OS (ie. automated test environment).
    mock_sensors_temperatures.return_value = {
        "coretemp": [Mock(label="#1", current=26), Mock(label="#2", current=28), Mock(label="#3", current=28)]
    }

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
