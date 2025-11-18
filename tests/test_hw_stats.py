from unittest.mock import patch, MagicMock
import importlib
import pytest

from transport import hw_stats
from transport.exceptions import DummyAmdSmiException
import message_models



@pytest.fixture
def gpuinfo_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("transport.hw_stats.message_models.GPUInfo", mock)
    return mock


@patch("transport.hw_stats.psutil.virtual_memory")
def test_get_ram_info(mock_virtual_memory):
    """Simple _get_ram_info test."""

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

@patch("transport.hw_stats.try_get_gpu_handle")
def test_graphics_handle_not_available(mock_get_gpu_handle, gpuinfo_mock):
    """If a gprahics library cannot be initialized,
    _get_gpu_info should return an empty GPUInfo model.
    """
    mock_get_gpu_handle.return_value = None
    result = hw_stats._get_gpu_info()
    gpuinfo_mock.assert_called_once_with()
    assert result == gpuinfo_mock.return_value

def test_gpu_handle_not_loaded_twice(monkeypatch):
    """_get_gpu_info should only attempt to load the GPU handle
    on first call.
    """
    monkeypatch.setattr("transport.hw_stats.GPU_DEVICE_HANDLE_LOADED", False)

    with patch("transport.hw_stats.try_get_gpu_handle") as mock_get_gpu_handle:
        # First call: should attempt to load handle
        mock_get_gpu_handle.return_value = None
        hw_stats._get_gpu_info()
        mock_get_gpu_handle.assert_called_once()

        mock_get_gpu_handle.reset_mock()

        # Second call: should NOT attempt to load handle again
        hw_stats._get_gpu_info()
        mock_get_gpu_handle.assert_not_called()

@patch("transport.hw_stats._get_nvidia_gpu_info")
def test_nvml_available(mock_get_nvidia_gpu_info, monkeypatch):
    """If pynvml is available, _get_nvidia_gpu_info should be used for GPU stats."""
    mock_device_handle = MagicMock()

    monkeypatch.setattr("transport.hw_stats.GPU_DEVICE_HANDLE_LOADED", True)
    monkeypatch.setattr("transport.hw_stats.handle_config", ("NVIDIA", mock_device_handle))
    hw_stats._get_gpu_info()

    mock_get_nvidia_gpu_info.assert_called_once_with(mock_device_handle)

@patch("transport.hw_stats.pynvml")
def test_get_nvidia_gpu_info(mock_pynvml, gpuinfo_mock):
    """_get_nvidia_gpu_info should return a valid GPUInfo model."""
    mock_mem_info = MagicMock()
    mock_mem_info.used = 2000000000
    mock_mem_info.total = 4000000000
    mock_util_info = MagicMock()
    mock_util_info.gpu = 50
    mock_temp_info = 70

    mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mock_mem_info
    mock_pynvml.nvmlDeviceGetUtilizationRates.return_value = mock_util_info
    mock_pynvml.nvmlDeviceGetTemperature.return_value = mock_temp_info

    mock_device_handle = MagicMock()
    result = hw_stats._get_nvidia_gpu_info(mock_device_handle)

    gpuinfo_mock.assert_called_once_with(
        mem_used=2000,
        mem_total=4000,
        utilization=50,
        temperature=70
    )
    assert result == gpuinfo_mock.return_value

@pytest.mark.skipif(not hw_stats.AMDSMI_IMPORTED, reason="amdsmi module not available")
@patch("atexit.register")
def test_try_get_gpu_handle(mock_register):
    """Test try_get_gpu_handle on multiple platform/library support combinations."""

    # amdsmi available: should return AMD handle
    with patch("transport.hw_stats.amdsmi") as mock_amdsmi:
        mock_handle = MagicMock()
        mock_amdsmi.amdsmi_get_processor_handles.return_value = [mock_handle]

        vendor, handle = hw_stats.try_get_gpu_handle()
        mock_register.is_called_with(mock_amdsmi.amdsmi_shut_down)
        assert vendor == "AMD"
        assert handle == mock_handle

    # amdmsi not available, pynvml is available: should return NVIDIA handle
    with patch("transport.hw_stats.pynvml") as mock_pynvml:
        with patch("transport.hw_stats.amdsmi.amdsmi_init", side_effect=DummyAmdSmiException):
            mock_handle = MagicMock()
            mock_pynvml.nvmlDeviceGetHandleByIndex.return_value = mock_handle

            vendor, handle = hw_stats.try_get_gpu_handle()
            mock_register.is_called_with(mock_pynvml.nvmlShutdown)
            assert vendor == "NVIDIA"
            assert handle == mock_handle

    # neither library available: should return None
    with patch("transport.hw_stats.amdsmi.amdsmi_init", side_effect=DummyAmdSmiException):
        with patch("transport.hw_stats.pynvml.nvmlInit", side_effect=mock_pynvml.NVMLError_LibraryNotFound):
            result = hw_stats.try_get_gpu_handle()
            assert result is None