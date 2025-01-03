import time
from unittest.mock import patch, Mock

import pytest

import hwmonitorGUI
from message_workers import LocalNetworkWorker



def test_widget_update(qtbot, mock_msg_data):
    """Does receiving new readings update the corresponding GUI elements?"""
    main_window = hwmonitorGUI.MainWindow(transport_worker_class=Mock)
    qtbot.addWidget(main_window)

    msg_data = mock_msg_data.copy()
    msg_data["timestamp"] = time.time() # add a timestamp to model received json data

    main_window.update_readings(msg_data)
    
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
    # On 1st call a minimum of 5 empty QLCDNumber elements are initialized
    assert main_window.core_window.empty_label.parent() is None
    assert len(main_window.core_window.qlcd_widgets) == 5

    # On subsequent calls values should be set
    main_window.update_readings(msg_data)
    assert [ qlcd.intValue() for qlcd in main_window.core_window.qlcd_widgets ] == [7, 0, 0, 1, 0]
