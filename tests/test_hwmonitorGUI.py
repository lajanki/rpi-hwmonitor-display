import time
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

import hwmonitorGUI
from message_workers import LocalNetworkWorker
from PyQt5.QtWidgets import QPushButton



def test_widget_update(qtbot, mock_msg_data):
    """Does receiving new readings update the corresponding GUI elements?"""
    main_window = hwmonitorGUI.MainWindow(transport_worker_class=Mock)
    qtbot.addWidget(main_window)

    msg_data = mock_msg_data.copy()
    msg_data["timestamp"] = time.time() # add a timestamp to model received json data

    main_window.update_readings(msg_data)
    
    # CPU utilization
    assert main_window.cpu_stats_labels["%"].text() == "10%"
    assert main_window.cpu_stats_labels["1 min"].text() == "0.8"
    assert main_window.cpu_stats_labels["5 min"].text() == "1.2"
    assert main_window.cpu_stats_labels["15 min"].text() == "2.3"
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


def test_missing_load_averages(qtbot, mock_msg_data):
    main_window = hwmonitorGUI.MainWindow(transport_worker_class=Mock)
    qtbot.addWidget(main_window)
    readings = {"cpu": mock_msg_data["cpu"].copy()}
    main_window._update_cpu_stat_cards(readings)
    readings["cpu"].pop("load_average_5min")
    readings["cpu"].pop("load_average_15min")

    main_window._update_cpu_stat_cards(readings)

    assert main_window.cpu_stats_labels["1 min"].text() == "0.8"
    assert main_window.cpu_stats_labels["5 min"].text() == "-"
    assert main_window.cpu_stats_labels["15 min"].text() == "-"


@pytest.mark.parametrize("window_size", [(800, 480), (620, 420)])
def test_touchscreen_spacing(qtbot, window_size, mock_msg_data):
    main_window = hwmonitorGUI.MainWindow(transport_worker_class=Mock)
    qtbot.addWidget(main_window)
    stylesheet = Path(__file__).resolve().parents[1] / "style.qss"
    main_window.setStyleSheet(stylesheet.read_text())
    main_window._update_cpu_stat_cards(mock_msg_data)
    main_window._update_temperature(mock_msg_data)
    main_window.resize(*window_size)
    main_window.show()
    qtbot.waitExposed(main_window)

    assert (main_window.width(), main_window.height()) == window_size
    for object_name in ("secondary_button", "close_button"):
        button = main_window.findChild(QPushButton, object_name)
        assert button.width() >= 100
        assert button.height() >= 52
        assert button.iconSize().width() == 24

    utilization_card = main_window.cpu_stats_labels["%"].parentWidget()
    load_card = main_window.cpu_stats_labels["1 min"].parentWidget()
    cores_card = main_window.cpu_stats_labels["#"].parentWidget()
    assert utilization_card.width() < load_card.width()
    assert cores_card.width() < load_card.width()

    cpu_temperature_card = main_window.cpu_temperature.parentWidget()
    gpu_temperature_card = main_window.gpu_temperature.parentWidget()
    cards = [utilization_card, load_card, cores_card, cpu_temperature_card, gpu_temperature_card]
    for card in cards:
        assert card.y() == utilization_card.y()
        assert card.height() == utilization_card.height()
        background = card.palette().color(card.backgroundRole())
        assert max(background.red(), background.green(), background.blue()) < 128
    for previous_card, next_card in zip(cards, cards[1:]):
        assert previous_card.geometry().right() < next_card.geometry().left()
    for label in (main_window.cpu_temperature, main_window.gpu_temperature):
        assert label.width() >= label.fontMetrics().horizontalAdvance(label.text())
    for plot_name in ("utilization_graph", "memory_graph"):
        plot = main_window.findChild(hwmonitorGUI.pg.PlotWidget, plot_name)
        background = plot.backgroundBrush().color()
        assert max(background.red(), background.green(), background.blue()) < 128


@pytest.mark.parametrize("utilization", [0, 20, 50, 100])
def test_cpu_utilization_colors_stay_dark(qtbot, mock_msg_data, utilization):
    main_window = hwmonitorGUI.MainWindow(transport_worker_class=Mock)
    qtbot.addWidget(main_window)
    readings = {"cpu": dict(mock_msg_data["cpu"], utilization=utilization)}
    main_window._update_cpu_stat_cards(readings)
    label = main_window.cpu_stats_labels["%"]
    label.ensurePolished()

    background = label.palette().color(label.backgroundRole())
    foreground = label.palette().color(label.foregroundRole())
    assert max(background.red(), background.green(), background.blue()) < 128
    assert min(foreground.red(), foreground.green(), foreground.blue()) > 180
