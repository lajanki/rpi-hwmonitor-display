from unittest.mock import patch, MagicMock
import pytest

from transport import hw_stats
import message_models



@pytest.fixture
def gpuinfo_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("transport.hw_stats.message_models.GPUInfo", mock)
    return mock


@patch("transport.hw_stats.psutil.virtual_memory")
def test_get_ram_info(mock_virtual_memory):
    # Setup mock return value
    mock_mem = MagicMock()
    mock_mem.total = 8_000_000_000
    mock_mem.used = 4_000_000_000
    mock_mem.available = 3_500_000_000
    mock_virtual_memory.return_value = mock_mem

    result = hw_stats._get_ram_info()
    assert isinstance(result, message_models.RAMInfo)
    assert result.total == 8000
    assert result.used == 4000
    assert result.available == 3500

def test_nvml_not_available(gpuinfo_mock, monkeypatch):
    monkeypatch.setattr("transport.hw_stats.NVML_AVAILABLE", False)
    result = hw_stats._get_gpu_info()
    gpuinfo_mock.assert_called_once_with()
    assert result == gpuinfo_mock.return_value

def test_nvml_available(gpuinfo_mock, monkeypatch):
    mock_pynvml = MagicMock()
    mock_mem_info = MagicMock()
    mock_mem_info.used = 2000000000
    mock_mem_info.total = 4000000000
    mock_util_info = MagicMock()
    mock_util_info.gpu = 50
    mock_temp_info = 70

    mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mock_mem_info
    mock_pynvml.nvmlDeviceGetUtilizationRates.return_value = mock_util_info
    mock_pynvml.nvmlDeviceGetTemperature.return_value = mock_temp_info

    monkeypatch.setattr("transport.hw_stats.pynvml", mock_pynvml)
    monkeypatch.setattr("transport.hw_stats.NVML_AVAILABLE", True)
    monkeypatch.setattr("transport.hw_stats.nvml_device_handle", "dummy_handle")

    result = hw_stats._get_gpu_info()
    gpuinfo_mock.assert_called_once_with(
        mem_used=2000,
        mem_total=4000,
        utilization=50,
        temperature=70
    )
    assert result == gpuinfo_mock.return_value