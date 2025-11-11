import atexit
import logging
import os
from collections import namedtuple

import psutil
import pynvml

import message_models


logger = logging.getLogger()


NVML_AVAILABLE = True
nvml_device_handle = None
try:
    pynvml.nvmlInit()
    # Try to get the first GPU handle now and keep it cached
    nvml_device_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    # Shutdown NVML when the process exits
    atexit.register(pynvml.nvmlShutdown)
except pynvml.NVMLError_LibraryNotFound:
    logger.warning("NVIDIA Management Library (NVML) not detected, Disabling GPU tracking.")
    NVML_AVAILABLE = False
except pynvml.NVMLError as e:
    logger.warning("NVML initialization failed: %s. Disabling GPU tracking.", e)
    NVML_AVAILABLE = False


def get_stats():
    """Wrapper function for collecting individual hardware readings as 
    message to be published.

    Return:
        pydantic MessageModel of the hardware readings
    """
    return message_models.MessageModel(
        cpu=_get_cpu_info(),
        ram=_get_ram_info(),
        gpu=_get_gpu_info()
    )

def _get_ram_info() -> message_models.RAMInfo:
    """Get system memory usage via psutil.

    Return:
        a RAMInfo pydantic model
    """
    mem = psutil.virtual_memory()
    return message_models.RAMInfo(
        total=int(mem.total / 10**6),
        used=int(mem.used / 10**6),
        available=int(mem.available / 10**6)
    )

def _get_gpu_info() -> message_models.GPUInfo:
    """Get GPU usage statistics using Nvidia management libary (NVML).
    Adapted from gpustat (https://pypi.org/project/gpustat/)
    https://pypi.org/project/nvidia-ml-py/
    https://docs.nvidia.com/deploy/nvml-api/index.html

    Return:
        a GPUInfo pydantic model
    """
    # Returna default empty message if NVML is not available
    if not NVML_AVAILABLE:
        return message_models.GPUInfo()

    global nvml_device_handle
    mem_info = pynvml.nvmlDeviceGetMemoryInfo(nvml_device_handle)
    util_info = pynvml.nvmlDeviceGetUtilizationRates(nvml_device_handle)
    temp_info = pynvml.nvmlDeviceGetTemperature(nvml_device_handle, pynvml.NVML_TEMPERATURE_GPU)

    return message_models.GPUInfo(
        mem_used=int(mem_info.used / 10**6),
        mem_total=int(mem_info.total / 10**6),
        utilization=util_info.gpu,
        temperature=temp_info
    )

def _get_cpu_info() -> message_models.CPUInfo:
    """Get CPU usage statistics via psutil.

    Return:
        a CPUInfo pydantic model
    """
    return message_models.CPUInfo(
        cores=message_models.CPUCoreInfo(
            utilization=list(map(int, psutil.cpu_percent(percpu=True))),
            frequency=[int(item.current) for item in psutil.cpu_freq(percpu=True)],
            temperature=[int(t.value) for t in _get_cpu_temps() if "Core" in t.label]
        ),
        utilization=int(psutil.cpu_percent()),
        frequency=int(psutil.cpu_freq().current),
        temperature=int(_get_cpu_temps()[-1].value), # assume last reading is CPU package temp
        load_average_1min=psutil.getloadavg()[0],
        num_high_load_cores=len([c for c in psutil.cpu_percent(percpu=True) if c > 50])
    )

def _get_cpu_temps() -> list[namedtuple]:
    """Get CPU temperature using either psutil (Linux) or
    wmi (Windows Management Instrumentation) and LibreHardwareMonitor (Windows).
    On Windows this requires Open Hardware Monitor running in the background.
        http://timgolden.me.uk/python/wmi/index.html
        https://github.com/LibreHardwareMonitor/LibreHardwareMonitor

    Return:
        A list of CoreTemp named tuples. One element for each core and one for
        the whole CPU unit.
    """

    # Common container for storing temperature readings
    # regardless of platform.
    CoreTemp = namedtuple("CoreTemp", ["label", "value"])

    if os.name == "nt":
        import wmi
        w = wmi.WMI(namespace=r"root\LibreHardwareMonitor")
        values = [CoreTemp(sensor.Name, sensor.value) for sensor in w.Sensor()
                  if sensor.SensorType == "Temperature"
                    and sensor.Name.startswith(("CPU Core #", "CPU Package"))
                    and "Distance to TjMax" not in sensor.Name]
    else:
        temps = psutil.sensors_temperatures()["coretemp"]
        values = [CoreTemp(t.label, t.current) for t in temps]
    
    # Sort by core label to ensure consistent order.
    # this will sort core specific readings first and package last.
    # E.g., "Core 0", "Core 1, ..., "Package id 0"
    values.sort(key=lambda c: c.label)
    return values
