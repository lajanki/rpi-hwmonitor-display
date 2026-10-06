import logging
import time

import numpy as np
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtCore import (
    Qt,
    QSize,
    QObject,
    QThread,
    QTimer,
    pyqtSlot,
    pyqtSignal
)
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QLCDNumber,
    QDesktopWidget,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QFrame,
)
import pyqtgraph as pg

from transport import CONFIG
import utils



logger = logging.getLogger()

class MainWindow(QMainWindow):
    """Main GUI window."""

    def __init__(self, transport_worker_class):
        super().__init__()
        self.message_worker_thread = QThread()
        self.transport_worker_class = transport_worker_class
        self.core_window = CPUCoreWindow()
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("main_widget")
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        icon_label = QLabel(self)
        pixmap = QPixmap("resources/iconfinder_gnome-system-monitor_23964.png")
        pixmap = pixmap.scaledToHeight(34)
        icon_label.setPixmap(pixmap)
        icon_label.setObjectName("app_icon")
        header.addWidget(icon_label)

        title = QLabel("System monitor")
        title.setObjectName("app_title")
        header.addWidget(title)
        header.addStretch(1)

        self.clock_lcd = QLCDNumber(5, self, objectName="clock_qlcd")
        self.clock_lcd.setSegmentStyle(QLCDNumber.Flat)
        self.clock_lcd.setMinimumWidth(100)
        header.addWidget(self.clock_lcd)

        core_utilization_button = QPushButton("Cores")
        core_utilization_button.setIcon(QIcon("resources/iconfinder_chip_square_6137627.png"))
        core_utilization_button.setObjectName("secondary_button")
        core_utilization_button.setMinimumSize(100, 52)
        core_utilization_button.setIconSize(QSize(24, 24))
        header.addWidget(core_utilization_button)
        core_utilization_button.clicked.connect(self.core_window.show)

        close_button = QPushButton("Close")
        close_button.setIcon(QIcon("resources/iconfinder_Close_1891023.png"))
        close_button.setObjectName("close_button")
        close_button.setMinimumSize(100, 52)
        close_button.setIconSize(QSize(24, 24))
        header.addWidget(close_button)
        close_button.clicked.connect(self.stop_thread_and_exit)
        layout.addLayout(header)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self.cpu_stats_labels = {}
        default_values = {
            "%": "0%",
            "1 min": "0.0",
            "#": "#0"
        }
        stat_titles = {"%": "CPU USAGE", "1 min": "LOAD AVERAGE", "#": "BUSY CORES"}
        for name, value in default_values.items():
            card = QFrame()
            card.setObjectName("metric_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(2)

            caption = QLabel(stat_titles[name])
            caption.setObjectName("metric_caption")
            card_layout.addWidget(caption)

            if name == "1 min":
                load_row = QHBoxLayout()
                load_row.setSpacing(6)
                for minutes in (1, 5, 15):
                    load_column = QVBoxLayout()
                    load_column.setSpacing(2)
                    label = QLabel(value)
                    label.setObjectName("load_average_value")
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    load_column.addWidget(label)
                    period_label = QLabel(f"{minutes} min")
                    period_label.setObjectName("metric_caption")
                    period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    load_column.addWidget(period_label)
                    load_row.addLayout(load_column, 1)
                    self.cpu_stats_labels[f"{minutes} min"] = label
                card_layout.addLayout(load_row)
            else:
                label = QLabel(value, self, objectName="cpu_stats_label")
                label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(label)
                self.cpu_stats_labels[name] = label
            stats_row.addWidget(card, 2 if name == "1 min" else 1)

        self.cpu_temperature = QLabel("0°C", self)
        self.gpu_temperature = QLabel("0°C", self)
        for label, object_name, caption_text in (
            (self.cpu_temperature, "cpu_temperature", "CPU TEMP"),
            (self.gpu_temperature, "gpu_temperature", "GPU TEMP"),
        ):
            card = QFrame()
            card.setObjectName("temperature_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(7, 8, 7, 8)
            card_layout.setSpacing(2)
            caption = QLabel(caption_text)
            caption.setObjectName("temperature_caption")
            card_layout.addWidget(caption)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName(object_name)
            card_layout.addWidget(label)
            stats_row.addWidget(card, 1)
        layout.addLayout(stats_row)

        content = QHBoxLayout()
        content.setSpacing(12)
        layout.addLayout(content, 1)

        graph_panel = QVBoxLayout()
        graph_panel.setSpacing(5)
        graph_title = QLabel("CPU & GPU ACTIVITY")
        graph_title.setObjectName("section_title")
        graph_panel.addWidget(graph_title)

        date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation="bottom")
        date_axis.setTickSpacing(major=60, minor=0)
        percent_axis = PercentAxisItem(orientation="left")

        utilization_graph = pg.PlotWidget(axisItems={"bottom": date_axis, "left": percent_axis})
        utilization_graph.setObjectName("utilization_graph")
        utilization_graph.setBackground("#f6f8f7")
        utilization_graph.showGrid(x=True, y=True, alpha=0.15)
        utilization_graph.getAxis("left").setWidth(42)
        utilization_graph.getAxis("bottom").setHeight(28)
        utilization_graph.addLegend()

        # Initialize graphs with zeros for previous 5 minutes
        REFRESH_INTERVAL = CONFIG["transport"]["refresh_interval"]
        NUM_DATAPOINTS = 60//REFRESH_INTERVAL * 5
        x = [int(time.time()) - REFRESH_INTERVAL*i for i in range(NUM_DATAPOINTS,0,-1)]
        y = [0] * NUM_DATAPOINTS

        cpu_plot = utilization_graph.plot(x, y, pen=pg.mkPen("#197f87", width=2), name="CPU")
        gpu_plot = utilization_graph.plot(x, y, pen=pg.mkPen("#d47a36", width=2), name="GPU")
        self.utilization_plots = {"cpu": cpu_plot, "gpu": gpu_plot}

        # Fix y-axis range
        view_box = utilization_graph.getViewBox()
        view_box.setRange(yRange=(0,100))
        utilization_graph.setMouseEnabled(x=False, y=False)
        graph_panel.addWidget(utilization_graph, 1)
        content.addLayout(graph_panel, 2)

        metrics_panel = QVBoxLayout()
        metrics_panel.setSpacing(5)
        memory_title = QLabel("MEMORY")
        memory_title.setObjectName("section_title")
        metrics_panel.addWidget(memory_title)
        ram_plot = pg.PlotWidget()
        ram_plot.setObjectName("memory_graph")
        ram_plot.setBackground("#f6f8f7")
        ram_plot.getAxis("bottom").setHeight(28)
        ram_plot.showGrid(y=True, alpha=0.12)

        x_labeled = {0: "RAM", 0.8: "GPU"}
        x = list(x_labeled.keys())

        self.system_mem_bg_used = pg.BarGraphItem(x=[x[0]], height=[0], width=0.6, brush="#197f87")
        self.gpu_mem_bg_used = pg.BarGraphItem(x=[x[1]], height=[0], width=0.6, brush="#d47a36")
        ram_plot.addItem(self.system_mem_bg_used)
        ram_plot.addItem(self.gpu_mem_bg_used)

        font = QFont()
        font.setPixelSize(14)

        self.system_mem_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.system_mem_bar_label.setPos(x[0], 10)
        self.system_mem_bar_label.setFont(font)
        ram_plot.addItem(self.system_mem_bar_label)

        self.gpu_mem_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.gpu_mem_bar_label.setPos(x[1], 10)
        self.gpu_mem_bar_label.setFont(font)
        ram_plot.addItem(self.gpu_mem_bar_label)

        ram_plot.setXRange(-0.5, 2)
        ram_plot.setYRange(0, 100)
        ram_plot.setMouseEnabled(x=False, y=False)

        xax = ram_plot.getAxis("bottom")
        xax.setTicks([list(x_labeled.items())])
        ram_plot.hideAxis("left")

        view_range = ram_plot.viewRange()
        X_MAX = view_range[0][1]
        Y_MAX = view_range[1][1]

        self.system_mem_label = pg.TextItem("0.0GB", fill="#197f87", anchor=(1,1))
        self.system_mem_label.setFont(font)
        self.system_mem_label.setPos(X_MAX, 0.75*Y_MAX)
        ram_plot.addItem(self.system_mem_label)

        self.gpu_mem_label = pg.TextItem("0.0GB", fill="#d47a36", anchor=(1,1))
        self.gpu_mem_label.setFont(font)
        self.gpu_mem_label.setPos(X_MAX, 0.57*Y_MAX)
        ram_plot.addItem(self.gpu_mem_label)

        metrics_panel.addWidget(ram_plot, 1)
        content.addLayout(metrics_panel, 1)

        self.resize(800, 480)
        self.setMinimumSize(620, 420)
        self.setWindowTitle("HWMonitor")
        self.setWindowIcon(QIcon("resources/iconfinder_gnome-system-monitor_23964.png"))
        self._center()

    def _center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def start_worker_threads(self):
        """Wrapper for starting all worker threads."""
        self.setup_msg_pull()
        self.setup_clock_timer()

    def setup_msg_pull(self):
        """Start a worker thread to listen for incoming hardware readings.
        Connect the thread's update signal to UI refresh call.
        """
        # Instantiate a worker and move to thread.
        # Keep a reference to the worker to prevent the socket connection
        # from being garbage ccollected.
        self.worker = self.transport_worker_class()
        self.worker.moveToThread(self.message_worker_thread)

        # Connect signals and slots
        self.message_worker_thread.started.connect(self.worker.run)
        self.message_worker_thread.finished.connect(self.message_worker_thread.deleteLater)
        self.worker.update.connect(self.update_readings)

        self.message_worker_thread.start()

    def setup_clock_timer(self):
        """Setup a thread for periodically updating the QLCD widget with
        current time.
        """
        def tick():
            s = time.strftime("%H:%M")
            self.clock_lcd.display(s)

        tick()
        _timer = QTimer(self)
        _timer.timeout.connect(tick)
        _timer.start(1000)

    @pyqtSlot()
    def stop_thread_and_exit(self):
        """Stop any running worker threads and exit the application."""
        self.message_worker_thread.exit()
        self.core_window.close()
        self.close()

    @pyqtSlot(dict)
    def update_readings(self, readings):
        """Slot for message worker: receive latest hardware readings
        and update the GUI.
        """
        self._update_cpu_stat_cards(readings)
        self._update_utilization_graphs(readings)
        self._update_ram(readings)
        self._update_temperature(readings)
        self.core_window._update_cpu_cores(readings)

    def _update_cpu_stat_cards(self, readings):
        """Update CPU statistics labels."""
        label = self.cpu_stats_labels["%"]
        val = readings["cpu"]["utilization"]
        label.setText(f"{val}%")

        # Adjust background color accordingly
        style_sheet = utils.get_cpu_utilization_background_style(val)
        label.setStyleSheet(style_sheet)


        for minutes in (1, 5, 15):
            label = self.cpu_stats_labels[f"{minutes} min"]
            val = readings["cpu"].get(f"load_average_{minutes}min")
            label.setText(f"{val:.1f}" if val is not None else "-")

        label = self.cpu_stats_labels["#"]
        val = readings["cpu"]["num_high_load_cores"]
        label.setText(f"#{val}")

    def _update_utilization_graphs(self, readings):
        """Update utilization time series graph.
        
        Remove oldest item and add new reading as latest.
        Updated both CPU and GPU graphs.
        """
        for key in self.utilization_plots:
            # Update old x and y values keeping only the latest n values
            old_data = self.utilization_plots[key].getData()

            # Ignore this reading if older than the latest data point in graph.
            if readings["timestamp"] <= old_data[0][-1]:
                logger.warning("Discarding out-of-order item. Age: %ds", time.time() - readings["timestamp"])
                return
            
            x = np.append(old_data[0][1:], readings["timestamp"])
            y = np.append(old_data[1][1:], readings[key]["utilization"])

            self.utilization_plots[key].setData(x, y)

    def _update_ram(self, readings):
        """Update RAM usage bars plot and labels.
        Update both system RAM and GPU memory usage.
        """
        system_used = int(readings["ram"]["used"] / readings["ram"]["total"] * 100)
        self.system_mem_bg_used.setOpts(height=[system_used])
        self.system_mem_bar_label.setText("{}%".format(system_used))
        self.system_mem_label.setText("{:.1f}GB".format(readings["ram"]["used"]/1000))

        gpu_mem_used = int(readings["gpu"]["mem_used"] / readings["gpu"]["mem_total"] * 100)
        self.gpu_mem_bg_used.setOpts(height=[gpu_mem_used])
        self.gpu_mem_bar_label.setText("{}%".format(gpu_mem_used))
        self.gpu_mem_label.setText("{:.1f}GB".format(readings["gpu"]["mem_used"]/1000))

    def _update_temperature(self, readings):
        """Update temperature QLabels."""
        cpu_temperature = f"{readings['cpu']['temperature']}°C"
        gpu_temperature = f"{readings['gpu']['temperature']}°C"
        self.gpu_temperature.setText(gpu_temperature)
        self.cpu_temperature.setText(cpu_temperature)


class CPUCoreWindow(QWidget):
    """Window for cpu core utilizations."""
    COLUMNS_PER_ROW = 5

    def __init__(self):
        super().__init__()
        self.layout = QGridLayout()
        self.qlcd_widgets = []

        # Button for closing the window, top right.
        close_button = QPushButton("Close ")
        close_button.setIcon(QIcon("resources/iconfinder_Close_1891023.png"))
        close_button.setLayoutDirection(Qt.RightToLeft)
        close_button.clicked.connect(self.close)
        close_button.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Preferred
        )

        self.empty_label = QLabel("Waiting for data...", self)
        self.layout.addWidget(self.empty_label, 1, CPUCoreWindow.COLUMNS_PER_ROW-1)

        self.layout.addWidget(close_button, 0, CPUCoreWindow.COLUMNS_PER_ROW-1)
        self.setLayout(self.layout)
        self.resize(600, 400)
        self.setWindowTitle("CPU core utilization")

    def _update_cpu_cores(self, readings):
        """Update Core utilization values. The number of cores is not known
        until the first response is received from the poller.
        Create a QLCD widget for each core if not already created
        and update the values.
        """
        # Remove the dummy label
        self.empty_label.setParent(None)
        if not self.qlcd_widgets:
            NUM_CORES = len(readings["cpu"]["cores"]["utilization"])
            # add at least 1 row if NUM_CORES < COLUMNS_PER_ROW
            NUM_ROWS = max(1, NUM_CORES//CPUCoreWindow.COLUMNS_PER_ROW)
            for row in range(NUM_ROWS):
                for col in range(CPUCoreWindow.COLUMNS_PER_ROW):
                    qlcd = QLCDNumber(self)
                    qlcd.setDigitCount(2)
                    qlcd.setSegmentStyle(QLCDNumber.Flat)
                    self.layout.addWidget(qlcd, row+2, col)
                    self.qlcd_widgets.append(qlcd)
        else:
            for i, qlcd in enumerate(self.qlcd_widgets):
                try:
                    val = readings["cpu"]["cores"]["utilization"][i]
                except IndexError:
                    val = 0
                qlcd.display(val)
                style_sheet = utils.get_cpu_utilization_background_style(val)
                qlcd.setStyleSheet(style_sheet) 

class PercentAxisItem(pg.AxisItem):
    """Custom pyqtgraph AxisItem class with customized tick strings."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [f"{int(v)}%" for v in values]
