import asyncio
import importlib
import os
import sys
import time

from PyQt6.QtCore import QThread, pyqtSignal

# Add backend directory to sys.path to allow importing Stochastic Chain
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.append(backend_path)


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


class TranslationWorker(QThread):
    """
    A worker thread to run the asynchronous translation pipeline.
    """

    progress_update = pyqtSignal(int)
    task_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            # Import dynamically because of the space in the filename
            stochastic_chain = importlib.import_module("Stochastic Chain")

            # Execute the async main() from the backend script
            asyncio.run(stochastic_chain.main())

            self.task_finished.emit("Translation pipeline completed successfully!")
        except Exception as e:
            self.error_occurred.emit(f"Error in translation pipeline: {str(e)}")
