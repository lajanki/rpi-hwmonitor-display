import logging
import time
import os
import json

from google.api_core.exceptions import DeadlineExceeded
import numpy as np
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QObject, QThread, QTimer, pyqtSlot, pyqtSignal
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
    QSizePolicy
)
import pyqtgraph as pg

from pubsub_utils import UPDATE_INTERVAL
from pubsub_utils.hw_stats import EMPTY_TEMPLATE
from pubsub_utils.subscriber import Subscriber
import utils


logger = logging.getLogger()


class MainWindow(QMainWindow):
    stop_worker = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_pubsub_pull()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setAutoFillBackground(True)
        self.setCentralWidget(main_widget)

        layout = QGridLayout()
        main_widget.setLayout(layout)

        cpu_core_grid = QGridLayout()
        timeline_grid = QVBoxLayout()
        metric_grid = QVBoxLayout()

        layout.addLayout(cpu_core_grid, 0, 0, 1, 2)
        layout.addLayout(timeline_grid, 1, 0)
        layout.addLayout(metric_grid, 1, 1)

        # Set more space to bottom row
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 2)

        # Set more space to left column
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 1)


        ### CPU utilization, top row
        # Close button, top right
        close_button = QPushButton("Close ")
        close_button.setIcon(QIcon("resources/iconfinder_Close_1891023.png"))
        close_button.setLayoutDirection(Qt.RightToLeft)
        cpu_core_grid.addWidget(close_button, 0, 4)
        close_button.clicked.connect(self.stop_thread_and_exit)
        close_button.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Preferred
        )

        self.clock_lcd = QLCDNumber(5, self, objectName="clock_qlcd")
        self.clock_lcd.setSegmentStyle(QLCDNumber.Flat)
        cpu_core_grid.addWidget(self.clock_lcd, 0, 2, 1, 2)
        self.setup_clock_polling()

        # QLCD widget per CPU core in rows of 4 widgets. This will likely not work well
        # with very high core number.
        QLCD_PER_ROW = 4
        self.core_qlcd = []
        for row in range(os.cpu_count()//QLCD_PER_ROW):
            for col in range(QLCD_PER_ROW):
                qlcd = QLCDNumber(self)
                qlcd.setDigitCount(2)
                qlcd.display(0)
                qlcd.setSegmentStyle(QLCDNumber.Flat)
                cpu_core_grid.addWidget(qlcd, row+1, col+1)
                self.core_qlcd.append(qlcd)


        ### CPU & GPU utilization time series grid
        date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation="bottom")
        date_axis.setTickSpacing(major=60, minor=0)
        percent_axis = PercentAxisItem(orientation="left")

        utilization_graph = pg.PlotWidget(axisItems = {"bottom": date_axis, "left": percent_axis})
        utilization_graph.setTitle("<h2>CPU/GPU</h2>")
        utilization_graph.addLegend() # Needs to be called before any plotting

        # Initialize graphs with zeros for previous 5 minutes
        NUM_DATAPOINTS = 60//UPDATE_INTERVAL * 5
        x = [int(time.time()) - UPDATE_INTERVAL*i for i in range(NUM_DATAPOINTS,0,-1)]
        y = [0] * NUM_DATAPOINTS

        cpu_plot = utilization_graph.plot(x, y, pen="#1227F1", name="CPU")
        gpu_plot = utilization_graph.plot(x, y, pen="#660000", name="GPU")
        self.utilization_plots = {"cpu": cpu_plot, "gpu": gpu_plot}

        # Fix y-axis range
        view_box = utilization_graph.getViewBox()
        view_box.setRange(yRange=(0,100))
        timeline_grid.addWidget(utilization_graph)

        utilization_graph.setMouseEnabled(x=False, y=False)


        ### CPU & GPU temperatures
        temperature_grid = QHBoxLayout()
        self.cpu_temperature = QLabel("0°C", self)
        self.gpu_temperature = QLabel("0°C", self)
        self.cpu_temperature.setStyleSheet("background-color: black; color: #93BAFF")
        self.gpu_temperature.setStyleSheet("background-color: black; color: #FF9393")
  
        temperature_grid.addWidget(self.cpu_temperature)
        temperature_grid.addWidget(self.gpu_temperature)
        metric_grid.addLayout(temperature_grid)


        ### RAM grid
        ram_grid = QVBoxLayout()
        ram_plot = pg.plot()
        ram_plot.setTitle("<h2>MEM</h2>")

        x_labeled = {0: "RAM", 0.8: "GPU"}
        x = list(x_labeled.keys())

        self.system_mem_bg_used = pg.BarGraphItem(x=[x[0]], height=[0], width=0.6, brush="#0E1F06")
        self.gpu_mem_bg_used = pg.BarGraphItem(x=[x[1]], height=[0], width=0.6, brush="#660000")
        ram_plot.addItem(self.system_mem_bg_used)
        ram_plot.addItem(self.gpu_mem_bg_used)

        # Add labels on top of bars
        font = QFont()
        font.setPixelSize(18)

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

        # Add RAM usage labels to the right side of the plot
        view_range = ram_plot.viewRange()
        X_MAX = view_range[0][1]
        Y_MAX = view_range[1][1]

        self.system_mem_label = pg.TextItem("0.0GB", fill="#0E1F06", anchor=(1,1))
        self.system_mem_label.setFont(font)
        self.system_mem_label.setPos(X_MAX, 0.75*Y_MAX)
        ram_plot.addItem(self.system_mem_label)

        self.gpu_mem_label = pg.TextItem("0.0GB", fill="#660000", anchor=(1,1))
        self.gpu_mem_label.setFont(font)
        self.gpu_mem_label.setPos(X_MAX, 0.57*Y_MAX)
        ram_plot.addItem(self.gpu_mem_label)

        ram_grid.addWidget(ram_plot)
        metric_grid.addLayout(ram_grid)


        self.resize(620, 420)
        self.setWindowTitle("HWMonitor")
        self.setWindowIcon(QIcon("resources/iconfinder_gnome-system-monitor_23964.png"))
        self._center()

    def _center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setup_pubsub_pull(self):
        """Start polling for statistics from the topic in a separate thread."""
        self.thread = QThread()

        # Create a worker and move to thread
        self.worker = PubSubWorker()
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.stop_worker.connect(self.worker.stop)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.update.connect(self.update_readings)

        self.thread.start()

    def setup_clock_polling(self):
        """Set clock QLCD display to the current time and start polling for
        with 1 second intervals.
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
        """Stop any running SubscriberThread and exit the application."""
        self.stop_worker.emit()
        self.thread.exit()
        self.thread.wait()
        self.close()

    @pyqtSlot(dict)
    def update_readings(self, readings):
        """slot for SubscriberThread: receives latest hardware readings
        and updates the GUI.
        """
        self._update_cpu_cores(readings)
        self._update_utilization_graphs(readings)
        self._update_ram(readings)
        self._update_temperature(readings)

    def _update_cpu_cores(self, readings):
        """Update CPU core QLCDs."""
        for i, qlcd in enumerate(self.core_qlcd):
            try:
                val = readings["cpu"]["cores"]["utilization"][i]
            except IndexError:
                val = 0
            qlcd.display(val)
            self._set_qlcd_color(qlcd)

    def _update_utilization_graphs(self, readings):
        """Update utilization time series graph. Remove oldest item and add new reading as latest."""
        for key in self.utilization_plots:
            # Update old x and y values keeping only the latest n values
            old_data = self.utilization_plots[key].getData()

            # Ignore this reading if older than the latest data point in graph.
            # (Pub/Sub does not guarantee ordering by default. Fix: enable ordering?)
            if readings["timestamp"] <= old_data[0][-1]:
                logging.warn("Discarding out-of-order item. Age: %ds", time.time() - readings["timestamp"])
                return
            
            x = np.append(old_data[0][1:], readings["timestamp"])
            y = np.append(old_data[1][1:], readings[key]["utilization"])

            self.utilization_plots[key].setData(x, y)

    def _update_ram(self, readings):
        """Update RAM usage bars plot and labels."""
        system_used = int(readings["ram"]["used"] / readings["ram"]["total"] * 100)
        self.system_mem_bg_used.setOpts(height=[system_used])
        self.system_mem_bar_label.setText("{}%".format(system_used))
        self.system_mem_label.setText("{:.1f}GB".format(readings["ram"]["used"]/1000))

        gpu_mem_used = int(readings["gpu"]["memory.used"] / readings["gpu"]["memory.total"] * 100)
        self.gpu_mem_bg_used.setOpts(height=[gpu_mem_used])
        self.gpu_mem_bar_label.setText("{}%".format(gpu_mem_used))
        self.gpu_mem_label.setText("{:.1f}GB".format(readings["gpu"]["memory.used"]/1000))

    def _update_temperature(self, readings):
        """Update temperature QLabels."""
        cpu_temperature = f"{readings['cpu']['temperature']}°C"
        gpu_temperature = f"{readings['gpu']['temperature']}°C"
        self.gpu_temperature.setText(cpu_temperature)
        self.cpu_temperature.setText(gpu_temperature)

    def _set_qlcd_color(self, qlcd):
        """Set QLCD background color based on its value. Lighter value for low values and
        darker for high values.
        Uses HSL color codes with varying lightness value.
        """ 
        value = qlcd.intValue()

        # saturation: 20 -> 42 and 100 -> 100
        saturation = utils.interpolate((20, 42), (100, 100), value)
        
        # lightness: 20 -> 79 and 100 -> 30
        lightness = utils.interpolate((20, 79), (100, 30), value)

        if value <= 20:
            saturation = 42
            lightness = 79
            
        qlcd.setStyleSheet(f"QLCDNumber {{ background-color: hsl(218, {saturation}%, {lightness}%) }}")


class PubSubWorker(QObject):
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.pull_timer = QTimer(self)

    def run(self):
        """Setup a Pub/Sub message pull every UPDATE_INTERVAL seconds."""
        empty_pull_counter = 0
        subscriber = Subscriber()

        def pull():
            nonlocal empty_pull_counter
            try:
                message = subscriber.pull_message()
                readings = json.loads(message.data.decode("utf-8"))
                readings["timestamp"] = message.publish_time.timestamp()
                self.update.emit(readings)
                empty_pull_counter = 0
            except DeadlineExceeded:
                # If this is the 2nd consecutive empty pull, reset all widgets
                if empty_pull_counter >= 1:
                    logger.info("Nothing received from topic for a while, resetting charts.")

                    # Emit an empty response with current timestamp to avoid
                    # discarding it as too old.
                    readings = EMPTY_TEMPLATE.copy()
                    readings["timestamp"] = time.time()
                    self.update.emit(readings)

                    empty_pull_counter += 1
                else:
                    logger.debug("Nothing received from topic.")
                    empty_pull_counter += 1

        subscriber.seek_to_time(int(time.time()))
        pull()
        self.pull_timer.timeout.connect(pull)
        self.pull_timer.start(UPDATE_INTERVAL * 1000)

    @pyqtSlot()
    def stop(self):
        self.pull_timer.stop()


class PercentAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [f"{int(v)}%" for v in values]
