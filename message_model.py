import time

from pydantic import BaseModel, Field
from typing import List


# CPU Core utilization
class _CPUCoresModel(BaseModel):
    utilization: List[int] = Field(default_factory=list)
    frequency: List[int] = Field(default_factory=list)
    temperature: List[int] = Field(default_factory=list)

# CPU utilization
class _CPUModel(BaseModel):
    utilization: int = 0  # system-wide percentage of total CPU time.
    frequency: int = 0
    temperature: int = 0
    load_average_1min: float = 0.0  # 1 minute load average
    num_high_load_cores: int = 0  # number of cores with utilization above p%
    cores: _CPUCoresModel = _CPUCoresModel()

# GPU utilization
class _GPUModel(BaseModel):
    mem_used: int = 0  # memory usage in MB
    mem_total: int = 1 # non-zero default value to avoid division by zero
    utilization: int = 0 
    temperature: int = 0

# System RAM usage in MB
class _RAMModel(BaseModel):
    total: int = 1
    used: int = 0
    available: int = 0

# Final, public, message model
class MessageModel(BaseModel):
    cpu: _CPUModel = _CPUModel()
    gpu: _GPUModel = _GPUModel()
    ram: _RAMModel = _RAMModel()
    timestamp: float = Field(default_factory=time.time)  # UNIX timestamp in seconds
