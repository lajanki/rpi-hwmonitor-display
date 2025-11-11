import atexit
import logging
import os
from collections import namedtuple

import psutil
import pynvml

from message_model import MessageModel


logger = logging.getLogger()

CoreTemp = namedtuple("CoreTemp", ["label", "value"])

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
    """Gather various CPU, GPU and RAM readings to pydantic model as message
    to be published.
    Return:
        pydantic MessageModel of the harware readings
    """
    data = {
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "gpu": get_gpu_info() if NVML_AVAILABLE else MessageModel().gpu.model_dump()
    }
    return MessageModel(**data)

def get_ram_info():
    """Get system memory usage via psutil.
    Return:
        a dictionary
    """
    mem = psutil.virtual_memory()
    return {
        "total": int(mem.total / 10**6),
        "used": int(mem.used / 10**6),
        "available": int(mem.available / 10**6)
    }

def get_gpu_info():
    """Get GPU usage statistics using Nvidia management libary (NVML).
    Adapted from gpustat (https://pypi.org/project/gpustat/); this library
    can be difficult to properly setup in Windows.
    https://pypi.org/project/nvidia-ml-py/
    https://docs.nvidia.com/deploy/nvml-api/index.html
    Return:
        a dictionary
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

def get_cpu_info():
    """Get CPU usage statistics via psutil.
    Return:
        a dictionary
    """
    stats = {
        "cores": {
            "utilization": list(map(int, psutil.cpu_percent(percpu=True))),
            "frequency": [int(item.current) for item in psutil.cpu_freq(percpu=True)],  # The percpu attribute is only supported in Linux,
                                                                                        # on Windows this has no effect.
            "temperature": [int(t.value) for t in _get_cpu_temps() if "Core" in t.label]
        },
        "utilization": int(psutil.cpu_percent()),
        "frequency": int(psutil.cpu_freq().current),
        "temperature":  int(_get_cpu_temps()[-1].value),
        "1_min_load_average": psutil.getloadavg()[0],
        "num_high_load_cores": len([c for c in psutil.cpu_percent(percpu=True) if c > 50])
    }

    return stats

def _get_cpu_temps():
    """Get CPU temperature using either psutil (Linux) or
    wmi (Windows Management Instrumentation) and LibreHardwareMonitor (Windows).
    On Windows this requires Open Hardware Monitor running in the background.
        http://timgolden.me.uk/python/wmi/index.html
        https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
    Return:
        A list of CoreTemp named tuples. One element for each core and one for
        the whole CPU unit.
    """
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
    
    # Sort by core label (total CPU first). This will NOT sort by
    # numeric index but rather ensure result will always be in he same order.
    values.sort(key=lambda c: c.label)
    return values
