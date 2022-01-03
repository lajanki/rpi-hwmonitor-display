import logging

import psutil
import pynvml
import gpustat

try:
    import wmi
    w = wmi.WMI(namespace="root\OpenHardwareMonitor")
except ImportError:
    pass


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")

# GPU statistics on Linux is based on NVIDIA library, disable if unable to load nvml
IGNORE_GPU = False
try:
    pynvml.nvmlInit()
except pynvml.NVMLError_LibraryNotFound as e:
    logging.warning(str(e))
    IGNORE_GPU = True

EMPTY_TEMPLATE = {
    "timestamp": 1640977505,
    "cpu": {
        "cores": {
            "utilization": [],
            "frequency": [],
            "temperature": []
        },
        "utilization": 0,
        "frequency": 0,
        "temperature": 0
    },
    "gpu": {
        "memory.used": 0,
        "memory.total": 1, # non zero default value to avoid division by zero
        "utilization": 0,
        "temperature": 0
    },
    "ram": {
        "total": 1,
        "used": 0,
        "available": 0
    }
}


def get_ram_info():
    """System memory usage via psutil."""
    mem = psutil.virtual_memory()
    return {
        "total": int(mem.total / 1000**2),
        "used": int(mem.used / 1000**2),
        "available": int(mem.available / 1000**2)
    }

def get_gpu_info():
    """GPU usage via gpustat. Linux only."""
    if IGNORE_GPU:
        stats = {
            "memory.used": 0,
            "memory.total": 1,
            "utilization": 0,
            "temperature": 0
        }

    else:
        gpustats = gpustat.GPUStatCollection.new_query().jsonify()
        stats = {
            "memory.used": gpustats["gpus"][0]["memory.used"],
            "memory.total": gpustats["gpus"][0]["memory.total"],
            "utilization": gpustats["gpus"][0]["utilization.gpu"],
            "temperature": gpustats["gpus"][0]["temperature.gpu"]
        }

    return stats

def _get_cpu_info_psutil():
    """CPU usage via psutil. Linux only."""
    temps = psutil.sensors_temperatures()
    stats = {
        "cores": {
            "utilization": list(map(int, psutil.cpu_percent(percpu=True))),
            "frequency": [int(item.current) for item in psutil.cpu_freq(percpu=True)],
            "temperature":  [int(item.current) for item in temps["coretemp"] if "Core" in item.label]
        },
        "utilization": int(psutil.cpu_percent()),
        "frequency": int(psutil.cpu_freq().current),
        "temperature": int(temps["coretemp"][0].current)
    }

    return stats

def _get_cpu_and_gpu_info_wmi():
    """Fetch current CPU and GPU using wmi (Windows Management Instrumentation) and OpenHardwareMonitor.
    psutil and gpustat have limited functionality in Windows, so third party application
    is used instead.
    Requires https://openhardwaremonitor.org/ running in the background.
    http://timgolden.me.uk/python/wmi/index.html.
    https://openhardwaremonitor.org/
    """
    cpu = {
        "cores": {
            "utilization": {},
            "frequency": {},
            "temperature": {}
        },
        "utilization": 0,
        "frequency": 0,
        "temperature": 0
    }
    gpu = {
        "memory.used": 0,
        "memory.total": 1,
        "utilization": 0,
        "temperature": 0
    }

    for sensor in w.Sensor():
        if sensor.SensorType == "Temperature":
            if sensor.Name.startswith("CPU Core #"):                
                cpu["cores"]["temperature"][sensor.Identifier] = int(sensor.value)

            if sensor.Name == "CPU Package":
                cpu["temperature"] = int(sensor.value)

            if sensor.Name == "GPU Core":
                gpu["temperature"] = int(sensor.value)

        elif sensor.SensorType == "Clock":
            if sensor.Name.startswith("CPU Core #"):
                cpu["cores"]["frequency"][sensor.Identifier] = int(sensor.Value)

        elif sensor.SensorType == "Load":
            if sensor.Name.startswith("CPU Core #"):
                cpu["cores"]["utilization"][sensor.Identifier] = int(sensor.Value)

            if sensor.Name == "CPU Total":
                cpu["utilization"] = int(sensor.value)

            if sensor.Name == "GPU Core":
                gpu["utilization"] = int(sensor.value)

        elif sensor.SensorType == "SmallData":
            if sensor.Name == "GPU Memory Used":
                gpu["memory.used"] = int(sensor.value)

            if sensor.Name == "GPU Memory Total":
                gpu["memory.total"] = int(sensor.value)

    # Transform CPU core values to list and sort by core index
    for key in cpu["cores"]:
        identifiers = sorted(list(cpu["cores"][key].keys()))
        cpu["cores"][key] = [cpu["cores"][key][i] for i in identifiers]

    return {"cpu": cpu, "gpu": gpu}
