import time

from PyQt6.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    """
    A simple worker thread to handle long-running background tasks
    without freezing the main GUI.
    """

    progress_update = pyqtSignal(int)
    task_finished = pyqtSignal(str)

    def run(self):
        # Simulate a time-consuming task (e.g., heavy data processing)
        for i in range(1, 101):
            time.sleep(0.05)
            self.progress_update.emit(i)

        self.task_finished.emit("Background task completed successfully!")
