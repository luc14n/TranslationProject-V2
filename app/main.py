import sqlite3
import sys

# Local module imports
from canvas import MplCanvas
from database import init_dummy_database
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from workers import WorkerThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 App Template")
        self.resize(800, 600)

        # Set up a dummy database for demonstration
        self.db_name = "app_data.db"
        init_dummy_database(self.db_name)

        # Main Layout (Tabbed Interface)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialize UI Tabs
        self.init_db_view_tab()
        self.init_graph_tab()
        self.init_file_management_tab()
        self.init_multithreading_tab()

    # --- Tab 1: SQLite Data Viewer ---
    def init_db_view_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Connect to SQLite using QtSql
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(self.db_name)
        if not self.db.open():
            QMessageBox.critical(self, "Database Error", "Could not open database.")
            return

        # Setup Table Model
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("Translations")
        self.model.select()

        # Setup Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Database Viewer")

    # --- Tab 2: Matplotlib Graphing ---
    def init_graph_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)

        refresh_btn = QPushButton("Refresh Graph from DB")
        refresh_btn.clicked.connect(self.plot_data)
        layout.addWidget(refresh_btn)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Data Graphing")
        self.plot_data()  # Initial plot

    def plot_data(self):
        """Fetches data from SQLite and plots it on the canvas."""
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        # Count translations by target language
        cur.execute("SELECT Language, COUNT(*) FROM Translations GROUP BY Language")
        data = cur.fetchall()
        con.close()

        languages = [row[0] for row in data]
        counts = [row[1] for row in data]

        self.canvas.axes.cla()  # Clear current axes
        self.canvas.axes.bar(languages, counts, color="skyblue")
        self.canvas.axes.set_title("Translations per Language")
        self.canvas.axes.set_ylabel("Number of Translations")
        self.canvas.draw()

    # --- Tab 3: File Management ---
    def init_file_management_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.file_label = QLabel("No file selected.")
        layout.addWidget(self.file_label)

        open_btn = QPushButton("Open File...")
        open_btn.clicked.connect(self.open_file_dialog)
        layout.addWidget(open_btn)

        save_btn = QPushButton("Save File As...")
        save_btn.clicked.connect(self.save_file_dialog)
        layout.addWidget(save_btn)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "File Management")

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*);;Text Files (*.txt)"
        )
        if file_path:
            self.file_label.setText(f"Opened: {file_path}")

    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "Text Files (*.txt)"
        )
        if file_path:
            self.file_label.setText(f"Saved to: {file_path}")

    # --- Tab 4: Multithreading ---
    def init_multithreading_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.thread_label = QLabel("Thread Status: Idle")
        layout.addWidget(self.thread_label)

        self.start_thread_btn = QPushButton("Start Background Task")
        self.start_thread_btn.clicked.connect(self.start_worker_thread)
        layout.addWidget(self.start_thread_btn)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Multithreading")

    def start_worker_thread(self):
        self.start_thread_btn.setEnabled(False)
        self.thread_label.setText("Thread Status: Running (0%)")

        self.worker = WorkerThread()
        self.worker.progress_update.connect(self.update_thread_progress)
        self.worker.task_finished.connect(self.thread_complete)
        self.worker.start()

    def update_thread_progress(self, val):
        self.thread_label.setText(f"Thread Status: Running ({val}%)")

    def thread_complete(self, message):
        self.thread_label.setText(f"Thread Status: {message}")
        self.start_thread_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
