from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optimaster.config import load_config
from optimaster.errors import AppError
from optimaster.models import CandidateResult, OptimizationMode, OptimizationSession, SourceAnalysis
from optimaster.service import EngineService


APP_TITLE = "OptiMaster v0"
SUPPORTED_EXTENSIONS = {".wav", ".flac"}


def format_metric(value: float, unit: str) -> str:
    return f"{value:.1f} {unit}"


@dataclass(slots=True)
class WorkerRequest:
    kind: str
    input_file: str
    output_dir: str
    mode: OptimizationMode
    config_path: str | None


class DropFrame(QFrame):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropFrame")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                path = Path(urls[0].toLocalFile())
                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            self.file_dropped.emit(str(path))
            event.acceptProposedAction()
            return
        event.ignore()


class EngineWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str, int)

    def __init__(self, request: WorkerRequest) -> None:
        super().__init__()
        self.request = request

    def run(self) -> None:
        try:
            config = load_config(self.request.config_path)
            service = EngineService(config=config)
            if self.request.kind == "analyze":
                result = service.analyze_source(
                    self.request.input_file,
                    progress_callback=self._emit_progress,
                )
            else:
                result = service.optimize(
                    input_file=self.request.input_file,
                    output_dir=self.request.output_dir,
                    mode=self.request.mode,
                    progress_callback=self._emit_progress,
                )
            self.finished.emit(result)
        except AppError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive UI safety net
            self.failed.emit(f"Unexpected error: {exc}")

    def _emit_progress(self, message: str, percent: int) -> None:
        self.progress.emit(message, percent)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1220, 860)

        self.current_analysis: SourceAnalysis | None = None
        self.current_session: OptimizationSession | None = None
        self.current_output_dir: Path | None = None
        self._thread: QThread | None = None
        self._worker: EngineWorker | None = None

        self._build_ui()
        self._apply_styles()
        self._update_actions()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        root.addWidget(self._build_header())
        root.addWidget(self._build_controls())
        root.addLayout(self._build_summary(), stretch=2)
        root.addWidget(self._build_results(), stretch=3)

        self.setCentralWidget(central)
        self._build_menu()
        self._refresh_history_panel()

    def _build_header(self) -> QGroupBox:
        box = QGroupBox("Session")
        layout = QVBoxLayout(box)

        self.drop_frame = DropFrame()
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("Drop a WAV or FLAC premaster here")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            "Analyze the source, test a few careful finishing passes, "
            "then review the top-ranked exports."
        )
        subtitle.setWordWrap(True)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(r"C:\path\to\track.wav")
        self.input_edit.textChanged.connect(self._update_actions)
        browse_button = QPushButton("Choose file")
        browse_button.clicked.connect(self._browse_input_file)
        row.addWidget(self.input_edit, stretch=1)
        row.addWidget(browse_button)

        drop_layout.addWidget(title)
        drop_layout.addWidget(subtitle)
        drop_layout.addLayout(row)
        layout.addWidget(self.drop_frame)
        self.drop_frame.file_dropped.connect(self._set_input_path)
        return box

    def _build_controls(self) -> QGroupBox:
        box = QGroupBox("Controls")
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self.output_edit = QLineEdit(str(Path.cwd() / "renders"))
        self.config_edit = QLineEdit()
        self.config_edit.setPlaceholderText("Optional YAML config")
        self.mode_combo = QComboBox()
        for mode in OptimizationMode:
            self.mode_combo.addItem(mode.value.title(), mode)
        self.mode_combo.setCurrentIndex(1)

        output_button = QPushButton("Choose output")
        output_button.clicked.connect(self._browse_output_dir)
        config_button = QPushButton("Load config")
        config_button.clicked.connect(self._browse_config_file)

        self.analyze_button = QPushButton("Analyze source")
        self.optimize_button = QPushButton("Run optimization")
        self.export_button = QPushButton("Export selected candidate")
        self.analyze_button.clicked.connect(self._run_analyze)
        self.optimize_button.clicked.connect(self._run_optimize)
        self.export_button.clicked.connect(self._export_selected_candidate)

        layout.addWidget(QLabel("Optimization mode"), 0, 0)
        layout.addWidget(self.mode_combo, 0, 1)
        layout.addWidget(QLabel("Output folder"), 1, 0)
        layout.addWidget(self.output_edit, 1, 1)
        layout.addWidget(output_button, 1, 2)
        layout.addWidget(QLabel("Config file"), 2, 0)
        layout.addWidget(self.config_edit, 2, 1)
        layout.addWidget(config_button, 2, 2)
        layout.addWidget(self.analyze_button, 3, 0)
        layout.addWidget(self.optimize_button, 3, 1)
        layout.addWidget(self.export_button, 3, 2)

        self.status_label = QLabel("Ready for analysis.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.status_label, 4, 0, 1, 2)
        layout.addWidget(self.progress_bar, 4, 2)
        return box

    def _build_summary(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)

        self.source_box = QGroupBox("Source analysis")
        source_layout = QFormLayout(self.source_box)
        self.metric_labels = {
            "profile": QLabel("Not analyzed"),
            "integrated": QLabel("--"),
            "true_peak": QLabel("--"),
            "lra": QLabel("--"),
            "diagnostics": QLabel("Run an analysis to inspect the source profile."),
        }
        self.metric_labels["diagnostics"].setWordWrap(True)
        source_layout.addRow("Profile", self.metric_labels["profile"])
        source_layout.addRow("Integrated LUFS", self.metric_labels["integrated"])
        source_layout.addRow("True Peak", self.metric_labels["true_peak"])
        source_layout.addRow("LRA", self.metric_labels["lra"])
        source_layout.addRow("Diagnostics", self.metric_labels["diagnostics"])

        self.best_box = QGroupBox("Recommended candidate")
        best_layout = QFormLayout(self.best_box)
        self.best_labels = {
            "name": QLabel("No candidate yet"),
            "score": QLabel("--"),
            "metrics": QLabel("--"),
            "reasons": QLabel("Run optimization to see the top recommendation."),
            "path": QLabel("--"),
        }
        self.best_labels["reasons"].setWordWrap(True)
        self.best_labels["path"].setWordWrap(True)
        best_layout.addRow("Preset", self.best_labels["name"])
        best_layout.addRow("Score", self.best_labels["score"])
        best_layout.addRow("Metrics", self.best_labels["metrics"])
        best_layout.addRow("Why it ranked first", self.best_labels["reasons"])
        best_layout.addRow("Rendered file", self.best_labels["path"])

        self.history_box = QGroupBox("Recent sessions")
        history_layout = QVBoxLayout(self.history_box)
        self.history_panel = QPlainTextEdit()
        self.history_panel.setReadOnly(True)
        self.history_panel.setPlaceholderText("Run a first optimization to build local history.")
        refresh_history_button = QPushButton("Refresh history")
        refresh_history_button.clicked.connect(self._refresh_history_panel)
        history_layout.addWidget(self.history_panel, stretch=1)
        history_layout.addWidget(refresh_history_button)

        layout.addWidget(self.source_box, stretch=1)
        layout.addWidget(self.best_box, stretch=1)
        layout.addWidget(self.history_box, stretch=1)
        return layout

    def _build_results(self) -> QGroupBox:
        box = QGroupBox("Top candidates")
        layout = QVBoxLayout(box)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Preset", "Score", "LUFS", "TP", "LRA"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self._update_selected_candidate_details)

        self.details_panel = QPlainTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlaceholderText("Candidate details and scoring reasons appear here.")
        self.details_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(self.results_table, stretch=2)
        layout.addWidget(self.details_panel, stretch=1)
        return box

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        choose_input_action = QAction("Choose audio file", self)
        choose_input_action.triggered.connect(self._browse_input_file)
        file_menu.addAction(choose_input_action)

        choose_output_action = QAction("Choose output folder", self)
        choose_output_action.triggered.connect(self._browse_output_dir)
        file_menu.addAction(choose_output_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #12161c;
                color: #eef4f7;
                font-size: 13px;
            }
            QMainWindow, QMenuBar, QMenu, QGroupBox, QPlainTextEdit, QTableWidget, QLineEdit, QComboBox, QProgressBar {
                background: #12161c;
            }
            QGroupBox {
                border: 1px solid #2b353f;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 14px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #7fd7c4;
            }
            #dropFrame {
                border: 2px dashed #3f5566;
                border-radius: 14px;
                background: #18212a;
            }
            #heroTitle {
                font-size: 21px;
                font-weight: 700;
                color: #f8fafb;
            }
            QPushButton {
                background: #1f8f7b;
                border: 0;
                border-radius: 8px;
                padding: 10px 14px;
                color: #061615;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #28a48f;
            }
            QPushButton:disabled {
                background: #3c4b56;
                color: #91a0ab;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget {
                border: 1px solid #31404b;
                border-radius: 8px;
                padding: 8px;
                background: #18212a;
                selection-background-color: #1f8f7b;
            }
            QHeaderView::section {
                background: #1d2831;
                color: #eef4f7;
                border: 0;
                padding: 8px;
            }
            QProgressBar {
                border: 1px solid #31404b;
                border-radius: 7px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #e5b94d;
                border-radius: 7px;
            }
            """
        )

    def _browse_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select source file",
            str(Path.home()),
            "Audio files (*.wav *.flac)",
        )
        if file_path:
            self._set_input_path(file_path)

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            self.output_edit.text() or str(Path.cwd()),
        )
        if folder:
            self.output_edit.setText(folder)

    def _browse_config_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select config file",
            str(Path.cwd()),
            "YAML files (*.yaml *.yml)",
        )
        if file_path:
            self.config_edit.setText(file_path)

    def _set_input_path(self, path: str) -> None:
        self.input_edit.setText(path)
        default_dir = Path(path).resolve().parent / "renders"
        self.output_edit.setText(str(default_dir))
        self.status_label.setText("Source file selected. Ready to analyze.")
        self.progress_bar.setValue(0)
        self._update_actions()

    def _run_analyze(self) -> None:
        request = self._build_request(kind="analyze")
        if request is not None:
            self._start_worker(request)

    def _run_optimize(self) -> None:
        request = self._build_request(kind="optimize")
        if request is not None:
            self._start_worker(request)

    def _build_request(self, kind: str) -> WorkerRequest | None:
        input_file = self.input_edit.text().strip()
        if not input_file:
            self._show_error("Choose a WAV or FLAC file first.")
            return None

        output_dir = self.output_edit.text().strip() or str(Path(input_file).resolve().parent / "renders")
        config_path = self.config_edit.text().strip() or None
        mode = self.mode_combo.currentData()
        return WorkerRequest(
            kind=kind,
            input_file=input_file,
            output_dir=output_dir,
            mode=mode,
            config_path=config_path,
        )

    def _start_worker(self, request: WorkerRequest) -> None:
        if self._thread is not None:
            return

        self.current_output_dir = Path(request.output_dir)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparing background task...")
        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = EngineWorker(request)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.failed.connect(self._cleanup_worker)
        self._thread.start()

    def _cleanup_worker(self) -> None:
        if self._thread is None or self._worker is None:
            return
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._set_busy(False)
        self._update_actions()

    def _on_progress(self, message: str, percent: int) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_worker_finished(self, result: object) -> None:
        if isinstance(result, SourceAnalysis):
            self.current_analysis = result
            self.current_session = None
            self._populate_analysis(result)
            self._clear_results()
            self.status_label.setText("Analysis complete.")
            self.progress_bar.setValue(100)
            return

        if isinstance(result, OptimizationSession):
            self.current_analysis = result.analysis
            self.current_session = result
            self._populate_analysis(result.analysis)
            self._populate_session(result)
            self._refresh_history_panel()
            self.status_label.setText(
                f"Optimization complete. Session {result.session_id} is ready for review."
            )
            self.progress_bar.setValue(100)

    def _on_worker_failed(self, message: str) -> None:
        self.status_label.setText("Task failed.")
        self.progress_bar.setValue(0)
        self._show_error(message)

    def _populate_analysis(self, analysis: SourceAnalysis) -> None:
        metrics = analysis.metrics
        self.metric_labels["profile"].setText(analysis.profile.value.replace("_", " ").title())
        self.metric_labels["integrated"].setText(format_metric(metrics.integrated_lufs, "LUFS"))
        self.metric_labels["true_peak"].setText(format_metric(metrics.true_peak_dbtp, "dBTP"))
        self.metric_labels["lra"].setText(format_metric(metrics.lra_lu, "LU"))
        self.metric_labels["diagnostics"].setText(" | ".join(analysis.diagnostics))

    def _populate_session(self, session: OptimizationSession) -> None:
        self.results_table.setRowCount(len(session.candidates))
        for row, candidate in enumerate(session.candidates):
            values = [
                candidate.preset.name,
                f"{candidate.score:.1f}",
                f"{candidate.output_metrics.integrated_lufs:.1f}",
                f"{candidate.output_metrics.true_peak_dbtp:.1f}",
                f"{candidate.output_metrics.lra_lu:.1f}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, candidate)
                self.results_table.setItem(row, col, item)
        self.results_table.resizeColumnsToContents()
        if session.candidates:
            self.results_table.selectRow(0)
            self._populate_best_candidate(session.best_candidate)
        else:
            self._populate_best_candidate(None)

    def _populate_best_candidate(self, candidate: CandidateResult | None) -> None:
        if candidate is None:
            self.best_labels["name"].setText("No candidate")
            self.best_labels["score"].setText("--")
            self.best_labels["metrics"].setText("--")
            self.best_labels["reasons"].setText("No candidate available.")
            self.best_labels["path"].setText("--")
            return

        metrics = candidate.output_metrics
        self.best_labels["name"].setText(candidate.preset.name)
        self.best_labels["score"].setText(f"{candidate.score:.1f}")
        self.best_labels["metrics"].setText(
            ", ".join(
                [
                    format_metric(metrics.integrated_lufs, "LUFS"),
                    format_metric(metrics.true_peak_dbtp, "dBTP"),
                    format_metric(metrics.lra_lu, "LU"),
                ]
            )
        )
        self.best_labels["reasons"].setText(" | ".join(candidate.reasons))
        self.best_labels["path"].setText(str(candidate.output_path))

    def _update_selected_candidate_details(self) -> None:
        selected = self._selected_candidate()
        if selected is None:
            self.details_panel.clear()
            self._update_actions()
            return
        lines = [
            f"Preset: {selected.preset.name}",
            f"Description: {selected.preset.description}",
            f"Output: {selected.output_path}",
            f"Score: {selected.score:.1f}",
            (
                "Output metrics: "
                f"LUFS {selected.output_metrics.integrated_lufs:.1f}, "
                f"TP {selected.output_metrics.true_peak_dbtp:.1f}, "
                f"LRA {selected.output_metrics.lra_lu:.1f}"
            ),
            "",
            "Reasons:",
        ]
        lines.extend(f"- {reason}" for reason in selected.reasons)
        self.details_panel.setPlainText("\n".join(lines))
        if self.current_session and self.current_session.best_candidate is selected:
            self._populate_best_candidate(selected)
        self._update_actions()

    def _selected_candidate(self) -> CandidateResult | None:
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return None
        item = self.results_table.item(selected_ranges[0].topRow(), 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _export_selected_candidate(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self._show_error("Select a rendered candidate before exporting.")
            return

        initial_name = candidate.output_path.name
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export selected candidate",
            str((self.current_output_dir or candidate.output_path.parent) / initial_name),
            "WAV files (*.wav);;FLAC files (*.flac);;All files (*.*)",
        )
        if not destination:
            return

        shutil.copy2(candidate.output_path, destination)
        QMessageBox.information(
            self,
            "Export complete",
            f"Copied {candidate.preset.name} to:\n{destination}",
        )

    def _clear_results(self) -> None:
        self.results_table.setRowCount(0)
        self.details_panel.clear()
        self._populate_best_candidate(None)
        self._update_actions()

    def _refresh_history_panel(self) -> None:
        history_rows = EngineService.load_recent_history(limit=8)
        if not history_rows:
            self.history_panel.setPlainText("No local history yet.")
            return
        lines: list[str] = []
        for item in reversed(history_rows):
            created_at = str(item.get("created_at", "unknown date"))
            session_id = str(item.get("session_id", "n/a"))
            mode = str(item.get("mode", "n/a"))
            source_name = Path(str(item.get("source_path", "unknown"))).name
            best_candidate = str(item.get("best_candidate", "n/a"))
            best_score = item.get("best_score", "n/a")
            lines.append(
                f"{created_at} | {session_id} | {source_name} | mode={mode} | best={best_candidate} ({best_score})"
            )
        self.history_panel.setPlainText("\n".join(lines))

    def _set_busy(self, busy: bool) -> None:
        self.analyze_button.setDisabled(busy)
        self.optimize_button.setDisabled(busy)
        self.export_button.setDisabled(busy or self._selected_candidate() is None)
        self.mode_combo.setDisabled(busy)
        self.input_edit.setDisabled(busy)
        self.output_edit.setDisabled(busy)
        self.config_edit.setDisabled(busy)

    def _update_actions(self) -> None:
        has_input = bool(self.input_edit.text().strip())
        self.analyze_button.setEnabled(has_input and self._thread is None)
        self.optimize_button.setEnabled(has_input and self._thread is None)
        self.export_button.setEnabled(self._thread is None and self._selected_candidate() is not None)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "OptiMaster", message)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
