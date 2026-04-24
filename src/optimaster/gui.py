from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
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
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optimaster.config import load_config
from optimaster.errors import AppError
from optimaster.ffmpeg import render_waveform_preview
from optimaster.history import SessionHistoryStore
from optimaster.models import CandidateResult, OptimizationMode, OptimizationSession, SourceAnalysis
from optimaster.service import EngineService


APP_TITLE = "OptiMaster v0"
SUPPORTED_EXTENSIONS = {".wav", ".flac"}
PRESET_DISPLAY_NAMES = {
    "do_almost_nothing": "Minimal touch",
    "transparent_trim": "Transparent trim",
    "safe_limit": "Safe limiter",
    "sweet_spot": "Balanced finish",
    "gentle_glue": "Gentle glue",
}


def format_metric(value: float, unit: str) -> str:
    return f"{value:.1f} {unit}"


@dataclass(slots=True)
class WorkerRequest:
    kind: str
    input_file: str
    output_dir: str
    mode: OptimizationMode
    config_path: str | None
    destination_profile: str
    strict_true_peak: bool
    source_analysis: SourceAnalysis | None = None


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
                    source_analysis=self.request.source_analysis,
                    destination_profile=self.request.destination_profile,
                    strict_true_peak=self.request.strict_true_peak,
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
        self.waveform_preview_path: Path | None = None
        self.destination_profiles = {
            "Streaming prudent": "streaming_prudent",
            "Club / Loud": "club_loud",
            "Archive safe": "archive_safe",
        }
        self._thread: QThread | None = None
        self._worker: EngineWorker | None = None
        self.history_store = SessionHistoryStore()
        self.audio_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_player.setAudioOutput(self.audio_output)
        self.current_playback: str | None = None

        self._build_ui()
        self._apply_styles()
        self._load_history()
        self._update_actions()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setObjectName("workflowTabs")

        source_step = QWidget()
        source_layout = QVBoxLayout(source_step)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(14)
        source_layout.addWidget(self._build_header())
        source_layout.addWidget(self._build_controls())
        source_layout.addWidget(self._build_source_analysis(), stretch=1)

        candidate_step = QWidget()
        candidate_layout = QVBoxLayout(candidate_step)
        candidate_layout.setContentsMargins(0, 0, 0, 0)
        candidate_layout.setSpacing(14)
        candidate_layout.addWidget(self._build_best_candidate())
        candidate_layout.addWidget(self._build_results(), stretch=1)

        listening_step = QWidget()
        listening_layout = QVBoxLayout(listening_step)
        listening_layout.setContentsMargins(0, 0, 0, 0)
        listening_layout.setSpacing(14)
        listening_layout.addWidget(self._build_listening_tools(), stretch=1)

        self.workflow_tabs.addTab(source_step, "1. Source")
        self.workflow_tabs.addTab(candidate_step, "2. Candidate")
        self.workflow_tabs.addTab(listening_step, "3. Listen / Export")
        root.addWidget(self.workflow_tabs, stretch=1)

        self.setCentralWidget(central)
        self._build_menu()

    def _build_header(self) -> QGroupBox:
        box = QGroupBox("Session")
        layout = QVBoxLayout(box)

        self.drop_frame = DropFrame()
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("1. Choose a WAV or FLAC premaster")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            "Classic path: choose a file, analyze it, then render candidates."
        )
        subtitle.setWordWrap(True)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(r"C:\path\to\track.wav")
        self.input_edit.textChanged.connect(self._update_actions)
        browse_button = QPushButton("1. Choose file")
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
        box = QGroupBox("2-3. Analysis and rendering")
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
        self.destination_combo = QComboBox()
        for label, value in self.destination_profiles.items():
            self.destination_combo.addItem(label, value)
        self.strict_tp_checkbox = QCheckBox("True peak strict (safer after encoding)")
        self.strict_tp_checkbox.setChecked(True)

        output_button = QPushButton("Choose output")
        output_button.clicked.connect(self._browse_output_dir)
        config_button = QPushButton("Load config")
        config_button.clicked.connect(self._browse_config_file)

        self.analyze_button = QPushButton("2. Analyze source")
        self.optimize_button = QPushButton("3. Render candidates")
        self.export_button = QPushButton("6. Export selected candidate")
        self.analyze_button.clicked.connect(self._run_analyze)
        self.optimize_button.clicked.connect(self._run_optimize)
        self.export_button.clicked.connect(self._export_selected_candidate)

        layout.addWidget(QLabel("Optimization mode"), 0, 0)
        layout.addWidget(self.mode_combo, 0, 1)
        layout.addWidget(QLabel("Destination profile"), 1, 0)
        layout.addWidget(self.destination_combo, 1, 1)
        layout.addWidget(self.strict_tp_checkbox, 1, 2)
        layout.addWidget(QLabel("Output folder"), 2, 0)
        layout.addWidget(self.output_edit, 2, 1)
        layout.addWidget(output_button, 2, 2)
        layout.addWidget(QLabel("Config file"), 3, 0)
        layout.addWidget(self.config_edit, 3, 1)
        layout.addWidget(config_button, 3, 2)
        layout.addWidget(self.analyze_button, 4, 0)
        layout.addWidget(self.optimize_button, 4, 1, 1, 2)

        self.status_label = QLabel("Step 1: choose a source file to begin.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.status_label, 5, 0, 1, 2)
        layout.addWidget(self.progress_bar, 5, 2)
        return box

    def _build_source_analysis(self) -> QGroupBox:
        self.source_box = QGroupBox("2. Source analysis")
        source_layout = QFormLayout(self.source_box)
        self.metric_labels = {
            "profile": QLabel("Not analyzed"),
            "integrated": QLabel("--"),
            "true_peak": QLabel("--"),
            "lra": QLabel("--"),
            "diagnostics": QLabel("Step 2 appears here after analysis."),
            "acoustic_note": QLabel(
                "Meters are technical indicators. Final validation depends on monitoring level and room acoustics."
            ),
        }
        self.metric_labels["diagnostics"].setWordWrap(True)
        self.metric_labels["acoustic_note"].setWordWrap(True)
        source_layout.addRow("Profile", self.metric_labels["profile"])
        source_layout.addRow("Integrated LUFS", self.metric_labels["integrated"])
        source_layout.addRow("True Peak", self.metric_labels["true_peak"])
        source_layout.addRow("LRA", self.metric_labels["lra"])
        source_layout.addRow("Diagnostics", self.metric_labels["diagnostics"])
        source_layout.addRow("Engineering note", self.metric_labels["acoustic_note"])
        self.waveform_label = QLabel("Waveform preview appears after file selection.")
        self.waveform_label.setMinimumHeight(130)
        self.waveform_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.waveform_label.setObjectName("waveformPreview")
        source_layout.addRow("Waveform", self.waveform_label)
        return self.source_box

    def _build_best_candidate(self) -> QGroupBox:
        self.best_box = QGroupBox("4. Recommended choice")
        best_layout = QFormLayout(self.best_box)
        self.best_labels = {
            "name": QLabel("No candidate yet"),
            "score": QLabel("--"),
            "metrics": QLabel("--"),
            "reasons": QLabel("Step 4: select a candidate after rendering."),
            "path": QLabel("--"),
        }
        self.best_labels["reasons"].setWordWrap(True)
        self.best_labels["path"].setWordWrap(True)
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 5)
        self.rating_spin.setValue(3)
        self.listen_selected_button = QPushButton("5. Listen to selected version")
        self.listen_selected_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self.save_note_button = QPushButton("5C. Save listening note")
        self.save_note_button.clicked.connect(self._save_listening_note)
        best_layout.addRow("Chosen version", self.best_labels["name"])
        best_layout.addRow("Score", self.best_labels["score"])
        best_layout.addRow("Metrics", self.best_labels["metrics"])
        best_layout.addRow("Why choose it", self.best_labels["reasons"])
        best_layout.addRow("Rendered file", self.best_labels["path"])
        best_layout.addRow("Next", self.listen_selected_button)
        best_layout.addRow("Rating (1-5)", self.rating_spin)
        best_layout.addRow("Preferences", self.save_note_button)
        return self.best_box

    def _build_listening_tools(self) -> QGroupBox:
        box = QGroupBox("5-6. A/B listening and export")
        layout = QVBoxLayout(box)

        listening_row = QHBoxLayout()
        self.play_source_button = QPushButton("5A. Play source (A)")
        self.play_candidate_button = QPushButton("5B. Play selected candidate (B)")
        self.stop_audio_button = QPushButton("Stop")
        self.play_source_button.clicked.connect(self._play_source)
        self.play_candidate_button.clicked.connect(self._play_selected_candidate)
        self.stop_audio_button.clicked.connect(self._stop_playback)
        listening_row.addWidget(self.play_source_button)
        listening_row.addWidget(self.play_candidate_button)
        listening_row.addWidget(self.stop_audio_button)
        listening_row.addWidget(self.export_button)

        self.playback_label = QLabel("Step 5: select a candidate, then compare A and B.")
        self.playback_label.setWordWrap(True)

        self.before_after_table = QTableWidget(4, 4)
        self.before_after_table.setHorizontalHeaderLabels(["Metric", "Before", "After", "Change"])
        self.before_after_table.setVerticalHeaderLabels([])
        self.before_after_table.setAlternatingRowColors(True)
        self.before_after_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.before_after_table.verticalHeader().setVisible(False)
        self.before_after_table.horizontalHeader().setStretchLastSection(True)
        self.before_after_table.setMaximumHeight(180)
        self._clear_before_after()

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Date (UTC)", "Session", "Mode", "Best", "Source"])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setMaximumHeight(170)

        layout.addLayout(listening_row)
        layout.addWidget(self.playback_label)
        layout.addWidget(self.before_after_table)
        layout.addWidget(self.history_table)
        return box

    def _build_results(self) -> QGroupBox:
        box = QGroupBox("4. Choose a version")
        layout = QVBoxLayout(box)

        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(["Choice", "Version", "Score", "LUFS", "TP", "LRA"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self._update_selected_candidate_details)

        self.details_panel = QPlainTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlaceholderText(
            "Step 4: select the recommended version, or an alternative if you want to compare."
        )
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
            QTabWidget::pane {
                border: 0;
                padding-top: 8px;
            }
            QTabBar::tab {
                background: #18212a;
                color: #91a0ab;
                border: 1px solid #2b353f;
                border-bottom: 0;
                padding: 10px 18px;
                min-width: 150px;
            }
            QTabBar::tab:selected {
                background: #1f8f7b;
                color: #061615;
                font-weight: 700;
            }
            QTabBar::tab:disabled {
                color: #53616b;
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
            #waveformPreview {
                border: 1px solid #31404b;
                border-radius: 8px;
                background: #18212a;
                color: #91a0ab;
                padding: 6px;
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
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QSpinBox {
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
        path_obj = Path(path).resolve()
        previous_path = Path(self.input_edit.text()).resolve() if self.input_edit.text().strip() else None
        self.input_edit.setText(path)
        default_dir = path_obj.parent / "renders"
        self.output_edit.setText(str(default_dir))
        if previous_path != path_obj:
            self.current_analysis = None
            self.current_session = None
            self._clear_results()
        self.status_label.setText("Step 1 complete. Step 2: analyze the source.")
        self._update_waveform_preview(path_obj)
        self.progress_bar.setValue(0)
        self.workflow_tabs.setCurrentIndex(0)
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
        mode_data = self.mode_combo.currentData()
        mode = mode_data if isinstance(mode_data, OptimizationMode) else OptimizationMode(str(mode_data))
        source_analysis = self._analysis_for_request(kind, input_file)
        return WorkerRequest(
            kind=kind,
            input_file=input_file,
            output_dir=output_dir,
            mode=mode,
            config_path=config_path,
            destination_profile=self.destination_combo.currentData(),
            strict_true_peak=self.strict_tp_checkbox.isChecked(),
            source_analysis=source_analysis,
        )

    def _analysis_for_request(self, kind: str, input_file: str) -> SourceAnalysis | None:
        if kind != "optimize" or self.current_analysis is None:
            return None
        if self.current_analysis.source_path == Path(input_file).resolve():
            return self.current_analysis
        return None

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
            self._update_waveform_preview(result.source_path)
            self._clear_results()
            self.status_label.setText("Step 2 complete. Step 3: render candidates.")
            self.progress_bar.setValue(100)
            self.workflow_tabs.setCurrentIndex(0)
            return

        if isinstance(result, OptimizationSession):
            self.current_analysis = result.analysis
            self.current_session = result
            self._populate_analysis(result.analysis)
            self._populate_session(result)
            if self.current_output_dir is not None:
                self.history_store.append(result, self.current_output_dir)
            self._load_history()
            self.status_label.setText(
                "Step 3 complete. Step 4: select a candidate."
            )
            self.progress_bar.setValue(100)
            self.workflow_tabs.setCurrentIndex(1)

    def _on_worker_failed(self, message: str) -> None:
        self.status_label.setText("Task failed. Check the error dialog for details.")
        self.progress_bar.setValue(0)
        self._show_error(message)

    def _populate_analysis(self, analysis: SourceAnalysis) -> None:
        metrics = analysis.metrics
        self.metric_labels["profile"].setText(analysis.profile.value.replace("_", " ").title())
        self.metric_labels["integrated"].setText(format_metric(metrics.integrated_lufs, "LUFS"))
        self.metric_labels["true_peak"].setText(format_metric(metrics.true_peak_dbtp, "dBTP"))
        self.metric_labels["lra"].setText(format_metric(metrics.lra_lu, "LU"))
        diagnostics = list(analysis.diagnostics)
        if analysis.profile.value in {"very_hot", "almost_ready"}:
            diagnostics.append("Source already hot: prioritize transparent and minimal moves.")
        self.metric_labels["diagnostics"].setText(" | ".join(diagnostics))

    def _populate_session(self, session: OptimizationSession) -> None:
        self.results_table.setRowCount(len(session.candidates))
        for row, candidate in enumerate(session.candidates):
            values = [
                "Recommended" if row == 0 else "Alternative",
                self._candidate_version_label(candidate),
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
            self.best_labels["reasons"].setText("Step 3 first: render candidates, then select one from the table.")
            self.best_labels["path"].setText("--")
            return

        metrics = candidate.output_metrics
        self.best_labels["name"].setText(f"{self._candidate_version_label(candidate)} (recommended)")
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
        top_reasons = candidate.reasons[:3]
        if len(candidate.reasons) > 3:
            top_reasons.append("Further details available in candidate panel.")
        self.best_labels["reasons"].setText(" | ".join(top_reasons))
        self.best_labels["path"].setText(str(candidate.output_path))

    def _update_selected_candidate_details(self) -> None:
        selected = self._selected_candidate()
        if selected is None:
            self.details_panel.clear()
            self._clear_before_after()
            self._update_actions()
            return
        lines = [
            f"Selected: {self._candidate_version_label(selected)}",
            f"Role: {self._candidate_choice_label(selected)}",
            f"Use it when: {selected.preset.description}",
            f"Output: {selected.output_path}",
            f"Score: {selected.score:.1f}",
            (
                "Output metrics: "
                f"LUFS {selected.output_metrics.integrated_lufs:.1f}, "
                f"TP {selected.output_metrics.true_peak_dbtp:.1f}, "
                f"LRA {selected.output_metrics.lra_lu:.1f}"
            ),
            (
                "Delta vs source: "
                f"LUFS {selected.output_metrics.integrated_lufs - selected.source_metrics.integrated_lufs:+.1f}, "
                f"LRA {selected.output_metrics.lra_lu - selected.source_metrics.lra_lu:+.1f}"
            ),
            "",
            "Why choose it:",
        ]
        lines.extend(f"- {reason}" for reason in selected.reasons)
        lines.extend(
            [
                "",
                "Listening checklist:",
                "- Compare at matched loudness when possible.",
                "- Check transients (kick/snare attack) for pumping or flattening.",
                "- Check vocal harshness/sibilance after limiting.",
                "- Validate low-end translation on a second system or headphones.",
            ]
        )
        self.details_panel.setPlainText("\n".join(lines))
        self._populate_before_after(selected)
        self.status_label.setText("Step 4 complete. Step 5: listen A/B, then step 6: export.")
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

    def _candidate_choice_label(self, candidate: CandidateResult) -> str:
        if self.current_session and self.current_session.candidates:
            if self.current_session.candidates[0] is candidate:
                return "Recommended by OptiMaster"
        return "Alternative version"

    def _candidate_version_label(self, candidate: CandidateResult) -> str:
        rank = self._candidate_rank(candidate)
        name = PRESET_DISPLAY_NAMES.get(candidate.preset.name, candidate.preset.name.replace("_", " ").title())
        if rank is None:
            return name
        return f"Version {rank}: {name}"

    def _candidate_rank(self, candidate: CandidateResult) -> int | None:
        if self.current_session is None:
            return None
        for idx, session_candidate in enumerate(self.current_session.candidates, start=1):
            if session_candidate is candidate:
                return idx
        return None

    def _clear_before_after(self) -> None:
        rows = [
            ("Integrated loudness", "--", "--", "--"),
            ("True peak", "--", "--", "--"),
            ("Dynamic range (LRA)", "--", "--", "--"),
            ("Score", "--", "--", "--"),
        ]
        self._set_before_after_rows(rows)

    def _populate_before_after(self, candidate: CandidateResult) -> None:
        source = candidate.source_metrics
        output = candidate.output_metrics
        rows = [
            (
                "Integrated loudness",
                format_metric(source.integrated_lufs, "LUFS"),
                format_metric(output.integrated_lufs, "LUFS"),
                f"{output.integrated_lufs - source.integrated_lufs:+.1f} LUFS",
            ),
            (
                "True peak",
                format_metric(source.true_peak_dbtp, "dBTP"),
                format_metric(output.true_peak_dbtp, "dBTP"),
                f"{output.true_peak_dbtp - source.true_peak_dbtp:+.1f} dB",
            ),
            (
                "Dynamic range (LRA)",
                format_metric(source.lra_lu, "LU"),
                format_metric(output.lra_lu, "LU"),
                f"{output.lra_lu - source.lra_lu:+.1f} LU",
            ),
            ("Score", "--", f"{candidate.score:.1f}", "Ranked by safety, loudness, and dynamics"),
        ]
        self._set_before_after_rows(rows)

    def _set_before_after_rows(self, rows: list[tuple[str, str, str, str]]) -> None:
        self.before_after_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.before_after_table.setItem(row, col, item)
        self.before_after_table.resizeColumnsToContents()

    def _export_selected_candidate(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self._show_error("Select a rendered candidate before exporting.")
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export final version",
            str(self._default_export_path(candidate)),
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

    def _default_export_path(self, candidate: CandidateResult) -> Path:
        source_stem = candidate.output_path.stem.removesuffix(f"_{candidate.preset.name}")
        export_dir = candidate.output_path.parent.parent
        suffix = candidate.output_path.suffix or ".wav"
        index = 1
        while True:
            destination = export_dir / f"{source_stem}_export_{index:02d}{suffix}"
            if not destination.exists():
                return destination
            index += 1

    def _save_listening_note(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self._show_error("Select a candidate to save a listening note.")
            return
        config = load_config(self.config_edit.text().strip() or None)
        preferences_path = (self.current_output_dir or Path.cwd() / "renders") / "preferences.json"
        service = EngineService(config=config, preference_path=preferences_path)
        service.add_listening_note(candidate.preset.name, self.rating_spin.value())
        self.status_label.setText(f"Saved note for {candidate.preset.name} in {preferences_path}")

    def _update_waveform_preview(self, source_path: Path) -> None:
        try:
            preview_dir = Path(self.output_edit.text().strip() or source_path.parent / "renders")
            preview_path = preview_dir / f"{source_path.stem}_waveform.png"
            config = load_config(self.config_edit.text().strip() or None)
            created = render_waveform_preview(
                input_path=source_path,
                output_path=preview_path,
                ffmpeg_binary=config.ffmpeg_binary,
            )
            self.waveform_preview_path = created
            pixmap = QPixmap(str(created))
            self.waveform_label.setPixmap(
                pixmap.scaled(
                    max(self.waveform_label.width(), 260),
                    130,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.waveform_label.setText("")
        except Exception:
            self.waveform_preview_path = None
            self.waveform_label.setPixmap(QPixmap())
            self.waveform_label.setText("Waveform preview unavailable for this file.")

    def _clear_results(self) -> None:
        self.results_table.setRowCount(0)
        self.details_panel.clear()
        self._clear_before_after()
        self._populate_best_candidate(None)
        self._update_actions()

    def _load_history(self) -> None:
        entries = self.history_store.read_all()
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                entry.created_at.replace("T", " ")[:19],
                entry.session_id,
                entry.mode.title(),
                (
                    f"{entry.best_preset} ({entry.best_score:.1f})"
                    if entry.best_preset is not None and entry.best_score is not None
                    else "n/a"
                ),
                Path(entry.source_path).name,
            ]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(value))
        self.history_table.resizeColumnsToContents()

    def _play_source(self) -> None:
        input_path = self.input_edit.text().strip()
        if not input_path:
            self._show_error("Choose a source file before playback.")
            return
        self._start_playback(Path(input_path), "A (source)")

    def _play_selected_candidate(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self.workflow_tabs.setCurrentIndex(1)
            self.status_label.setText("Step 4 needed: select a candidate before listening to B.")
            return
        self._start_playback(candidate.output_path, f"B ({candidate.preset.name})")

    def _start_playback(self, path: Path, label: str) -> None:
        if not path.exists():
            self._show_error(f"Cannot play missing file: {path}")
            return
        self.audio_player.setSource(QUrl.fromLocalFile(str(path)))
        self.audio_player.play()
        self.current_playback = str(path)
        self.playback_label.setText(f"Now playing {label}: {path.name}")

    def _stop_playback(self) -> None:
        self.audio_player.stop()
        self.current_playback = None
        self.playback_label.setText("Playback stopped.")

    def _set_busy(self, busy: bool) -> None:
        self.analyze_button.setDisabled(busy)
        self.optimize_button.setDisabled(busy)
        self.export_button.setDisabled(busy or self._selected_candidate() is None)
        self.play_source_button.setDisabled(busy)
        self.play_candidate_button.setDisabled(busy or self._selected_candidate() is None)
        self.listen_selected_button.setDisabled(busy or self._selected_candidate() is None)
        self.save_note_button.setDisabled(busy or self._selected_candidate() is None)
        self.mode_combo.setDisabled(busy)
        self.destination_combo.setDisabled(busy)
        self.strict_tp_checkbox.setDisabled(busy)
        self.input_edit.setDisabled(busy)
        self.output_edit.setDisabled(busy)
        self.config_edit.setDisabled(busy)

    def _update_actions(self) -> None:
        has_input = bool(self.input_edit.text().strip())
        input_path = Path(self.input_edit.text()).resolve() if has_input else None
        has_analysis = (
            self.current_analysis is not None
            and input_path is not None
            and self.current_analysis.source_path == input_path
        )
        has_candidates = bool(self.current_session and self.current_session.candidates)
        has_candidate = self._selected_candidate() is not None
        self.analyze_button.setEnabled(has_input and self._thread is None)
        self.optimize_button.setEnabled(has_analysis and self._thread is None)
        self.export_button.setEnabled(self._thread is None and has_candidate)
        self.play_candidate_button.setEnabled(self._thread is None and has_candidate)
        self.listen_selected_button.setEnabled(self._thread is None and has_candidate)
        self.save_note_button.setEnabled(self._thread is None and has_candidate)
        self.workflow_tabs.setTabEnabled(0, True)
        self.workflow_tabs.setTabEnabled(1, has_candidates)
        self.workflow_tabs.setTabEnabled(2, has_candidate)

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
