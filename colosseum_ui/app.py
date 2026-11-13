"""Desktop execution and artifact inspection."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFontDatabase, QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QTabWidget,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .artifacts import format_summary_text, load_run_browser_snapshot, load_run_snapshot
from .console import Console
from .execution import Execution, RunRequest
from .theme import _GAP, _MARGIN, _STATUS_COLORS, apply_theme

_POLL_MS = 50
_HISTORY_BATCH = 100
_RECENT_RUN_LIMIT = 20
_RECENT_ROW_HEIGHT = 52
_FILE_STATUS_WIDTH = 92
_FILE_NAME_WIDTH = 280
_DEFAULT_SIZE = (1100, 746)
_MINIMUM_SIZE = (760, 580)
_STATUS_VERTICAL_MARGIN = 4
_STATUS_RIGHT_MARGIN = 8


class Inspector(QMainWindow):
    def __init__(self, cwd=None):
        super().__init__()
        self.cwd = cwd or Path.cwd()
        self.execution = Execution(self.cwd, self)
        self.execution.output.connect(self.append_output)
        self.execution.state_changed.connect(self.update_controls)
        self.execution.completed.connect(self.run_finished)
        self.closing = False
        self.selected = None
        self.generation = 0
        self.jobs = []
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.setWindowTitle("Colosseum")
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/colosseum.ico")))
        self.resize(*_DEFAULT_SIZE)
        self.setMinimumSize(*_MINIMUM_SIZE)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _GAP)
        layout.setSpacing(_GAP)
        self.build_form(layout)
        toolbar = QHBoxLayout()
        for label, callback in (("Live output", self.show_live), ("Open output folder", self.open_folder)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.wrap = QCheckBox("Wrap text")
        self.wrap.toggled.connect(lambda checked: self.log.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if checked else QPlainTextEdit.LineWrapMode.NoWrap))
        toolbar.addWidget(self.wrap)
        layout.addLayout(toolbar)
        splitter = QSplitter()
        self.tabs = QTabWidget()
        self.log = Console()
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        paging = QHBoxLayout()
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.hide()
        for caption, direction in (("Previous page", -1), ("Next page", 1)):
            button = QPushButton(caption)
            button.clicked.connect(lambda checked=False, delta=direction: self.log.turn_page(delta))
            button.hide()
            paging.addWidget(button)
            if direction < 0:
                self.previous_page = button
            else:
                self.next_page = button
        paging.addWidget(self.page_label)
        paging.addStretch()
        log_layout.addWidget(self.log, 1)
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Enter a response and press Enter")
        self.input_line.setAccessibleName("Runner input")
        self.input_line.returnPressed.connect(self.send_input)
        log_layout.addWidget(self.input_line)
        log_layout.addLayout(paging)
        self.log.page_changed.connect(self.update_paging)
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.log.setPlaceholderText("Select a run to inspect its debug log.")
        self.tabs.addTab(log_panel, "Log")
        self.summary_content = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_content)
        self.summary_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setWidget(self.summary_content)
        self.tabs.addTab(self.summary_scroll, "Summary")
        self.tabs.currentChanged.connect(self.summary_tab_changed)
        self.current_summary = None
        splitter.addWidget(self.tabs)
        self.tree = QTreeView()
        self.tree.setUniformRowHeights(True)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Files", "Status"])
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setTreePosition(0)
        self._output_rows = {}
        self.tree.expanded.connect(self.populate_output_group)
        self.files_page = QWidget()
        files_layout = QVBoxLayout(self.files_page)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_toolbar = QHBoxLayout()
        files_toolbar.addWidget(QLabel("Files"))
        files_toolbar.addStretch()
        for label, callback in (("Refresh", self.refresh), ("Expand", self.tree.expandAll),
                                ("Collapse", self.tree.collapseAll)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            button.setAccessibleName(label + " files")
            files_toolbar.addWidget(button)
            setattr(self, label.lower() + "_button", button)
        files_layout.addLayout(files_toolbar)
        files_layout.addWidget(self.tree)
        self.right_tabs = QTabWidget()
        self.recent = QListWidget()
        self.right_tabs.addTab(self.recent, "Recent runs")
        self.right_tabs.addTab(self.files_page, "Files")
        self.recent.currentItemChanged.connect(self.select_recent)
        self.tree.selectionModel().currentChanged.connect(self.select_run)
        splitter.addWidget(self.right_tabs)
        splitter.setSizes([680, 400])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(body)
        self.appearance = QComboBox()
        self.appearance.addItems(["System", "Light", "Dark"])
        self.appearance.setAccessibleName("Appearance")
        self.appearance.currentTextChanged.connect(self.change_theme)
        appearance_container = QWidget()
        appearance_layout = QHBoxLayout(appearance_container)
        appearance_layout.setContentsMargins(0, _STATUS_VERTICAL_MARGIN, _STATUS_RIGHT_MARGIN, _STATUS_VERTICAL_MARGIN)
        appearance_layout.setSpacing(_GAP)
        appearance_layout.addWidget(QLabel("Appearance"))
        appearance_layout.addWidget(self.appearance)
        self.statusBar().addPermanentWidget(appearance_container)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        apply_theme(self, "System")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(_POLL_MS)
        self.refresh()
        self.update_controls()

    def change_theme(self, value):
        apply_theme(self, value)
        self.refresh()

    def status_color(self, status):
        key = str(status).upper()
        pair = _STATUS_COLORS.get(key)
        if pair is None:
            return self.palette().color(self.palette().ColorRole.Text)
        dark = self.palette().color(self.palette().ColorRole.Base).lightness() < 128
        return QColor(pair[int(dark)])

    def display_status(self, status):
        return {"PASS": "Pass", "FAIL": "Fail", "ERROR": "Error", "INCOMPLETE": "Incomplete"}.get(
            str(status).upper(), str(status)
        )

    def system_theme_changed(self, scheme):
        if self.appearance.currentText() == "System":
            apply_theme(self, "System")
            self.refresh()

    def build_form(self, layout):
        group = QGroupBox("Execution setup")
        group_layout = QVBoxLayout(group)
        form = QFormLayout()
        form.setHorizontalSpacing(_MARGIN)
        form.setVerticalSpacing(_GAP)
        self.fields = {}
        additional_rows = QVBoxLayout()
        additional_rows.setContentsMargins(0, 0, 0, 0)
        additional_labels = []
        form_labels = []
        for name in ("Test / Suite", "Config", "Parameters", "Metadata"):
            row = QHBoxLayout()
            field = QLineEdit()
            if name == "Config":
                field.setText(os.environ.get("COLOSSEUM_BENCH_CONFIG", ""))
            elif name == "Metadata":
                field.setText(os.environ.get("COLOSSEUM_METADATA_PATH", ""))
            field.setAccessibleName(name)
            field.setToolTip(field.text())
            field.textChanged.connect(field.setToolTip)
            self.fields[name] = field
            field.textChanged.connect(self.update_controls)
            row.addWidget(field)
            browse = QToolButton()
            browse.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
            browse.setToolTip("Choose " + name.lower() + " file")
            browse.setAccessibleName("Choose " + name.lower() + " file")
            browse.clicked.connect(lambda checked=False, n=name: self.browse(n))
            row.addWidget(browse)
            label = QLabel("  Test / suite (.py, .toml)" if name == "Test / Suite" else "  Config" if name == "Config" else "  " + name)
            label.setBuddy(field)
            if name in {"Parameters", "Metadata"}:
                aligned_row = QHBoxLayout()
                aligned_row.addWidget(label)
                aligned_row.addLayout(row)
                additional_rows.addLayout(aligned_row)
                additional_labels.append(label)
            else:
                form.addRow(label, row)
                form_labels.append(label)
            if name == "Config":
                self.additional_button = QToolButton()
                self.additional_button.setText("> Additional")
                self.additional_button.setObjectName("additionalToggle")
                self.additional_button.setAutoRaise(True)
                self.additional_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                self.additional_button.setCheckable(True)
                self.additional_button.setAccessibleName("Show additional parameters and metadata")
                self.additional_button.toggled.connect(self.toggle_additional)
                form.setWidget(form.rowCount(), QFormLayout.ItemRole.LabelRole, self.additional_button)
        label_width = max(label.sizeHint().width() for label in form_labels)
        for label in (*form_labels, *additional_labels):
            label.setFixedWidth(label_width)
        self.additional_widget = QWidget()
        self.additional_widget.setLayout(additional_rows)
        self.additional_widget.setVisible(False)
        form.addRow(self.additional_widget)
        group_layout.addLayout(form)
        actions = QHBoxLayout()
        self.run_button = QPushButton()
        self.run_button.setProperty("primary", True)
        self.run_button.hide()
        self.run_button.clicked.connect(self.run_selected_file)
        actions.addWidget(self.run_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setProperty("danger", True)
        self.stop_button.clicked.connect(self.execution.stop)
        actions.addWidget(self.stop_button)
        self.debug = QCheckBox("Debug")
        self.no_sleep = QCheckBox("No sleep")
        self.dry_run = QCheckBox("Dry run")
        actions.addStretch()
        actions.addWidget(self.debug)
        actions.addWidget(self.no_sleep)
        actions.addWidget(self.dry_run)
        group_layout.addLayout(actions)
        layout.addWidget(group)

    def toggle_additional(self, expanded):
        self.additional_widget.setVisible(expanded)
        self.additional_button.setText("v Additional" if expanded else "> Additional")
        self.additional_button.setAccessibleName(
            "Hide additional parameters and metadata" if expanded else "Show additional parameters and metadata"
        )

    def browse(self, name):
        pattern = "Test and suite (*.py *.toml);;All files (*)" if name == "Test / Suite" else "TOML (*.toml);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, name, str(self.cwd), pattern)
        if path:
            self.fields[name].setText(path)

    def update_controls(self, state=None):
        if not hasattr(self, "run_button"):
            return
        path = self.fields["Test / Suite"].text().strip()
        source = self.cwd / path
        suffix = source.suffix.lower() if source.is_file() else ""
        self.run_button.setText("Run test" if suffix == ".py" else "Run suite" if suffix == ".toml" else "")
        self.run_button.setEnabled(not self.execution.active and suffix in {".py", ".toml"})
        self.run_button.setVisible(suffix in {".py", ".toml"})
        self.stop_button.setEnabled(self.execution.state in {"Starting", "Running"})
        self.input_line.setEnabled(self.execution.state == "Running")
        self.dry_run.setEnabled(not self.execution.active)
        self.statusBar().showMessage(self.execution.state)

    def run_selected_file(self):
        value = self.fields["Test / Suite"].text().strip()
        kind = "run" if Path(value).suffix.lower() == ".py" else "run-suite"
        self.start_run(kind, "Test / Suite")

    def start_run(self, kind, name):
        if self.execution.active:
            return
        self.selected = None
        self.log.start_live()
        self.current_summary = None
        self.render_summary(None)
        self.tabs.setCurrentWidget(self.log)
        values = {key: field.text().strip() for key, field in self.fields.items()}
        self.execution.start(RunRequest(kind, values[name], values["Config"], values["Parameters"],
                                        values["Metadata"], self.debug.isChecked(), self.no_sleep.isChecked(),
                                        self.dry_run.isChecked()))

    def send_input(self):
        self.execution.send_input(self.input_line.text())
        self.input_line.clear()

    def show_live(self):
        self.selected = None
        self.log.show_live()
        self.current_summary = None
        self.render_summary(None)
        self.tabs.setCurrentWidget(self.log)

    def append_output(self, text):
        self.log.append_live(text)

    def run_finished(self, code):
        self.refresh()
        if self.closing:
            self.close()

    def submit(self, kind, function, *args):
        self.jobs.append((kind, self.generation, self.pool.submit(function, *args)))

    def refresh(self):
        self.generation += 1
        self.statusBar().showMessage("Loading runs...")
        self.submit("history", load_run_browser_snapshot, self.cwd)

    def select_run(self, index, previous=None):
        path = index.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self.selected = Path(path)
        self.submit("detail", load_run_snapshot, self.selected)

    def poll(self):
        pending, self.jobs = self.jobs, []
        for kind, generation, future in pending:
            if not future.done():
                self.jobs.append((kind, generation, future))
                continue
            if generation != self.generation:
                continue
            try:
                result = future.result()
                if kind == "history":
                    self.populate(result)
                elif result.run_dir == self.selected:
                    self.log.setPlainText(result.log_error or result.log_text or "debug.log is empty.")
                    self.current_summary = result.summary
                    self.render_summary(result.summary)
            except Exception as exc:  # noqa: BLE001 - isolate filesystem worker failures at UI boundary
                self.statusBar().showMessage(str(exc))

    def populate(self, snapshot):
        expanded = set()

        def remember(parent):
            for i in range(parent.rowCount()):
                item = parent.child(i, 0)
                if item and self.tree.isExpanded(item.index()):
                    expanded.add(item.data(Qt.ItemDataRole.UserRole + 1))
                if item:
                    remember(item)

        remember(self.model.invisibleRootItem())
        self.model.removeRows(0, self.model.rowCount())
        self._output_rows = {}
        recent_rows = []
        groups = {}
        for row in snapshot.rows:
            directory = row.entry.outputs_dir
            self._output_rows.setdefault(directory, []).append(row)
            if directory not in groups:
                label = str(directory.relative_to(self.cwd)) if directory.is_relative_to(self.cwd) else str(directory)
                group = QStandardItem(label)
                group.setToolTip(str(directory))
                group.setEditable(False)
                group.setData(str(directory), Qt.ItemDataRole.UserRole + 1)
                self.model.appendRow(group)
                groups[directory] = group
                if self._output_rows[directory]:
                    group.appendRow(QStandardItem())
                self.tree.setExpanded(group.index(), str(directory) in expanded)
            if len(recent_rows) < _RECENT_RUN_LIMIT:
                recent_rows.append(row)

        self.recent.clear()
        for recent_row in recent_rows:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(recent_row.entry.path))
            item.setToolTip(str(recent_row.entry.path))
            self.recent.addItem(item)
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 4, 4, 4)
            status = QLabel(self.display_status(recent_row.status))
            status.setStyleSheet(f"color: {self.status_color(recent_row.status).name()}; font-weight: 600")
            status.setFixedWidth(84)
            row_layout.addWidget(status)
            description = QVBoxLayout()
            name = QLabel(recent_row.entry.path.name)
            description.addWidget(name)
            date_label = QLabel(datetime.fromtimestamp(recent_row.mtime).strftime("%b %d, %I:%M %p"))
            date_label.setWordWrap(False)
            description.addWidget(date_label)
            name.setWordWrap(False)
            row_layout.addLayout(description, 1)
            item.setSizeHint(QSize(0, _RECENT_ROW_HEIGHT))
            self.recent.setItemWidget(item, row_widget)
        self.tree.setColumnWidth(0, _FILE_NAME_WIDTH)
        self.tree.setColumnWidth(1, _FILE_STATUS_WIDTH)
        self.update_controls()

    def populate_output_group(self, index):
        group = self.model.itemFromIndex(index.siblingAtColumn(0))
        if group is None or group.data(Qt.ItemDataRole.UserRole + 2):
            return
        directory = Path(group.data(Qt.ItemDataRole.UserRole + 1))
        if group.rowCount() and not group.child(0).text():
            group.removeRows(0, group.rowCount())
        group.setData(True, Qt.ItemDataRole.UserRole + 2)
        rows = iter(self._output_rows.get(directory, ()))
        generation = self.generation

        def add(parent, row):
            status_item = QStandardItem(self.display_status(row.status))
            status_item.setForeground(QBrush(self.status_color(row.status)))
            status_item.setEditable(False)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_item.setData(str(row.entry.path), Qt.ItemDataRole.UserRole)
            status_item.setData(str(row.entry.path), Qt.ItemDataRole.UserRole + 1)
            item = QStandardItem(row.entry.path.name)
            item.setEditable(False)
            item.setToolTip(str(row.entry.path))
            item.setData(str(row.entry.path), Qt.ItemDataRole.UserRole)
            item.setData(str(row.entry.path), Qt.ItemDataRole.UserRole + 1)
            item.setForeground(QBrush(self.palette().color(self.palette().ColorRole.Text)))
            parent.appendRow([item, status_item])
            for child in row.children:
                if child.children:
                    add(item, child)
                else:
                    child_status = QStandardItem(self.display_status(child.status))
                    child_status.setForeground(QBrush(self.status_color(child.status)))
                    child_status.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    child_status.setData(str(child.entry.path), Qt.ItemDataRole.UserRole)
                    child_item = QStandardItem(child.entry.path.name)
                    child_item.setForeground(QBrush(self.palette().color(self.palette().ColorRole.Text)))
                    child_item.setToolTip(str(child.entry.path))
                    child_item.setData(str(child.entry.path), Qt.ItemDataRole.UserRole)
                    item.appendRow([child_item, child_status])
            if row.entry.path == self.selected:
                self.tree.setCurrentIndex(item.index())

        def batch():
            if generation != self.generation:
                return
            for _ in range(_HISTORY_BATCH):
                row = next(rows, None)
                if row is None:
                    self.tree.setColumnWidth(0, _FILE_NAME_WIDTH)
                    self.tree.setColumnWidth(1, _FILE_STATUS_WIDTH)
                    return
                add(group, row)
            QTimer.singleShot(0, self, batch)

        batch()

    def select_recent(self, current, previous=None):
        if current:
            path = current.data(Qt.ItemDataRole.UserRole)
            self.selected = Path(path)
            self.submit("detail", load_run_snapshot, self.selected)

    def update_paging(self, label):
        self.page_label.setText(label)
        multiple = len(self.log.store.offsets) > 1
        self.page_label.setVisible(multiple)
        self.previous_page.setVisible(multiple)
        self.next_page.setVisible(multiple)

    def summary_tab_changed(self, index):
        if self.tabs.widget(index) is self.summary_scroll:
            self.render_summary(self.current_summary)

    def render_summary(self, summary):
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not isinstance(summary, dict):
            self.summary_layout.addWidget(QLabel("Summary unavailable for this run."))
            return
        result = str(summary.get("overall_result") or "INCOMPLETE").upper()
        badge = QLabel(self.display_status(result))
        badge.setStyleSheet(f"color: {self.status_color(result).name()}; font-weight: 600")
        self.summary_layout.addWidget(badge)
        counts = summary.get("verification_counts") or {}
        required = counts.get("required", {}) if isinstance(counts, dict) else {}
        total = sum(v for v in required.values() if isinstance(v, int))
        failures = sum(v for k, v in required.items() if str(k).upper() in {"FAIL", "ERROR"})
        duration = summary.get("duration_seconds")
        metrics = QHBoxLayout()
        for value, label in ((str(total), "Verifications"), (str(failures), "Failures"),
                             (f"{duration:.1f}s" if isinstance(duration, (int, float)) else "Unavailable", "Duration")):
            block = QVBoxLayout()
            number = QLabel(value)
            number.setStyleSheet("font-size: 20px; font-weight: 600")
            block.addWidget(number)
            block.addWidget(QLabel(label))
            metrics.addLayout(block)
        self.summary_layout.addLayout(metrics)
        self.summary_layout.addWidget(QLabel("Run details"))
        details = QPlainTextEdit()
        details.setReadOnly(True)
        details.setPlainText(format_summary_text(summary))
        self.summary_layout.addWidget(details)

    def open_folder(self):
        if not self.selected or not self.selected.is_dir():
            self.statusBar().showMessage("Select an existing run folder.")
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.selected))):
            self.statusBar().showMessage("Could not open the output folder.")

    def closeEvent(self, event):
        if self.execution.active:
            answer = QMessageBox.question(self, "Run active", "Stop the active run and close?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Yes:
                self.closing = True
                self.execution.stop()
            event.ignore()
            return
        self.generation += 1
        self.timer.stop()
        self.log.release()
        self.pool.shutdown(wait=False, cancel_futures=True)
        event.accept()


def main():
    app = QApplication([])
    window = Inspector()
    window.show()
    return app.exec()
