import sqlite3
import sys
from pathlib import Path

# Local module imports
from canvas import MplCanvas
from database import init_dummy_database
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from workers import TranslationWorker, WorkerThread


class StreamRedirector(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 App Template")
        self.resize(800, 600)

        # Set up a dummy database for demonstration
        self.db_name = str(Path(__file__).parent.parent / "data" / "app_data.db")
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

        # Setup Table Selector
        self.table_selector = QComboBox()
        self.table_selector.addItems(self.db.tables())
        self.table_selector.currentTextChanged.connect(self.change_table_view)
        layout.addWidget(self.table_selector)

        # Setup Table Model
        self.model = QSqlTableModel(self, self.db)

        # Select initially chosen table
        initial_table = self.table_selector.currentText()
        if initial_table:
            self.model.setTable(initial_table)
            self.model.select()

        # Setup Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Database Viewer")

    def change_table_view(self, table_name):
        """Updates the table model when a new table is selected."""
        self.model.setTable(table_name)
        self.model.select()

    # --- Tab 2: Matplotlib Graphing ---
    def init_graph_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.metric_selector = QComboBox()
        self.metric_selector.addItems(["LaBSE", "Fidelity", "BLEU", "COMET", "TTR"])
        self.metric_selector.currentTextChanged.connect(self.plot_data)
        layout.addWidget(self.metric_selector)

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
        selected_metric = self.metric_selector.currentText()
        if not selected_metric:
            selected_metric = "LaBSE"

        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        # Average score per Model for the selected metric
        cur.execute(f"""
            SELECT m2.Name, AVG(m1.{selected_metric})
            FROM Translations t
            JOIN Metrics m1 ON t.TranslationID = m1.Translation
            JOIN Model m2 ON t.Model = m2.ModelID
            GROUP BY m2.Name
        """)
        data = cur.fetchall()
        con.close()

        models = [row[0] for row in data]
        scores = [row[1] if row[1] is not None else 0 for row in data]

        self.canvas.axes.cla()  # Clear current axes
        self.canvas.axes.bar(models, scores, color="skyblue")
        self.canvas.axes.set_title(f"Average {selected_metric} Score per Model")
        self.canvas.axes.set_ylabel(f"Average {selected_metric} Score")
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

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output)

        self.redirector = StreamRedirector()
        self.redirector.text_written.connect(self.append_console_text)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Multithreading")

    def append_console_text(self, text):
        if "\r" in text:
            parts = text.split("\r")
            for i, part in enumerate(parts):
                if i > 0:
                    cursor = self.console_output.textCursor()
                    from PyQt6.QtGui import QTextCursor

                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.removeSelectedText()
                if part:
                    self.console_output.insertPlainText(part)
        else:
            self.console_output.insertPlainText(text)
        self.console_output.ensureCursorVisible()

    def start_worker_thread(self):
        self.start_thread_btn.setEnabled(False)
        self.thread_label.setText("Thread Status: Running (0%)")

        self.worker = TranslationWorker()
        self.worker.progress_update.connect(self.update_thread_progress)
        self.worker.task_finished.connect(self.thread_complete)
        self.worker.error_occurred.connect(self.thread_error)
        self.worker.start()

    def update_thread_progress(self, val):
        self.thread_label.setText(f"Thread Status: Running ({val}%)")

    def thread_complete(self, message):
        self.thread_label.setText(f"Thread Status: {message}")
        self.start_thread_btn.setEnabled(True)
        self.plot_data()

    def thread_error(self, message):
        self.thread_label.setText(f"Thread Status: Error")
        QMessageBox.critical(self, "Pipeline Error", message)
        self.start_thread_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
