import logging
import time

from google.api_core.exceptions import DeadlineExceeded
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
    QSizePolicy
)
import pyqtgraph as pg

from pubsub_utils import UPDATE_INTERVAL
from pubsub_utils.hw_stats import EMPTY_TEMPLATE
from pubsub_utils.subscriber import Subscriber


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

        base_layout = QGridLayout()
        main_widget.setLayout(base_layout)

        cpu_core_grid = QGridLayout()
        timeline_grid = QGridLayout()
        ram_grid = QGridLayout()

        base_layout.addLayout(cpu_core_grid, 0, 0, 1, 2)
        base_layout.addLayout(timeline_grid, 1, 0)
        base_layout.addLayout(ram_grid, 1, 1)

        # Set more space to bottom row
        base_layout.setRowStretch(0, 1)
        base_layout.setRowStretch(1, 2)

        # Set more space to left column
        base_layout.setColumnStretch(0, 2)
        base_layout.setColumnStretch(1, 1)


        ### CPU utilization, top row
        cpu_title_label = QLabel("CPU", objectName="cpu_title_label")
        #cpu_core_grid.addWidget(cpu_title_label, 0, 0)

        cpu_utilization_label = QLabel("%")
        cpu_utilization_label.adjustSize()
        #cpu_core_grid.addWidget(cpu_utilization_label, 1, 0)

        # Close button, top right
        close_button = QPushButton("Close ")
        close_button.setIcon(QIcon("resources/iconfinder_Close_1891023.png"))
        close_button.setLayoutDirection(Qt.RightToLeft)
        cpu_core_grid.addWidget(close_button, 0, 4)
        close_button.clicked.connect(self.stop_thread_and_exit)
        close_button.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Expanding
        )

        self.clock_lcd = QLCDNumber(5, self, objectName="clock_qlcd")
        self.clock_lcd.setSegmentStyle(QLCDNumber.Flat)
        cpu_core_grid.addWidget(self.clock_lcd, 0, 1, 1, 3)
        self.setup_clock_polling()

        ### CPU core utilization grid
        # Currently fixed to showing 4 cores.
        # TODO dynamic row count based on cores available
        NUM_QLCD_PER_ROW = 4
        self.core_qlcd = []
        for col in range(1, NUM_QLCD_PER_ROW+1):
            qlcd = QLCDNumber(self)
            qlcd.setDigitCount(2)
            qlcd.display(0)
            qlcd.setSegmentStyle(QLCDNumber.Flat)
            cpu_core_grid.addWidget(qlcd, 1, col)
            self.core_qlcd.append(qlcd)


        ### CPU & GPU time series grid
        # TODO
        date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation="bottom")
        percent_axis = PercentAxisItem(orientation="left")
        graph = pg.PlotWidget(axisItems = {"bottom": date_axis, "left": percent_axis})

        import numpy as np
        from datetime import datetime, timedelta
        x = [time.time() - i for i in range(10)]
  
        graph.addLegend() # Needs to be called before plotting series
        graph.plot(x, np.random.normal(loc=5, size=(10,)), pen="b", name="CPU")
        graph.plot(x, np.random.normal(loc=5, size=(10,)), pen="g", name="GPU")

        timeline_grid.addWidget(graph, 0, 0)


        ### RAM grid, bottom right
        ram_plot = pg.plot()
        ram_plot.setTitle("<h2>RAM</h2>")

        x_labeled = {0: "RAM", 1: "GPU"}
        x = list(x_labeled.keys())

        self.system_mem_bg_used = pg.BarGraphItem(x=[x[0]], height=[0], width=0.6, brush="#0E1F06")
        self.gpu_mem_bg_used = pg.BarGraphItem(x=[x[1]], height=[0], width=0.6, brush="#0E1F06")
        ram_plot.addItem(self.system_mem_bg_used)
        ram_plot.addItem(self.gpu_mem_bg_used)

        # Add labels on top of bars
        bar_label_font = QFont()
        bar_label_font.setPixelSize(20)

        self.system_mem_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.system_mem_bar_label.setPos(0, 10)
        self.system_mem_bar_label.setFont(bar_label_font)
        ram_plot.addItem(self.system_mem_bar_label)

        self.gpu_mem_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.gpu_mem_bar_label.setPos(1, 10)
        self.gpu_mem_bar_label.setFont(bar_label_font)
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

        font = QFont()
        font.setPixelSize(22)
        self.ram_used_label = pg.TextItem("GB", fill="#660000", anchor=(1,1))
        self.ram_used_label.setFont(font)
        self.ram_used_label.setPos(X_MAX, 0.7 * Y_MAX)
        ram_plot.addItem(self.ram_used_label)

        ram_grid.addWidget(ram_plot, 0, 0)


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
        self.cpu_readings = []
        self.gpu_readings = []
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
        #self._update_gpu(readings)
        self._update_ram(readings)

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
        self.cpu_readings

    def _update_ram(self, readings):
        """Update RAM usage bar plot and labels."""
        used = int(readings["ram"]["used"] / readings["ram"]["total"] * 100)

        self.system_mem_bg_used.setOpts(height=[used])
        self.system_mem_bar_label.setText("{}%".format(used))
        #self.ram_available_bar_label.setText("{}%".format(available))

        self.ram_used_label.setText("{:.1f}GB".format(readings["ram"]["used"]/1000))

    def _update_gpu(self, readings):
        used = int(readings["gpu"]["memory.used"] / readings["gpu"]["memory.total"] * 100)
        utilization = readings["gpu"]["utilization"]
        temperature = readings["gpu"]["temperature"]

        self.gpu_bg_used.setOpts(height=[used])
        self.gpu_bg_utilization.setOpts(height=[utilization])
        self.gpu_used_bar_label.setText("{}%".format(used))
        self.gpu_utilization_bar_label.setText("{}%".format(utilization))

        self.gpu_utilization_label.setText("{:d}%".format(utilization))
        self.gpu_temp_label.setText("{}°C".format(temperature))

    def _set_qlcd_color(self, qlcd):
        """Set QLCD background color based on its value. Lighter value for low values and
        darker for high values.
        Uses HSL color codes with varying lightness value.
        """ 
        value = qlcd.intValue()
        if value <= 20:
            lightness = 62
        else:
            # Create a linear function for lightness value with 20 -> 62 and 100 -> 25
            k = (25-62)/(100-20)
            b = 25 - k * 100  # f(x) = kx + b
            lightness = int(k*value + b)
            
        qlcd.setStyleSheet(f"QLCDNumber {{ background-color: hsl(0, 100%, {lightness}%) }}")


class PubSubWorker(QObject):
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.pull_timer = QTimer(self)

    def run(self):
        """Setup a Pub/Sub message pull every UPDATE_INTERVAL seconds.
        Note that this runs on the same thread as the GUI.
        """
        empty_pull_counter = 0
        subscriber = Subscriber()

        def pull():
            nonlocal empty_pull_counter
            try:
                readings = subscriber.pull_message()
                logger.debug(readings)
                self.update.emit(readings)
                empty_pull_counter = 0
            except DeadlineExceeded:
                logger.debug("Nothing received from topic.")

                # If this is the 3rd consecutive empty pull, reset all widgets (unless already empty)
                if empty_pull_counter == 2:
                    logger.info("Nothing received from topic for a while, resetting charts.")
                    self.update.emit(EMPTY_TEMPLATE)
                    empty_pull_counter += 1
                else:
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
        return [f"{v}%" for v in values]