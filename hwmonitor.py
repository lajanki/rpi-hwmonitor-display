import logging

import publisher
import hwmonitorGUI


logging.basicConfig(format="%(asctime)s - %(message)s", level="INFO")



class App:

    def __init__(self):
        self.main_window = hwmonitorGUI.MainWindow()
        t = hwmonitorGUI.SubscriberThread(self.main_window)

        # Fetch initial readings directly from the utility function
        stats = publisher.get_stats()
        self.main_window.update_readings(stats)

        t.start()






