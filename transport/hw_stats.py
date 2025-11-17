import atexit
import logging
import os
from collections import namedtuple

import psutil
import pynvml

# The amdsmi module is importable only if the AMD SMI library is installed.
# https://rocm.docs.amd.com/projects/amdsmi/en/latest/install/install.html
try: import amdsmi;
except (ImportError, KeyError): pass

import message_models
from transport.exceptions import DummyAmdSmiException


GPU_DEVICE_HANDLE_LOADED = False
handle_config = None

logger = logging.getLogger()


def try_get_gpu_handle():
    """Try to get AMD GPU handle using AMD SMI library.

    Return:
        AMD GPU handle if available, else None
    """
    logging.info("Attempting to initialize GPU monitoring...")
    try:
        logger.info("Checking if an AMD device can be initialized...")
        amdsmi.amdsmi_init() 
        handle = amdsmi.amdsmi_get_processor_handles()[0]
        atexit.register(amdsmi.amdsmi_shut_down)
        logger.info("Success!")
        return "AMD", handle
    except NameError:
        logger.error("amdsmi library not detected.")
    except (amdsmi.AmdSmiException, DummyAmdSmiException):
        logger.warning("AMD SMI initialization failed.")

    try:
        logger.info("Checking if an Nvidia device can be initialized...")
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        atexit.register(pynvml.nvmlShutdown)
        logger.info("Success!")
        return "NVIDIA", handle
    except pynvml.NVMLError_LibraryNotFound:
        logger.warning("NVIDIA Management Library (NVML) not detected.")
    except pynvml.NVMLError as e:
        logger.warning("NVML initialization failed.")

    logger.warning("Couldn't initialize GPU, Disabling GPU tracking.")
    return None

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
    """Get usage statistics.

    On first call, tries to initialize a GPU handle using
    try_get_gpu_handle(). Subsequent calls will use the cached handle.

    Return:
        a GPUInfo pydantic model
    """
    # initialize a device handle on first call
    global handle_config, GPU_DEVICE_HANDLE_LOADED
    if not GPU_DEVICE_HANDLE_LOADED:
        handle_config = try_get_gpu_handle()
        GPU_DEVICE_HANDLE_LOADED = True

    # Return empty model if no GPU handle could be obtained
    if not handle_config:
        return message_models.GPUInfo()
    
    gpu_vendor, handle = handle_config
    if gpu_vendor == "NVIDIA":
        return _get_nvidia_gpu_info(handle)

    return _get_radeon_gpu_info(handle)


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

def _get_nvidia_gpu_info(handle) -> message_models.GPUInfo:
    """Get Nvidia GPU usage statistics using Nvidia management libary (NVML).
    https://pypi.org/project/nvidia-ml-py/
    https://docs.nvidia.com/deploy/nvml-api/index.html

    Return:
        a GPUInfo pydantic model
    """
    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
    temp_info = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

    return message_models.GPUInfo(
        mem_used=int(mem_info.used / 10**6),
        mem_total=int(mem_info.total / 10**6),
        utilization=util_info.gpu,
        temperature=temp_info
    )

def _get_radeon_gpu_info(handle) -> message_models.GPUInfo:
    """Get GPU usage statistics using amdsmi management library.
    https://rocm.docs.amd.com/projects/amdsmi/en/latest/reference/amdsmi-py-api.html

    Return:
        a GPUInfo pydantic model
    """
    gpu_metrics = amdsmi.amdsmi_get_gpu_metrics_info(handle)
    mem_info = amdsmi.amdsmi_get_gpu_vram_usage(handle)

    return message_models.GPUInfo(
        mem_used=int(mem_info["vram_used"]),
        mem_total=int(mem_info["vram_total"]),
        utilization=gpu_metrics["average_gfx_activity"],
        temperature=gpu_metrics["temperature_vrgfx"]
    )