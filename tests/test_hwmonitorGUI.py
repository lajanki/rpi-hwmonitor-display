import os
import pytest
import time
from unittest.mock import patch, Mock

import hwmonitorGUI



mock_message = {
    "cpu": {
        "utilization": 10,
        "frequency": 11,
        "temperature": 12,
        "1_min_load_average": 0.7651,
        "num_high_load_cores": 2,
        "cores": {
            "utilization": [7,0,0,1],
            "frequency": [],
            "temperature": []
        }
    },
    "gpu": {
        "memory.used": 4.5*10**3,
        "memory.total": 8*10**3,
        "utilization": 62,
        "temperature": 70
    },
    "ram": {
        "total": 2*10**3,
        "used": 1.2*10**3,
        "available": 8*10**3
    },
    "timestamp": time.time()
}


def test_reading_widget_update(qtbot):
    """Does receiving new readings update the corresponding GUI elements?"""
    main_window = hwmonitorGUI.MainWindow()
    qtbot.addWidget(main_window)

    main_window.update_readings(mock_message)
    
    # CPU utilization
    assert main_window.cpu_stats_labels["%"].text() == "10%"
    assert main_window.cpu_stats_labels["1 min"].text() == "0.8<span style='font-size:20px'>(1 min)</span>"
    assert main_window.cpu_stats_labels["#"].text() == "#2"

    # System & GPU memory
    assert main_window.system_mem_bar_label.toPlainText() == "60%"
    assert main_window.system_mem_label.toPlainText() == "1.2GB"

    assert main_window.gpu_mem_bar_label.toPlainText() == "56%"
    assert main_window.gpu_mem_label.toPlainText() == "4.5GB"

    # Temperatures
    assert main_window.cpu_temperature.text() == "12°C"
    assert main_window.gpu_temperature.text() == "70°C"

    # Core window
    #main_window.core_window._update_cpu_cores(mock_message)

    #assert len(main_window.core_window.qlcd_widgets) == 4
    #assert [ qlcd.value() for qlcd in core_window.qlcd_widgets ] == ["7", "0", "0", "1"]
