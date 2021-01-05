import logging

import psutil
import pynvml
import gpustat


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")


# GPU statistics is based on NVIDIA library, disable if unable to load nvml
IGNORE_GPU = False
try:
    pynvml.nvmlInit()
except pynvml.NVMLError_LibraryNotFound:
    logging.warning("NVML library not found, disabling GPU statistics")
    IGNORE_GPU = True



def get_ram_info():
    mem = psutil.virtual_memory()
    return {
        "total": int(mem.total / 1000**2),
        "used": int(mem.used / 1000**2),
        "available": int(mem.available / 1000**2)
    }

def get_gpu_info():
    if IGNORE_GPU:
        stats = {
            "memory.used": 0,
            "memory.total": 1, # non zero value to avoid division by zero
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
    """Fetch current CPU core temperature, frequnces and loads using psutil."""
    cpu_temps = psutil.sensors_temperatures()

    temperatures = [int(item.current) for item in cpu_temps["coretemp"] if "Core" in item.label]
    frequences = [int(item.current) for item in psutil.cpu_freq(percpu=True)]
    load = list(map(int, psutil.cpu_percent(percpu=True)))

    return {"utilization": load, "freq": frequences, "temperature": temperatures }

def _get_cpu_info_wmi():
    """Fetch current CPU core temperature, frequnces and loads using wmi and OpenHardwareMonitor
    psutil has limted functionality in Windows. Windows Management Instrumentation is used instead.
    Requires https://openhardwaremonitor.org/ running in the background.
    http://timgolden.me.uk/python/wmi/index.html.
    https://openhardwaremonitor.org/
    """
    import wmi # Windows only library
    
    w = wmi.WMI(namespace="root\OpenHardwareMonitor")
    ohm_infos = w.Sensor()

    temperatures = []
    frequences = []
    load = []
    for sensor in ohm_infos:
        if sensor.SensorType == "Temperature":
            if sensor.Name.startswith("CPU Core #"):
                temperatures.append((sensor.Value, int(sensor.Name[-1])))

        elif sensor.SensorType == "Clock":
            if sensor.Name.startswith("CPU Core #"):
                frequences.append((sensor.Value, int(sensor.Name[-1])))

        elif sensor.SensorType == "Load":
            if sensor.Name.startswith("CPU Core #"):
                load.append((sensor.Value, int(sensor.Name[-1])))

    temperatures = [int(t[0]) for t in sorted(temperatures, key=lambda token: token[1])]
    frequences = [int(t[0]) for t in sorted(frequences, key=lambda token: token[1])]
    load = [int(t[0]) for t in sorted(load, key=lambda token: token[1])]

    return {"utilization": load, "freq": frequences, "temperature": temperatures }

