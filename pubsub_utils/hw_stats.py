from collections import namedtuple
import logging
import os

import psutil
import pynvml
import gpustat

import utils


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")

CoreTemp = namedtuple("CoreTemp", ["label", "value"])

def get_ram_info():
    """System memory usage in MB via psutil."""
    mem = psutil.virtual_memory()
    return {
        "total": int(mem.total / 10**6),
        "used": int(mem.used / 10**6),
        "available": int(mem.available / 10**6)
    }

def get_gpu_info():
    """GPU usage statistics using Nvidia management libary (NVML).
    Adapted from gpustat (https://pypi.org/project/gpustat/); this library
    can be difficult to properly setup in Windows.
    https://pypi.org/project/nvidia-ml-py/
    https://docs.nvidia.com/deploy/nvml-api/index.html
    Nvidia only.
    """
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Assume GPU is at index 0
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp_info = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        stats = {
            "memory.used": int(mem_info.used / 10**6), # MB
            "memory.total": int(mem_info.total / 10**6),
            "utilization": util_info.gpu,
            "temperature": temp_info
        }
    except pynvml.NVMLError_LibraryNotFound as e:
        logging.warning("Unable to load gpustat, defaulting to empty values")
        stats = utils.DEFAULT_MESSAGE["gpu"]
    finally:
        pynvml.nvmlShutdown()

    return stats

def get_gpustat_info():
    """GPU usage via gpustat. Nvidia only."""
    try:
        gpustats = gpustat.GPUStatCollection.new_query().jsonify()
        stats = {
            "memory.used": gpustats["gpus"][0]["memory.used"],  # MB
            "memory.total": gpustats["gpus"][0]["memory.total"],
            "utilization": gpustats["gpus"][0]["utilization.gpu"],
            "temperature": gpustats["gpus"][0]["temperature.gpu"]
        }
    except pynvml.NVMLError_LibraryNotFound as e:
        logging.warning("Unable to load gpustat, defaulting to empty values")
        stats = utils.DEFAULT_MESSAGE["gpu"]

    return stats

def get_cpu_info():
    """CPU usage statistics."""
    stats = {
        "cores": {
            "utilization": list(map(int, psutil.cpu_percent(percpu=True))),
            "frequency": [int(item.current) for item in psutil.cpu_freq(percpu=True)],  # The percpu option is only supported in Linux,
                                                                                        # on Windows returns the same as when set to False
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
        w = wmi.WMI(namespace="root\LibreHardwareMonitor")
        values = [CoreTemp(sensor.Name, sensor.value) for sensor in w.Sensor()
                  if sensor.SensorType == "Temperature"
                    and sensor.Name.startswith(("CPU Core #", "CPU Package"))]
    else:
        temps = psutil.sensors_temperatures()["coretemp"]
        values = [CoreTemp(t.label, t.current) for t in temps]
    
    # Sort by core label (total CPU first). This will NOT sort by
    # numeric index but rather ensure result will always be in he same order.
    values.sort(key=lambda c: c.label)
    return values



def _get_cpu_and_gpu_info_wmi():
    """Fetch current CPU and GPU using wmi (Windows Management Instrumentation) and LibreHardwareMonitor.
    psutil and gpustat have limited functionality in Windows, so third party application
    is used instead.
    Requires LibreHardwareMonitor running in the background.
    http://timgolden.me.uk/python/wmi/index.html.
    https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
    """
    template = utils.DEFAULT_MESSAGE.copy()

    import wmi
    w = wmi.WMI(namespace="root\LibreHardwareMonitor")
    for sensor in w.Sensor():
        if sensor.SensorType == "Temperature":
            if sensor.Name.startswith("CPU Core #"):                
                template["cpu"]["cores"]["temperature"][sensor.Identifier] = int(sensor.value)

            if sensor.Name == "CPU Package":
                template["cpu"]["temperature"] = int(sensor.value)

            if sensor.Name == "GPU Core":
                template["gpu"]["temperature"] = int(sensor.value)

        elif sensor.SensorType == "Clock":
            if sensor.Name.startswith("CPU Core #"):
                template["cpu"]["cores"]["frequency"][sensor.Identifier] = int(sensor.Value)

        elif sensor.SensorType == "Load":
            if sensor.Name.startswith("CPU Core #"):
                template["cpu"]["cores"]["utilization"][sensor.Identifier] = int(sensor.Value)

            if sensor.Name == "CPU Total":
                template["cpu"]["utilization"] = int(sensor.value)

            if sensor.Name == "GPU Core":
                template["gpu"]["utilization"] = int(sensor.value)

        elif sensor.SensorType == "SmallData":
            if sensor.Name == "GPU Memory Used":
                template["gpu"]["memory.used"] = int(sensor.value)

            if sensor.Name == "GPU Memory Total":
                template["gpu"]["memory.total"] = int(sensor.value)

    # Transform CPU core values to list and sort by core index
    for key in template["cpu"]["cores"]:
        identifiers = sorted(list(template["cpu"]["cores"][key].keys()))
        template["cpu"]["cores"][key] = [template["cpu"]["cores"][key][i] for i in identifiers]

    return template
