import os.path
from functools import partial
from collections import namedtuple
import time
import json
import pytz
from datetime import datetime

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
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

import subscriber


# Create namedtuples for storing button and label configurations
ButtonConfig = namedtuple("ButtonConfig", ["text", "position", "slot", "icon", "size_policy"])
ButtonConfig.__new__.__defaults__ = (
    None, None, None, None, (QSizePolicy.Preferred, QSizePolicy.Preferred))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
  
        base_layout.setRowStretch(0, 2)
        base_layout.setRowStretch(1, 3)

        ### CPU row (top row)
        cpu_title_label = QLabel("CPU", objectName="cpu_title")
        cpu_grid.addWidget(cpu_title_label, 0, 0)

        cpu_utilization_label = QLabel("%")
        cpu_utilization_label.adjustSize()
        cpu_grid.addWidget(cpu_utilization_label, 1, 0)
        cpu_grid.addWidget(QLabel("MHz"), 2, 0)
        cpu_grid.addWidget(QLabel("°C "), 3, 0)

        # Close button, top right
        close_button = QPushButton("Close")
        cpu_grid.addWidget(close_button, 0, 4)
        close_button.clicked.connect(self.stop_thread_and_exit)

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
        self.ram_used_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.ram_used_bar_label.setPos(0, 10)
        ram_plot.addItem(self.ram_used_bar_label)

        self.ram_available_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.ram_available_bar_label.setPos(1, 10)
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
        font.setPixelSize(18)

        self.ram_used_label = pg.TextItem("Used: GB", fill="#660000", anchor=(1,1))
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
        gpu_plot.addItem(self.gpu_used_bar_label)

        self.gpu_utilization_bar_label = pg.TextItem("%", anchor=(0.5, 0.5))
        self.gpu_utilization_bar_label.setPos(1, 10)
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
        self.gpu_utilization_label.setPos(X_MAX, 0.7 * Y_MAX)
        gpu_plot.addItem(self.gpu_utilization_label)  

        self.gpu_temp_label = pg.TextItem("°C", fill="#660000", anchor=(1,1))
        self.gpu_temp_label.setFont(font)
        self.gpu_temp_label.setPos(X_MAX, 0.5 * Y_MAX)
        gpu_plot.addItem(self.gpu_temp_label)  

        gpu_grid.addWidget(gpu_plot, 0, 0)


        with open("style.qss") as f:
           self.setStyleSheet(f.read())

        #self.setLayout(base_layout)
        self.resize(620, 420)
        self.center()

        self.setWindowTitle("HWMonitor")
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    @pyqtSlot()
    def stop_thread_and_exit(self):
        """Stop any running SubscriberThread and exit the application."""
        #for thread in SubscriberThread._instances:
            #thread.requestInterruption()
            #thread.exit()

        # [t.terminate() for t in SubscriberThread._instances]
        # print([t.isRunning() for t in SubscriberThread._instances])
        # print(SubscriberThread._instances)

        #self.close()

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

        for i, qlcd in enumerate(self.cpu_frequency_readings):
            qlcd.display(readings["cpu"]["freq"][i])

        for i, qlcd in enumerate(self.cpu_temperature_readings):
            qlcd.display(readings["cpu"]["temperature"][i])

    def _update_ram(self, readings):
        used = int(readings["ram"]["used"] / readings["ram"]["total"] * 100)
        available = int(readings["ram"]["available"] / readings["ram"]["total"] * 100)

        # Update bar heights and labels
        self.ram_bg_used.setOpts(height=[used])
        self.ram_bg_available.setOpts(height=[available])
        self.ram_used_bar_label.setText("{}%".format(used))
        self.ram_available_bar_label.setText("{}%".format(available))

        # Update used GB label
        self.ram_used_label.setText("Used: {:.1f}GB".format(readings["ram"]["used"]/1000)) 

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


class SubscriberThread(QThread):
    _instances = []

    def __init__(self, parent_window):
        self.parent = parent_window
        self.refresh_signal = RefreshSignal()
        self.refresh_signal.signal.connect(parent_window.update_readings)
        self.THREAD_START_TIME = pytz.UTC.localize(datetime.utcnow()) 

        super(SubscriberThread, self).__init__(parent_window)
        SubscriberThread._instances.append(self)

    def run(self):
        subscriber.listen_for_messages(self.pull_and_emit_stats)

    def pull_and_emit_stats(self, message):
        """Callback to pubsub subscriber: decode the message and pass
        latest values to individual update functions.
        """
        readings = json.loads(message.data.decode("utf-8"))
        message.ack()

        # Ignore messages that were published before the subscriber
        # was ready.
        if message.publish_time >= self.THREAD_START_TIME:
            self.refresh_signal.signal.emit(readings)


class RefreshSignal(QObject):
    signal = pyqtSignal(dict)
