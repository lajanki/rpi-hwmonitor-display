import os.path
import logging
import time

from google.api_core.exceptions import DeadlineExceeded
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
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

from pubsub_utils import subscriber, UPDATE_INTERVAL
from pubsub_utils.hw_stats import EMPTY_TEMPLATE


logger = logging.getLogger()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.empty_pull_counter = 0
        subscriber.seek_to_time(int(time.time()))
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget(objectName="main_window") # dummy widget to hold a layout
        main_widget.setAutoFillBackground(True)
        self.setCentralWidget(main_widget)
        
        base_layout = QGridLayout()
        main_widget.setLayout(base_layout)

        cpu_grid = QGridLayout()
        gpu_grid = QGridLayout()
        ram_grid = QGridLayout()

        base_layout.addLayout(cpu_grid, 0, 0, 1, 2)
        base_layout.addLayout(ram_grid, 1, 0)
        base_layout.addLayout(gpu_grid, 1, 1)
  
        base_layout.setRowStretch(0, 7)
        base_layout.setRowStretch(1, 8)

        ### CPU row (top row)
        cpu_title_label = QLabel("CPU", objectName="cpu_title")
        cpu_grid.addWidget(cpu_title_label, 0, 0)

        cpu_utilization_label = QLabel("%")
        cpu_utilization_label.adjustSize()
        cpu_grid.addWidget(cpu_utilization_label, 1, 0)
        cpu_grid.addWidget(QLabel("MHz"), 2, 0)
        cpu_grid.addWidget(QLabel("°C "), 3, 0)

        # Close button, top right
        close_button = QPushButton("Close ")
        close_button.setIcon(QIcon("resources/iconfinder_Close_1891023.png"))
        close_button.setLayoutDirection(Qt.RightToLeft)
        cpu_grid.addWidget(close_button, 0, 4)
        close_button.clicked.connect(self.stop_thread_and_exit)

        # Increase close button size 
        close_button.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Expanding
        )
        cpu_grid.setRowStretch(0, 3)
        cpu_grid.setRowStretch(1, 2)
        cpu_grid.setRowStretch(2, 2)
        cpu_grid.setRowStretch(3, 2)

        self.cpu_utilization_reading = []
        for i in range(4):
            qlcd = QLCDNumber(self)
            qlcd.setDigitCount(2)
            qlcd.display(0)
            cpu_grid.addWidget(qlcd, 1, i+1)
            qlcd.setSegmentStyle(QLCDNumber.Flat)
            self.cpu_utilization_reading.append(qlcd)

        self.cpu_frequency_readings = []
        for i in range(4):
            qlcd = QLCDNumber(self)
            qlcd.setDigitCount(4)
            qlcd.display(0)
            cpu_grid.addWidget(qlcd, 2, i+1)
            qlcd.setSegmentStyle(QLCDNumber.Flat)
            self.cpu_frequency_readings.append(qlcd)

        self.cpu_temperature_readings = []
        for i in range(4):
            qlcd = QLCDNumber(self)
            qlcd.setDigitCount(2)
            qlcd.display(0)
            cpu_grid.addWidget(qlcd, 3, i+1)
            qlcd.setSegmentStyle(QLCDNumber.Flat)
            self.cpu_temperature_readings.append(qlcd)


        ### RAM section (bottom left column)
        ram_plot = pg.plot()
        ram_plot.setTitle("<h2>RAM</h2>")

        x_labeled = {0: "used", 1: "available"}
        x = list(x_labeled.keys())

        self.ram_bg_used = pg.BarGraphItem(x=[x[0]], height=[0], width=0.6, brush="#134d00")
        self.ram_bg_available = pg.BarGraphItem(x=[x[1]], height=[0], width=0.6, brush="#269900")
        ram_plot.addItem(self.ram_bg_used)
        ram_plot.addItem(self.ram_bg_available)

        # Add labels on top of bars 
        bar_label_font = QFont()
        bar_label_font.setPixelSize(20)

        self.ram_used_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.ram_used_bar_label.setPos(0, 10)
        self.ram_used_bar_label.setFont(bar_label_font)
        ram_plot.addItem(self.ram_used_bar_label)

        self.ram_available_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.ram_available_bar_label.setPos(1, 10)
        self.ram_available_bar_label.setFont(bar_label_font)
        ram_plot.addItem(self.ram_available_bar_label)

        ram_plot.setXRange(-0.5, 2.5)
        ram_plot.setYRange(0, 100)
        ram_plot.setMouseEnabled(x=False, y=False)

        xax = ram_plot.getAxis("bottom")
        xax.setTicks([list(x_labeled.items())])
        ram_plot.hideAxis("left")

        # Add labels RAM usage to the right side of the plot
        view_range = ram_plot.viewRange()
        X_MAX = view_range[0][1]
        Y_MAX = view_range[1][1]

        font=QFont()
        font.setPixelSize(22)

        self.ram_used_label = pg.TextItem("GB", fill="#660000", anchor=(1,1))
        self.ram_used_label.setFont(font)
        self.ram_used_label.setPos(X_MAX, 0.7 * Y_MAX)
        ram_plot.addItem(self.ram_used_label)  

        ram_grid.addWidget(ram_plot, 0, 0)


        ### GPU section (bottom right column)
        gpu_plot = pg.plot()
        gpu_plot.setTitle("<h2>GPU</h2>")

        x_labeled = {0: "used", 1: "utilization"}
        x = list(x_labeled.keys())

        self.gpu_bg_used = pg.BarGraphItem(x=[x[0]], height=[0], width=0.6, brush="#00004d")
        self.gpu_bg_utilization = pg.BarGraphItem(x=[x[1]], height=[0], width=0.6, brush="#000099")
        gpu_plot.addItem(self.gpu_bg_used)
        gpu_plot.addItem(self.gpu_bg_utilization)

        # Add labels on top of bars 
        self.gpu_used_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.gpu_used_bar_label.setPos(0, 10)
        self.gpu_used_bar_label.setFont(bar_label_font)
        gpu_plot.addItem(self.gpu_used_bar_label)

        self.gpu_utilization_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.gpu_utilization_bar_label.setPos(1, 10)
        self.gpu_utilization_bar_label.setFont(bar_label_font)
        gpu_plot.addItem(self.gpu_utilization_bar_label)

        gpu_plot.setXRange(-0.5, 2.5)
        gpu_plot.setYRange(0, 100)
        gpu_plot.setMouseEnabled(x=False, y=False)

        xax = gpu_plot.getAxis("bottom")
        xax.setTicks([list(x_labeled.items())])
        gpu_plot.hideAxis("left")

        # Add label for current utilization and temperature
        view_range = gpu_plot.viewRange()
        X_MAX = view_range[0][1]
        Y_MAX = view_range[1][1]

        self.gpu_utilization_label = pg.TextItem("%", fill="#660000", anchor=(1,1))
        self.gpu_utilization_label.setFont(font)
        self.gpu_utilization_label.setPos(X_MAX, 0.73 * Y_MAX)
        gpu_plot.addItem(self.gpu_utilization_label)  

        self.gpu_temp_label = pg.TextItem("°C", fill="#660000", anchor=(1,1))
        self.gpu_temp_label.setFont(font)
        self.gpu_temp_label.setPos(X_MAX, 0.5 * Y_MAX)
        gpu_plot.addItem(self.gpu_temp_label)  

        gpu_grid.addWidget(gpu_plot, 0, 0)


        with open("style.qss") as f:
           self.setStyleSheet(f.read())

        self.resize(620, 420)
        self.setWindowTitle("HWMonitor")
        self.setWindowIcon(QIcon("resources/iconfinder_gnome-system-monitor_23964.png"))
        self.center()
        
        self.pull()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.pull)

        timer_wait_ms = UPDATE_INTERVAL * 1000
        self.timer.start(timer_wait_ms)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def pull(self):
        """Pull a single message from the topic.
        Note that this runs on the same thread as the GUI.
        """
        try:
            readings = subscriber.pull_message()
            logger.debug(readings)
            self.update_readings(readings)
            self.empty_pull_counter = 0
        except DeadlineExceeded:
            logger.debug("Nothing received from topic.")

            # If this is the 3rd consecutive empty pull, reset all widgets
            if self.empty_pull_counter >= 2:
                logger.info("Nothing received from topic for a while, resetting charts.")
                readings = EMPTY_TEMPLATE.copy()
                self.update_readings(readings)
                self.empty_pull_counter = 0
                
            else:
                self.empty_pull_counter += 1


    @pyqtSlot()
    def stop_thread_and_exit(self):
        """Stop any running SubscriberThread and exit the application."""
        self.timer.stop()
        self.close()

    @pyqtSlot(dict)
    def update_readings(self, readings):
        """slot for SubscriberThread: receives latest hardware readings
        and updates the GUI.
        """        
        self._update_cpu(readings)
        self._update_gpu(readings)
        self._update_ram(readings)

    def _update_cpu(self, readings):
        for i, qlcd in enumerate(self.cpu_utilization_reading):
            qlcd.display(readings["cpu"]["utilization"][i])
            self._check_and_set_qlcd_color(qlcd, 80)

        for i, qlcd in enumerate(self.cpu_frequency_readings):
            qlcd.display(readings["cpu"]["freq"][i])

        for i, qlcd in enumerate(self.cpu_temperature_readings):
            qlcd.display(readings["cpu"]["temperature"][i])
            self._check_and_set_qlcd_color(qlcd, 80)


    def _update_ram(self, readings):
        used = int(readings["ram"]["used"] / readings["ram"]["total"] * 100)
        available = int(readings["ram"]["available"] / readings["ram"]["total"] * 100)

        # Update bar heights and labels
        self.ram_bg_used.setOpts(height=[used])
        self.ram_bg_available.setOpts(height=[available])
        self.ram_used_bar_label.setText("{}%".format(used))
        self.ram_available_bar_label.setText("{}%".format(available))

        # Update used GB label
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

    def _check_and_set_qlcd_color(self, qlcd, threshold):
        """Change specified QLCDNumber color between red and white based on
        current value.
        """
        if qlcd.intValue() > threshold:
            qlcd.setStyleSheet("QLCDNumber { color: red }")
        else:
            qlcd.setStyleSheet("QLCDNumber { color: white }")