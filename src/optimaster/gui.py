from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QAbstractSpinBox,
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
    QDoubleSpinBox,
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
from optimaster.models import CandidateResult, OptimizationMode, OptimizationSession, SourceAnalysis, SourceProfile
from optimaster.service import EngineService


APP_TITLE = "OptiMaster"
APP_VERSION = "2026.4.24"
APP_ICON = "optimaster_icon.ico"
APP_ICON_FALLBACK = "optimaster_icon.svg"
SUPPORTED_EXTENSIONS = {".wav", ".flac"}
PRESET_DISPLAY_NAMES = {
    "do_almost_nothing": "Light polish",
    "transparent_trim": "Clean headroom",
    "safe_limit": "Controlled loudness",
    "sweet_spot": "Balanced master",
    "gentle_glue": "Glue and punch",
}
PRESET_DISPLAY_DESCRIPTIONS = {
    "do_almost_nothing": "Small cleanup for tracks that are already close.",
    "transparent_trim": "Keeps the sound close to the source and makes room for playback safety.",
    "safe_limit": "Pushes level while keeping peaks under control.",
    "sweet_spot": "Balances loudness, clarity, and dynamics.",
    "gentle_glue": "Adds gentle compression for a more finished, connected feel.",
}
CONFIG_TEMPLATE = """# OptiMaster config template
# Save this file, edit only what you need, then load it in the app.
#
# Common goals:
# - Keep it simple: leave this file as-is and use the app quick targets.
# - Louder master: use the app "Max loudness, keep quality" option first.
# - Advanced users: tune scoring values below.

# FFmpeg executable. Use "ffmpeg" if it is available on PATH.
ffmpeg_binary: ffmpeg

# Export format for rendered candidates: wav or flac.
output_format: wav

# Default CLI mode: safe, balanced, or louder.
# The GUI mode selector can still override this.
default_mode: balanced

scoring:
  # Preferred loudness window when no explicit GUI target is selected.
  # Higher numbers closer to 0 sound louder, but can reduce dynamics.
  target_lufs_min: -11.0
  target_lufs_max: -9.0

  # True Peak safety. -1.0 dBTP is a common safe streaming target.
  ideal_true_peak_max: -1.0
  hard_true_peak_max: -0.5

  # Dynamic range guardrails. Lower values allow more aggressive loudness.
  min_lra: 5.0
  preferred_lra_min: 6.0

  # Maximum LUFS increase from the source before the score becomes cautious.
  max_lufs_delta_from_source: 2.0

presets:
  # Internal preset IDs. Keep these unless you know what you are disabling.
  enabled:
    - do_almost_nothing
    - transparent_trim
    - safe_limit
    - sweet_spot
    - gentle_glue
"""
SOURCE_PROFILE_DISPLAY_NAMES = {
    SourceProfile.VERY_HOT: "Already loud",
    SourceProfile.ALMOST_READY: "Almost ready",
    SourceProfile.NEEDS_FINISH: "Needs finishing",
    SourceProfile.LOW_DYNAMICS: "Low dynamics",
    SourceProfile.DYNAMIC_OK: "Healthy dynamics",
    SourceProfile.TOUCH_MINIMALLY: "Needs a light touch",
}


def format_metric(value: float, unit: str) -> str:
    return f"{value:.1f} {unit}"


def app_icon() -> QIcon:
    icon_path = resources.files("optimaster.assets").joinpath(APP_ICON)
    if not icon_path.is_file():
        icon_path = resources.files("optimaster.assets").joinpath(APP_ICON_FALLBACK)
    return QIcon(str(icon_path))


@dataclass(slots=True)
class WorkerRequest:
    kind: str
    input_file: str
    output_dir: str
    mode: OptimizationMode
    config_path: str | None
    destination_profile: str
    strict_true_peak: bool
    target_lufs: float | None
    maximize_loudness: bool
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
                    target_lufs=self.request.target_lufs,
                    maximize_loudness=self.request.maximize_loudness,
                    progress_callback=self._emit_progress,
                )
            self.finished.emit(result)
        except AppError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive UI safety net
            self.failed.emit(f"Unexpected error: {exc}")

    def _emit_progress(self, message: str, percent: int) -> None:
        self.progress.emit(message, percent)


@dataclass(slots=True)
class WaveformRequest:
    source_path: Path
    preview_path: Path
    config_path: str | None


class WaveformWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str)

    def __init__(self, request: WaveformRequest) -> None:
        super().__init__()
        self.request = request

    def run(self) -> None:
        try:
            config = load_config(self.request.config_path)
            created = render_waveform_preview(
                input_path=self.request.source_path,
                output_path=self.request.preview_path,
                ffmpeg_binary=config.ffmpeg_binary,
            )
            self.finished.emit(str(self.request.source_path), created)
        except Exception:
            self.failed.emit(str(self.request.source_path))


class MetricCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        layout = QGridLayout(self)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")

        self.before_label = QLabel("--")
        self.before_label.setObjectName("metricBefore")
        self.after_label = QLabel("--")
        self.after_label.setObjectName("metricAfter")
        self.delta_label = QLabel("--")
        self.delta_label.setObjectName("metricDelta")

        self.bar = QProgressBar()
        self.bar.setObjectName("deltaBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)

        self.hint_label = QLabel("--")
        self.hint_label.setObjectName("metricHint")
        self.hint_label.setWordWrap(True)

        layout.addWidget(self.title_label, 0, 0, 1, 2)
        layout.addWidget(self.before_label, 1, 0)
        layout.addWidget(self.after_label, 1, 1)
        layout.addWidget(self.delta_label, 2, 1)
        layout.addWidget(self.bar, 3, 0, 1, 2)
        layout.addWidget(self.hint_label, 4, 0, 1, 2)

    def set_values(self, before: str, after: str, delta: str, magnitude: int, hint: str) -> None:
        self.before_label.setText(before)
        self.after_label.setText(after)
        self.delta_label.setText(delta)
        self.bar.setValue(max(0, min(magnitude, 100)))
        self.hint_label.setText(hint)


class PlaybackWaveform(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("playbackWaveform")
        self.setMinimumHeight(150)
        self._label = "No audio playing"
        self._path = ""
        self._bars = self._make_bars("")
        self._position = 0
        self._duration = 0
        self._is_playing = False
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)

    def set_track(self, path: Path, label: str) -> None:
        self._path = str(path)
        self._label = label
        self._bars = self._make_bars(self._path)
        self._position = 0
        self._duration = 0
        self._is_playing = True
        self._timer.start()
        self.update()

    def set_position(self, position: int) -> None:
        self._position = max(position, 0)
        self.update()

    def set_duration(self, duration: int) -> None:
        self._duration = max(duration, 0)
        self.update()

    def stop(self) -> None:
        self._is_playing = False
        self._timer.stop()
        self.update()

    def clear(self) -> None:
        self._label = "No audio playing"
        self._path = ""
        self._position = 0
        self._duration = 0
        self._is_playing = False
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 1000
        self.update()

    def _make_bars(self, key: str) -> list[float]:
        seed = sum((idx + 1) * ord(char) for idx, char in enumerate(key or "optimaster"))
        bars: list[float] = []
        value = seed or 1
        for idx in range(88):
            value = (value * 1103515245 + 12345 + idx) & 0x7FFFFFFF
            base = 0.18 + (value % 100) / 160
            pulse = 0.18 * (1 + ((idx * 7 + seed) % 9)) / 9
            bars.append(min(base + pulse, 0.95))
        return bars

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(14, 12, -14, -12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#10151b"))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(QColor("#b9c6ce"))
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignmentFlag.AlignTop, self._label)

        bars_rect = rect.adjusted(12, 38, -12, -14)
        if not self._bars:
            return

        progress = self._position / self._duration if self._duration else 0.0
        progress = max(0.0, min(progress, 1.0))
        bar_gap = 3
        bar_width = max(3, int((bars_rect.width() - bar_gap * (len(self._bars) - 1)) / len(self._bars)))
        center_y = bars_rect.center().y()
        max_height = bars_rect.height() * 0.82

        for idx, amplitude in enumerate(self._bars):
            x = bars_rect.left() + idx * (bar_width + bar_gap)
            animated = amplitude
            if self._is_playing:
                animated += 0.08 * (((idx + self._phase) % 12) / 12)
            height = max(8, min(max_height, max_height * animated))
            y = center_y - height / 2
            played = idx / max(len(self._bars) - 1, 1) <= progress
            color = QColor("#2ac6a8" if played else "#2d3a45")
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_width, height), 3, 3)

        playhead_x = bars_rect.left() + bars_rect.width() * progress
        painter.setBrush(QColor("#e5b94d"))
        painter.drawRoundedRect(QRectF(playhead_x - 2, bars_rect.top(), 4, bars_rect.height()), 2, 2)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(1180, 720)
        self.setMinimumSize(980, 560)

        self.current_analysis: SourceAnalysis | None = None
        self.current_session: OptimizationSession | None = None
        self.current_output_dir: Path | None = None
        self.waveform_preview_path: Path | None = None
        self.destination_profiles = {
            "Streaming clean": "streaming_prudent",
            "SoundCloud / DJ loud": "club_loud",
            "Archive safe": "archive_safe",
        }
        self._thread: QThread | None = None
        self._worker: EngineWorker | None = None
        self._active_worker_kind: str | None = None
        self._waveform_thread: QThread | None = None
        self._waveform_worker: WaveformWorker | None = None
        self._pending_waveform_source: Path | None = None
        self.history_store = SessionHistoryStore()
        self.audio_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_player.setAudioOutput(self.audio_output)
        self.current_playback: str | None = None

        self._build_ui()
        self._apply_styles()
        self._load_history()
        self._update_actions()
        self._schedule_window_fit()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(18)

        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setObjectName("workflowTabs")

        source_step = QWidget()
        source_layout = QVBoxLayout(source_step)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(14)
        source_layout.addWidget(self._build_header())
        source_layout.addWidget(self._build_controls())
        source_layout.addWidget(self._build_source_analysis())
        source_layout.addWidget(self._build_render_controls())
        source_layout.addStretch(1)

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

        self.workflow_tabs.addTab(source_step, "Source")
        self.workflow_tabs.addTab(candidate_step, "Versions")
        self.workflow_tabs.addTab(listening_step, "Listen / Export")
        root.addWidget(self.workflow_tabs)
        root.addStretch(1)

        self.setCentralWidget(central)
        self._build_menu()

    def _build_header(self) -> QGroupBox:
        self.session_box = QGroupBox("Session")
        self.session_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(self.session_box)

        self.drop_frame = DropFrame()
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("Drop a WAV or FLAC premaster")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            f"Classic path: choose a file, analyze it, then render candidates. Beta {APP_VERSION}."
        )
        subtitle.setWordWrap(True)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(r"C:\path\to\track.wav")
        self.input_edit.textChanged.connect(self._update_actions)
        browse_button = QPushButton("Choose file")
        browse_button.setObjectName("secondaryAction")
        browse_button.clicked.connect(self._browse_input_file)
        row.addWidget(self.input_edit, stretch=1)
        row.addWidget(browse_button)

        drop_layout.addWidget(title)
        drop_layout.addWidget(subtitle)
        drop_layout.addLayout(row)
        layout.addWidget(self.drop_frame)
        self.drop_frame.file_dropped.connect(self._set_input_path)
        return self.session_box

    def _build_controls(self) -> QGroupBox:
        self.analyze_box = QGroupBox("Analyze source")
        self.analyze_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QGridLayout(self.analyze_box)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self.selected_source_label = QLabel("Source selected. Analyze it to unlock mastering choices.")
        self.selected_source_label.setObjectName("storyLabel")
        self.selected_source_label.setWordWrap(True)
        self.change_source_button = QPushButton("Change source")
        self.change_source_button.setObjectName("utilityAction")
        self.change_source_button.clicked.connect(self._browse_input_file)
        self.analyze_button = QPushButton("Analyze source")
        self.analyze_button.setObjectName("stepAction")
        self.analyze_button.clicked.connect(self._run_analyze)
        self.status_label = QLabel("Step 1: choose a source file to begin.")
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        layout.addWidget(self.selected_source_label, 0, 0, 1, 3)
        layout.addWidget(self.change_source_button, 0, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.analyze_button, 1, 0)
        layout.addWidget(self.status_label, 1, 1, 1, 2)
        layout.addWidget(self.progress_bar, 1, 3)
        return self.analyze_box

    def _build_render_controls(self) -> QGroupBox:
        self.render_box = QGroupBox("Render candidates")
        self.render_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QGridLayout(self.render_box)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self.render_context_label = QLabel("Source ready. Choose a target, then render versions.")
        self.render_context_label.setObjectName("storyLabel")
        self.render_context_label.setWordWrap(True)
        self.source_review_button = QPushButton("Review source analysis")
        self.source_review_button.setObjectName("secondaryAction")
        self.source_review_button.clicked.connect(self._toggle_source_review)
        self.output_edit = QLineEdit(str(Path.cwd() / "renders"))
        self.config_edit = QLineEdit()
        self.config_edit.setPlaceholderText("Optional YAML config")
        self.mode_combo = QComboBox()
        mode_labels = {
            OptimizationMode.SAFE: "Clean / safe",
            OptimizationMode.BALANCED: "Balanced master",
            OptimizationMode.LOUDER: "Push louder",
        }
        for mode in OptimizationMode:
            self.mode_combo.addItem(mode_labels[mode], mode)
        self.mode_combo.setCurrentIndex(1)
        self.destination_combo = QComboBox()
        for label, value in self.destination_profiles.items():
            self.destination_combo.addItem(label, value)
        self.strict_tp_checkbox = QCheckBox("True peak strict (safer after encoding)")
        self.strict_tp_checkbox.setChecked(True)
        self.quick_target_combo = QComboBox()
        self.quick_target_combo.addItem("Auto recommended", None)
        self.quick_target_combo.addItem("Clean streaming master (-14 LUFS)", -14.0)
        self.quick_target_combo.addItem("SoundCloud loud clean (-10.5 LUFS)", -10.5)
        self.quick_target_combo.addItem("Club / DJ loud (-9 LUFS)", -9.0)
        self.quick_target_combo.addItem("Hard / raw test (-8 LUFS)", -8.0)
        self.quick_target_combo.addItem("Extreme loudness check (-7 LUFS)", -7.0)
        self.quick_target_combo.currentIndexChanged.connect(self._apply_quick_target)
        self.target_hint_label = QLabel("Auto uses the source analysis to suggest a sane target.")
        self.target_hint_label.setObjectName("targetHint")
        self.target_hint_label.setWordWrap(True)
        self.target_lufs_spin = QDoubleSpinBox()
        self.target_lufs_spin.setRange(-18.0, -6.0)
        self.target_lufs_spin.setDecimals(1)
        self.target_lufs_spin.setSingleStep(0.5)
        self.target_lufs_spin.setValue(-9.0)
        self.target_lufs_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.target_lufs_spin.setToolTip("Target loudness for rendered candidates. Higher, closer to zero, sounds louder.")
        self.target_lufs_unit = QLabel("LUFS")
        self.target_lufs_unit.setObjectName("inputUnit")
        target_lufs_field = QFrame()
        target_lufs_field.setObjectName("inputWithUnit")
        target_lufs_layout = QHBoxLayout(target_lufs_field)
        target_lufs_layout.setContentsMargins(0, 0, 0, 0)
        target_lufs_layout.setSpacing(8)
        target_lufs_layout.addWidget(self.target_lufs_spin, stretch=1)
        target_lufs_layout.addWidget(self.target_lufs_unit)
        self.max_loudness_checkbox = QCheckBox("Find the loudest clean version")
        self.max_loudness_checkbox.setToolTip(
            "Try several louder LUFS targets and rank the best loud/safe compromise."
        )
        self.max_loudness_checkbox.toggled.connect(self._update_actions)
        self.max_loudness_warning = QLabel(
            "Check before export: kick attack, sub control, distortion, and hat fatigue."
        )
        self.max_loudness_warning.setObjectName("warningHint")
        self.max_loudness_warning.setWordWrap(True)
        self.max_loudness_warning.setVisible(False)

        output_button = QPushButton("Choose output")
        output_button.setObjectName("utilityAction")
        output_button.clicked.connect(self._browse_output_dir)
        config_button = QPushButton("Load config")
        config_button.setObjectName("utilityAction")
        config_button.clicked.connect(self._browse_config_file)
        template_button = QPushButton("Create template")
        template_button.setObjectName("utilityAction")
        template_button.clicked.connect(self._create_config_template)
        self.advanced_button = QPushButton("Show advanced options")
        self.advanced_button.setObjectName("secondaryAction")
        self.advanced_button.clicked.connect(self._toggle_advanced_options)
        self.advanced_options_visible = False

        self.optimize_button = QPushButton("Create versions")
        self.export_button = QPushButton("Export final")
        self.optimize_button.setObjectName("stepAction")
        self.export_button.setObjectName("primaryAction")
        self.optimize_button.clicked.connect(self._run_optimize)
        self.export_button.clicked.connect(self._export_selected_candidate)
        self.render_status_label = QLabel("Ready to render candidate versions.")
        self.render_status_label.setObjectName("renderStatus")
        self.render_status_label.setWordWrap(True)
        self.render_progress_bar = QProgressBar()
        self.render_progress_bar.setRange(0, 100)
        self.render_progress_bar.setValue(0)
        self.render_progress_bar.setVisible(False)

        self.mode_label = QLabel("Master goal")
        self.quick_target_label = QLabel("Quick target")
        self.target_lufs_label = QLabel("Level target")
        self.destination_label = QLabel("Usage")
        self.output_label = QLabel("Output folder")
        self.config_label = QLabel("Config file")

        layout.addWidget(self.render_context_label, 0, 0, 1, 3)
        layout.addWidget(self.source_review_button, 0, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.mode_label, 1, 0)
        layout.addWidget(self.mode_combo, 1, 1)
        layout.addWidget(self.quick_target_label, 1, 2)
        layout.addWidget(self.quick_target_combo, 1, 3)
        layout.addWidget(self.destination_label, 2, 0)
        layout.addWidget(self.destination_combo, 2, 1)
        layout.addWidget(self.target_lufs_label, 2, 2)
        layout.addWidget(target_lufs_field, 2, 3)
        layout.addWidget(self.target_hint_label, 3, 0, 1, 2)
        layout.addWidget(self.max_loudness_checkbox, 3, 2, 1, 2)
        layout.addWidget(self.max_loudness_warning, 4, 0, 1, 2)
        layout.addWidget(self.strict_tp_checkbox, 4, 2, 1, 2)
        layout.addWidget(self.output_label, 4, 0)
        layout.addWidget(self.output_edit, 4, 1)
        layout.addWidget(output_button, 4, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.config_label, 5, 0)
        layout.addWidget(self.config_edit, 5, 1)
        layout.addWidget(config_button, 5, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(template_button, 5, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.advanced_button, 6, 0, 1, 4)
        layout.addWidget(self.render_status_label, 7, 0, 1, 2)
        layout.addWidget(self.render_progress_bar, 7, 2, 1, 2)
        layout.addWidget(self.optimize_button, 8, 0, 1, 4)

        self.mastering_widgets = [
            self.render_context_label,
            self.source_review_button,
            self.mode_label,
            self.mode_combo,
            self.quick_target_label,
            self.quick_target_combo,
            self.target_hint_label,
            self.target_lufs_label,
            target_lufs_field,
            self.target_lufs_spin,
            self.destination_label,
            self.destination_combo,
            self.max_loudness_checkbox,
            self.max_loudness_warning,
            self.strict_tp_checkbox,
            self.render_status_label,
            self.render_progress_bar,
            self.optimize_button,
        ]
        self.advanced_widgets = [
            self.output_label,
            self.output_edit,
            output_button,
            self.config_label,
            self.config_edit,
            config_button,
            template_button,
        ]
        return self.render_box

    def _build_source_analysis(self) -> QGroupBox:
        self.source_box = QGroupBox("Source analysis")
        self.source_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        source_layout = QVBoxLayout(self.source_box)
        source_layout.setSpacing(12)
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

        summary_layout = QGridLayout()
        summary_layout.setSpacing(10)
        for index, (key, label) in enumerate(
            [
                ("profile", "Profile"),
                ("integrated", "LUFS"),
                ("true_peak", "True peak"),
                ("lra", "Dynamics"),
            ]
        ):
            tile = QFrame()
            tile.setObjectName("sourceMetricTile")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(12, 10, 12, 10)
            tile_layout.setSpacing(4)
            title = QLabel(label)
            title.setObjectName("sourceMetricLabel")
            self.metric_labels[key].setObjectName("sourceMetricValue")
            tile_layout.addWidget(title)
            tile_layout.addWidget(self.metric_labels[key])
            summary_layout.addWidget(tile, 0, index)
        source_layout.addLayout(summary_layout)

        self.source_details_button = QPushButton("Show waveform and diagnostics")
        self.source_details_button.setObjectName("secondaryAction")
        self.source_details_button.clicked.connect(self._toggle_source_details)
        source_layout.addWidget(self.source_details_button)

        self.source_details_panel = QFrame()
        self.source_details_panel.setObjectName("sourceDetailsPanel")
        details_layout = QFormLayout(self.source_details_panel)
        details_layout.addRow("Diagnostics", self.metric_labels["diagnostics"])
        details_layout.addRow("Engineering note", self.metric_labels["acoustic_note"])
        self.waveform_label = QLabel("Waveform preview appears after file selection.")
        self.waveform_label.setMinimumHeight(130)
        self.waveform_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.waveform_label.setObjectName("waveformPreview")
        details_layout.addRow("Waveform", self.waveform_label)
        self.source_details_panel.setVisible(False)
        source_layout.addWidget(self.source_details_panel)
        return self.source_box

    def _build_best_candidate(self) -> QGroupBox:
        self.best_box = QGroupBox("Best measured compromise")
        self.best_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
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
        self.listen_selected_button = QPushButton("Listen to selected version")
        self.listen_selected_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self.save_note_button = QPushButton("Save listening note")
        self.save_note_button.setObjectName("secondaryAction")
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
        box = QGroupBox("Compare and export")
        layout = QVBoxLayout(box)

        listening_row = QHBoxLayout()
        self.play_source_button = QPushButton("Play source (A)")
        self.play_candidate_button = QPushButton("Play candidate (B)")
        self.stop_audio_button = QPushButton("Stop")
        self.play_source_button.setObjectName("secondaryAction")
        self.play_candidate_button.setObjectName("secondaryAction")
        self.stop_audio_button.setObjectName("secondaryAction")
        self.play_source_button.clicked.connect(self._play_source)
        self.play_candidate_button.clicked.connect(self._play_selected_candidate)
        self.stop_audio_button.clicked.connect(self._stop_playback)
        listening_row.addWidget(self.play_source_button)
        listening_row.addWidget(self.play_candidate_button)
        listening_row.addWidget(self.stop_audio_button)
        listening_row.addWidget(self.export_button)

        self.playback_label = QLabel("Step 5: select a candidate, then compare A and B.")
        self.playback_label.setWordWrap(True)
        self.playback_waveform = PlaybackWaveform()
        self.audio_player.positionChanged.connect(self.playback_waveform.set_position)
        self.audio_player.durationChanged.connect(self.playback_waveform.set_duration)

        self.before_after_panel = QFrame()
        self.before_after_panel.setObjectName("beforeAfterPanel")
        before_after_layout = QGridLayout(self.before_after_panel)
        before_after_layout.setSpacing(10)
        before_label = QLabel("AVANT")
        before_label.setObjectName("comparisonColumnTitle")
        after_label = QLabel("APRES")
        after_label.setObjectName("comparisonColumnTitle")
        before_after_layout.addWidget(before_label, 0, 0)
        before_after_layout.addWidget(after_label, 0, 1)
        self.metric_cards = {
            "loudness": MetricCard("LUFS"),
            "peak": MetricCard("True peak"),
            "lra": MetricCard("Dynamics (LRA)"),
            "score": MetricCard("Technical score"),
        }
        before_after_layout.addWidget(self.metric_cards["loudness"], 1, 0, 1, 2)
        before_after_layout.addWidget(self.metric_cards["peak"], 2, 0, 1, 2)
        before_after_layout.addWidget(self.metric_cards["lra"], 3, 0, 1, 2)
        before_after_layout.addWidget(self.metric_cards["score"], 4, 0, 1, 2)
        self._clear_before_after()

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Date (UTC)", "Session", "Mode", "Best", "Source"])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setDefaultSectionSize(38)
        self.history_table.setMaximumHeight(170)
        self.history_table.setVisible(False)
        self.history_button = QPushButton("Show session history")
        self.history_button.setObjectName("secondaryAction")
        self.history_button.clicked.connect(self._toggle_history)

        layout.addLayout(listening_row)
        layout.addWidget(self.playback_waveform)
        layout.addWidget(self.playback_label)
        layout.addWidget(self.before_after_panel)
        layout.addWidget(self.history_button)
        layout.addWidget(self.history_table)
        return box

    def _build_results(self) -> QGroupBox:
        box = QGroupBox("Choose a version")
        layout = QVBoxLayout(box)

        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(["Choice", "Version", "Score", "LUFS", "TP", "LRA"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(False)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setDefaultSectionSize(40)
        self.results_table.setMaximumHeight(190)
        self.results_table.itemSelectionChanged.connect(self._update_selected_candidate_details)

        self.details_button = QPushButton("Show scoring details")
        self.details_button.setObjectName("secondaryAction")
        self.details_button.clicked.connect(self._toggle_candidate_details)
        self.details_panel = QPlainTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlaceholderText(
            "Step 4: select the recommended version, or an alternative if you want to compare."
        )
        self.details_panel.setMaximumHeight(170)
        self.details_panel.setVisible(False)

        layout.addWidget(self.results_table)
        layout.addWidget(self.details_button)
        layout.addWidget(self.details_panel)
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
                background: #09090b;
                color: #fafafa;
                font-size: 13px;
            }
            QMainWindow, QMenuBar, QMenu {
                background: #09090b;
                color: #e4e4e7;
            }
            QMenuBar {
                border-bottom: 1px solid #18181b;
                padding: 4px 6px;
            }
            QMenuBar::item:selected, QMenu::item:selected {
                background: #18181b;
                border-radius: 8px;
            }
            QTabWidget::pane {
                border: 0;
                padding-top: 14px;
            }
            QTabBar::tab {
                background: #111113;
                color: #a1a1aa;
                border: 1px solid #27272a;
                border-radius: 12px;
                margin-right: 10px;
                padding: 12px 24px;
                min-width: 136px;
            }
            QTabBar::tab:selected {
                background: #14b8a6;
                border-color: #2dd4bf;
                color: #ffffff;
                font-weight: 700;
            }
            QTabBar::tab:disabled {
                color: #52525b;
            }
            QGroupBox {
                background: #111113;
                border: 1px solid #27272a;
                border-radius: 12px;
                margin-top: 20px;
                padding: 24px 18px 18px 18px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                top: 5px;
                padding: 1px 10px;
                color: #5eead4;
                background: #09090b;
                border-radius: 999px;
            }
            #dropFrame {
                border: 1px solid #2dd4bf;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111113, stop:1 #16201f);
            }
            #heroTitle {
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
            }
            #waveformPreview {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #18181b;
                color: #a1a1aa;
                padding: 8px;
            }
            #sourceMetricTile {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #18181b;
            }
            #sourceMetricLabel {
                color: #a1a1aa;
                font-size: 12px;
                font-weight: 600;
            }
            #sourceMetricValue {
                color: #fafafa;
                font-size: 18px;
                font-weight: 800;
            }
            #sourceDetailsPanel {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #0f0f11;
                padding: 10px;
            }
            #targetHint {
                color: #a1a1aa;
                padding: 4px 2px;
            }
            #warningHint {
                color: #facc15;
                background: #18130a;
                border: 1px solid #854d0e;
                border-radius: 8px;
                padding: 8px 10px;
            }
            #renderStatus {
                color: #e4e4e7;
                background: #09090b;
                border: 1px solid #18181b;
                border-radius: 8px;
                padding: 8px 10px;
            }
            #storyLabel {
                color: #e4e4e7;
                background: #09090b;
                border: 1px solid #18181b;
                border-radius: 8px;
                padding: 10px 12px;
            }
            #playbackWaveform {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #111113;
            }
            #beforeAfterPanel {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #0f0f11;
                padding: 10px;
            }
            #metricCard {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #18181b;
                padding: 12px;
            }
            #metricTitle {
                color: #5eead4;
                font-weight: 700;
            }
            #comparisonColumnTitle {
                color: #d4d4d8;
                font-weight: 700;
                padding: 4px 8px;
            }
            #metricBefore, #metricAfter {
                background: #09090b;
                border-radius: 8px;
                padding: 8px;
                font-size: 15px;
                font-weight: 700;
            }
            #metricDelta {
                color: #facc15;
                font-size: 18px;
                font-weight: 700;
            }
            #metricHint {
                color: #d4d4d8;
            }
            #deltaBar {
                min-height: 8px;
                max-height: 8px;
                border-radius: 4px;
                text-align: center;
            }
            #deltaBar::chunk {
                background: #facc15;
                border-radius: 4px;
            }
            QPushButton {
                background: #14b8a6;
                border: 0;
                border-radius: 8px;
                padding: 10px 14px;
                color: #042f2e;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #2dd4bf;
            }
            QPushButton:disabled {
                background: #27272a;
                color: #71717a;
            }
            #primaryAction {
                background: #facc15;
                color: #18181b;
            }
            #primaryAction:hover {
                background: #fde047;
            }
            #secondaryAction {
                background: #18181b;
                border: 1px solid #3f3f46;
                color: #f4f4f5;
            }
            #secondaryAction:hover {
                background: #27272a;
            }
            #stepAction {
                background: #14b8a6;
                color: #042f2e;
                min-height: 18px;
            }
            #stepAction:hover {
                background: #2dd4bf;
            }
            #stepAction:disabled {
                background: #27272a;
                color: #71717a;
            }
            #utilityAction {
                background: transparent;
                border: 1px solid #3f3f46;
                color: #d4d4d8;
                padding: 7px 10px;
                min-width: 112px;
                max-width: 132px;
                font-weight: 600;
            }
            #utilityAction:hover {
                background: #18181b;
                border-color: #71717a;
            }
            QCheckBox {
                spacing: 8px;
                color: #f4f4f5;
                padding: 4px 0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #a1a1aa;
                background: #18181b;
            }
            QCheckBox::indicator:hover {
                border-color: #f4f4f5;
                background: #27272a;
            }
            QCheckBox::indicator:checked {
                border-color: #2dd4bf;
                background: #14b8a6;
            }
            QCheckBox::indicator:checked:hover {
                border-color: #5eead4;
                background: #2dd4bf;
            }
            QCheckBox::indicator:disabled {
                border-color: #52525b;
                background: #18181b;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QSpinBox, QDoubleSpinBox {
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 8px;
                background: #09090b;
                selection-background-color: #14b8a6;
            }
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #2dd4bf;
            }
            #inputWithUnit {
                background: transparent;
            }
            #inputUnit {
                color: #a1a1aa;
                font-weight: 700;
                padding-right: 4px;
            }
            QHeaderView::section {
                background: #18181b;
                color: #e4e4e7;
                border: 0;
                padding: 10px;
                font-weight: 700;
            }
            QTableWidget {
                gridline-color: transparent;
                alternate-background-color: #111113;
                selection-background-color: #14b8a6;
            }
            QTableWidget::item:selected {
                background: #14b8a6;
                color: #042f2e;
            }
            QProgressBar {
                border: 1px solid #27272a;
                border-radius: 999px;
                text-align: center;
                background: #09090b;
                min-height: 16px;
            }
            QProgressBar::chunk {
                background: #38bdf8;
                border-radius: 999px;
            }
            QScrollBar:vertical {
                background: #09090b;
                border: 0;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3f3f46;
                border-radius: 5px;
                min-height: 32px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background: #09090b;
                border: 0;
                height: 10px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #3f3f46;
                border-radius: 5px;
                min-width: 32px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
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

    def _create_config_template(self) -> None:
        source_path = self.input_edit.text().strip()
        default_dir = Path(source_path).resolve().parent if source_path else Path.cwd()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create OptiMaster config template",
            str(default_dir / "optimaster_config_template.yaml"),
            "YAML files (*.yaml *.yml)",
        )
        if not file_path:
            return

        destination = Path(file_path)
        if destination.suffix.lower() not in {".yaml", ".yml"}:
            destination = destination.with_suffix(".yaml")
        destination.write_text(CONFIG_TEMPLATE, encoding="utf-8")
        self.config_edit.setText(str(destination))
        QMessageBox.information(
            self,
            "Config template created",
            f"Created a commented YAML template:\n{destination}",
        )

    def _toggle_advanced_options(self) -> None:
        self.advanced_options_visible = not self.advanced_options_visible
        self.advanced_button.setText(
            "Hide advanced options" if self.advanced_options_visible else "Show advanced options"
        )
        self._update_actions()

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
            self.source_details_panel.setVisible(False)
            self.source_details_button.setText("Show waveform and diagnostics")
            self.source_box.setVisible(False)
            self.source_review_button.setText("Review source analysis")
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
            target_lufs=self.target_lufs_spin.value(),
            maximize_loudness=self.max_loudness_checkbox.isChecked(),
            source_analysis=source_analysis,
        )

    def _apply_quick_target(self) -> None:
        target = self.quick_target_combo.currentData()
        if isinstance(target, float):
            self.target_lufs_spin.setValue(target)

        label = self.quick_target_combo.currentText()
        hints = {
            "Auto recommended": "Auto uses the source analysis to suggest a sane target.",
            "Clean streaming master (-14 LUFS)": "Clean, conservative export for normalized streaming platforms.",
            "SoundCloud loud clean (-10.5 LUFS)": "Louder and direct for SoundCloud, while staying reasonably clean.",
            "Club / DJ loud (-9 LUFS)": "More pressure for DJ sets and club playback; listen for kick and sub control.",
            "Hard / raw test (-8 LUFS)": "Aggressive test for hard techno/raw energy; compare carefully before export.",
            "Extreme loudness check (-7 LUFS)": "Stress test only: high risk of crushed kick, harsh hats, and fatigue.",
        }
        self.target_hint_label.setText(hints.get(label, ""))

    def _analysis_for_request(self, kind: str, input_file: str) -> SourceAnalysis | None:
        if kind != "optimize" or self.current_analysis is None:
            return None
        if self.current_analysis.source_path == Path(input_file).resolve():
            return self.current_analysis
        return None

    def _start_worker(self, request: WorkerRequest) -> None:
        if self._thread is not None:
            return

        self._active_worker_kind = request.kind
        self.current_output_dir = Path(request.output_dir)
        if request.kind == "optimize":
            self.source_box.setVisible(False)
            self.source_review_button.setText("Review source analysis")
            self.render_progress_bar.setValue(0)
            self.render_progress_bar.setVisible(True)
            self.render_status_label.setText("Preparing render...")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Preparing analysis...")
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
        finished_kind = self._active_worker_kind
        self._active_worker_kind = None
        self._set_busy(False)
        if finished_kind == "optimize":
            self.render_progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(False)
        self._update_actions()

    def _on_progress(self, message: str, percent: int) -> None:
        message = self._display_progress_message(message)
        if self._active_worker_kind == "optimize":
            self.render_status_label.setText(message)
            self.render_progress_bar.setValue(percent)
            return
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_worker_finished(self, result: object) -> None:
        if isinstance(result, SourceAnalysis):
            self.current_analysis = result
            self.current_session = None
            self._populate_analysis(result)
            recommended_lufs, lufs_reason = self._recommended_target_lufs(result)
            self.quick_target_combo.setCurrentIndex(0)
            self.target_lufs_spin.setValue(recommended_lufs)
            self.target_hint_label.setText(
                f"Auto recommendation: {recommended_lufs:.1f} LUFS because {lufs_reason}."
            )
            self.source_box.setVisible(False)
            self.source_review_button.setText("Review source analysis")
            self._update_waveform_preview(result.source_path)
            self._clear_results()
            self.status_label.setText(
                f"Step 2 complete. Suggested target: {recommended_lufs:.1f} LUFS ({lufs_reason})."
            )
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
            self.render_status_label.setText("Rendering complete. Review the recommended version.")
            self.render_progress_bar.setValue(100)
            self.progress_bar.setValue(100)
            self.workflow_tabs.setCurrentIndex(1)

    def _on_worker_failed(self, message: str) -> None:
        if self._active_worker_kind == "optimize":
            self.render_status_label.setText("Render failed. Check the error dialog for details.")
            self.render_progress_bar.setValue(0)
        else:
            self.status_label.setText("Task failed. Check the error dialog for details.")
            self.progress_bar.setValue(0)
        self._show_error(message)

    def _populate_analysis(self, analysis: SourceAnalysis) -> None:
        metrics = analysis.metrics
        self.metric_labels["profile"].setText(
            SOURCE_PROFILE_DISPLAY_NAMES.get(analysis.profile, analysis.profile.value.replace("_", " ").title())
        )
        self.metric_labels["integrated"].setText(format_metric(metrics.integrated_lufs, "LUFS"))
        self.metric_labels["true_peak"].setText(format_metric(metrics.true_peak_dbtp, "dBTP"))
        self.metric_labels["lra"].setText(format_metric(metrics.lra_lu, "LU"))
        diagnostics = list(analysis.diagnostics)
        if analysis.profile.value in {"very_hot", "almost_ready"}:
            diagnostics.append("Source already hot: prioritize transparent and minimal moves.")
        self.metric_labels["diagnostics"].setText(" | ".join(diagnostics))

    def _recommended_target_lufs(self, analysis: SourceAnalysis) -> tuple[float, str]:
        metrics = analysis.metrics
        if analysis.profile in {SourceProfile.VERY_HOT, SourceProfile.ALMOST_READY, SourceProfile.TOUCH_MINIMALLY}:
            return -10.5, "source is already hot"
        if analysis.profile is SourceProfile.LOW_DYNAMICS:
            return -11.0, "limited dynamics need headroom"
        if metrics.lra_lu >= 8.0 and metrics.true_peak_dbtp <= -1.0:
            return -9.0, "healthy dynamics can take a louder pass"
        if metrics.integrated_lufs <= -14.0:
            return -10.0, "source has room for gain"
        return -10.0, "balanced default"

    def _populate_session(self, session: OptimizationSession) -> None:
        self.results_table.setRowCount(len(session.candidates))
        for row, candidate in enumerate(session.candidates):
            values = [
                "Best compromise" if row == 0 else self._candidate_choice_label(candidate),
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
        self.best_labels["name"].setText(f"{self._candidate_version_label(candidate)} (best measured compromise)")
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
            f"Use it when: {self._human_preset_description(selected.preset.name, selected.preset.description)}",
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
                "- At matched loudness, is it really better or just louder?",
                "- Does the kick keep its attack?",
                "- Does the sub stay controlled after limiting?",
                "- Do hats or synths become harsh or tiring?",
                "- Test intro, drop, and break, not only the loudest section.",
            ]
        )
        self.details_panel.setPlainText("\n".join(lines))
        self._populate_before_after(selected)
        self.status_label.setText("Step 4 complete. Step 5: listen A/B, then step 6: export.")
        if self.current_session and self.current_session.best_candidate is selected:
            self._populate_best_candidate(selected)
        self._update_actions()

    def _toggle_candidate_details(self) -> None:
        visible = self.details_panel.isHidden()
        self.details_panel.setVisible(visible)
        self.details_button.setText("Hide scoring details" if visible else "Show scoring details")

    def _toggle_source_details(self) -> None:
        visible = self.source_details_panel.isHidden()
        self.source_details_panel.setVisible(visible)
        self.source_details_button.setText(
            "Hide waveform and diagnostics" if visible else "Show waveform and diagnostics"
        )

    def _toggle_source_review(self) -> None:
        visible = self.source_box.isHidden()
        self.source_box.setVisible(visible)
        self.source_review_button.setText(
            "Hide source analysis" if visible else "Review source analysis"
        )

    def _selected_candidate(self) -> CandidateResult | None:
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return None
        item = self.results_table.item(selected_ranges[0].topRow(), 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _candidate_choice_label(self, candidate: CandidateResult) -> str:
        if "_loudest_" in candidate.preset.name:
            return "Max loudness test"
        if candidate.preset.name.endswith("_optimaster"):
            return "Clean fallback"
        if self.current_session and self.current_session.candidates:
            if self.current_session.candidates[0] is candidate:
                return "Best measured compromise"
        return "Your target version"

    def _candidate_version_label(self, candidate: CandidateResult) -> str:
        rank = self._candidate_rank(candidate)
        name = self._human_preset_name(candidate.preset.name)
        if "_loudest_" in candidate.preset.name:
            name = f"{name} - Max loudness"
        if candidate.preset.name.endswith("_optimaster"):
            name = f"{name} - Clean fallback"
        if rank is None:
            return name
        return f"Version {rank}: {name}"

    def _base_preset_name(self, preset_name: str) -> str:
        name = preset_name.removesuffix("_optimaster")
        if "_loudest_" in name:
            name = name.split("_loudest_", 1)[0]
        return name

    def _human_preset_name(self, preset_name: str) -> str:
        base_name = self._base_preset_name(preset_name)
        return PRESET_DISPLAY_NAMES.get(base_name, base_name.replace("_", " ").title())

    def _human_preset_description(self, preset_name: str, fallback: str) -> str:
        return PRESET_DISPLAY_DESCRIPTIONS.get(self._base_preset_name(preset_name), fallback)

    def _display_progress_message(self, message: str) -> str:
        for prefix in ("Rendering ", "Measuring ", "Scoring "):
            if message.startswith(prefix):
                preset_name = message.removeprefix(prefix)
                return f"{prefix}{self._human_preset_name(preset_name)}"
        return message

    def _candidate_rank(self, candidate: CandidateResult) -> int | None:
        if self.current_session is None:
            return None
        for idx, session_candidate in enumerate(self.current_session.candidates, start=1):
            if session_candidate is candidate:
                return idx
        return None

    def _clear_before_after(self) -> None:
        self.metric_cards["loudness"].set_values("--", "--", "--", 0, "Select a version to see loudness change.")
        self.metric_cards["peak"].set_values("--", "--", "--", 0, "Peak safety appears here.")
        self.metric_cards["lra"].set_values("--", "--", "--", 0, "Dynamics change appears here.")
        self.metric_cards["score"].set_values("--", "--", "--", 0, "OptiMaster decision score appears here.")

    def _populate_before_after(self, candidate: CandidateResult) -> None:
        source = candidate.source_metrics
        output = candidate.output_metrics
        loudness_delta = output.integrated_lufs - source.integrated_lufs
        peak_delta = output.true_peak_dbtp - source.true_peak_dbtp
        lra_delta = output.lra_lu - source.lra_lu

        self.metric_cards["loudness"].set_values(
            format_metric(source.integrated_lufs, "LUFS"),
            format_metric(output.integrated_lufs, "LUFS"),
            f"{loudness_delta:+.1f} LUFS",
            self._delta_magnitude(loudness_delta, 6.0),
            "Louder" if loudness_delta > 0 else "Quieter" if loudness_delta < 0 else "Same loudness",
        )
        self.metric_cards["peak"].set_values(
            format_metric(source.true_peak_dbtp, "dBTP"),
            format_metric(output.true_peak_dbtp, "dBTP"),
            f"{peak_delta:+.1f} dB",
            self._delta_magnitude(peak_delta, 4.0),
            "More headroom" if peak_delta < 0 else "Hotter peak" if peak_delta > 0 else "Same peak",
        )
        self.metric_cards["lra"].set_values(
            format_metric(source.lra_lu, "LU"),
            format_metric(output.lra_lu, "LU"),
            f"{lra_delta:+.1f} LU",
            self._delta_magnitude(lra_delta, 4.0),
            "More dynamic" if lra_delta > 0 else "Tighter" if lra_delta < 0 else "Dynamics preserved",
        )
        self.metric_cards["score"].set_values(
            "--",
            f"{candidate.score:.1f}",
            "Best compromise" if self._candidate_rank(candidate) == 1 else "Alternative",
            int(round(candidate.score)),
            "Technical compromise between loudness, safety, and dynamics.",
        )

    def _delta_magnitude(self, delta: float, full_scale: float) -> int:
        return int(round(min(abs(delta) / full_scale, 1.0) * 100))

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
            f"Copied {self._candidate_version_label(candidate)} to:\n{destination}",
        )

    def _default_export_path(self, candidate: CandidateResult) -> Path:
        source_stem = candidate.output_path.stem.removesuffix(f"_{candidate.preset.name}")
        export_dir = candidate.output_path.parent.parent
        suffix = candidate.output_path.suffix or ".wav"
        index = 1
        app_name = APP_TITLE.replace(" ", "")
        while True:
            destination = export_dir / f"{source_stem}_{app_name}_export_{index:02d}{suffix}"
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
        self.status_label.setText(f"Saved note for {self._candidate_version_label(candidate)} in {preferences_path}")

    def _update_waveform_preview(self, source_path: Path) -> None:
        self.waveform_label.setPixmap(QPixmap())
        self.waveform_label.setText("Loading waveform preview...")
        self.status_label.setText("Loading source preview...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)

        if self._waveform_thread is not None:
            self._pending_waveform_source = source_path
            return

        preview_dir = Path(self.output_edit.text().strip() or source_path.parent / "renders")
        request = WaveformRequest(
            source_path=source_path,
            preview_path=preview_dir / f"{source_path.stem}_waveform.png",
            config_path=self.config_edit.text().strip() or None,
        )
        self._waveform_thread = QThread(self)
        self._waveform_worker = WaveformWorker(request)
        self._waveform_worker.moveToThread(self._waveform_thread)
        self._waveform_thread.started.connect(self._waveform_worker.run)
        self._waveform_worker.finished.connect(self._on_waveform_ready)
        self._waveform_worker.failed.connect(self._on_waveform_failed)
        self._waveform_worker.finished.connect(self._cleanup_waveform_worker)
        self._waveform_worker.failed.connect(self._cleanup_waveform_worker)
        self._waveform_thread.start()

    def _on_waveform_ready(self, source_path: str, created: object) -> None:
        current_input = self.input_edit.text().strip()
        if not current_input or Path(current_input).resolve() != Path(source_path):
            return

        created_path = Path(created)
        self.waveform_preview_path = created_path
        pixmap = QPixmap(str(created_path))
        self.waveform_label.setPixmap(
            pixmap.scaled(
                max(self.waveform_label.width(), 260),
                130,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.waveform_label.setText("")
        self._finish_waveform_loading(source_path)

    def _on_waveform_failed(self, source_path: str) -> None:
        current_input = self.input_edit.text().strip()
        if not current_input or Path(current_input).resolve() != Path(source_path):
            return

        self.waveform_preview_path = None
        self.waveform_label.setPixmap(QPixmap())
        self.waveform_label.setText("Waveform preview unavailable for this file.")
        self._finish_waveform_loading(source_path)

    def _finish_waveform_loading(self, source_path: str) -> None:
        if self._thread is not None:
            return

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        current_path = Path(source_path)
        if self.current_analysis is not None and self.current_analysis.source_path == current_path:
            self.status_label.setText("Step 2 complete. Step 3: render candidates.")
            self.progress_bar.setValue(100)
            return

        self.status_label.setText("Step 1 complete. Step 2: analyze the source.")
        self.progress_bar.setValue(0)

    def _cleanup_waveform_worker(self) -> None:
        if self._waveform_thread is None or self._waveform_worker is None:
            return
        self._waveform_thread.quit()
        self._waveform_thread.wait()
        self._waveform_worker.deleteLater()
        self._waveform_thread.deleteLater()
        self._waveform_thread = None
        self._waveform_worker = None
        if self._pending_waveform_source is not None:
            pending_source = self._pending_waveform_source
            self._pending_waveform_source = None
            self._update_waveform_preview(pending_source)

    def _clear_results(self) -> None:
        self.results_table.setRowCount(0)
        self.details_panel.clear()
        self._clear_before_after()
        self._populate_best_candidate(None)
        self.render_status_label.setText("Ready to render candidate versions.")
        self.render_progress_bar.setValue(0)
        self.render_progress_bar.setVisible(False)
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

    def _toggle_history(self) -> None:
        visible = self.history_table.isHidden()
        self.history_table.setVisible(visible)
        self.history_button.setText("Hide session history" if visible else "Show session history")

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
        self._start_playback(candidate.output_path, f"B ({self._candidate_version_label(candidate)})")

    def _start_playback(self, path: Path, label: str) -> None:
        if not path.exists():
            self._show_error(f"Cannot play missing file: {path}")
            return
        self.audio_player.setSource(QUrl.fromLocalFile(str(path)))
        self.audio_player.play()
        self.current_playback = str(path)
        self.playback_waveform.set_track(path, f"Now playing {label}: {path.name}")
        self.playback_label.setText(f"Now playing {label}: {path.name}")

    def _stop_playback(self) -> None:
        self.audio_player.stop()
        self.current_playback = None
        self.playback_waveform.stop()
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
        self.quick_target_combo.setDisabled(busy)
        self.target_lufs_spin.setDisabled(busy)
        self.max_loudness_checkbox.setDisabled(busy)
        self.advanced_button.setDisabled(busy)
        self.change_source_button.setDisabled(busy)
        self.source_review_button.setDisabled(busy)
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
        if has_input and input_path is not None:
            self.selected_source_label.setText(f"Selected source: {input_path.name}. Next: analyze it.")
        if has_analysis:
            self.render_context_label.setText(self._render_story_text())
        self.analyze_button.setEnabled(has_input and not has_analysis and self._thread is None)
        self.analyze_button.setText("Analyzed" if has_analysis else "Analyze source")
        self.optimize_button.setEnabled(has_analysis and self._thread is None)
        self.export_button.setEnabled(self._thread is None and has_candidate)
        self.play_candidate_button.setEnabled(self._thread is None and has_candidate)
        self.listen_selected_button.setEnabled(self._thread is None and has_candidate)
        self.save_note_button.setEnabled(self._thread is None and has_candidate)
        can_choose_target = self._thread is None and not self.max_loudness_checkbox.isChecked()
        self.quick_target_combo.setEnabled(can_choose_target)
        self.target_lufs_spin.setEnabled(can_choose_target)
        self.max_loudness_warning.setVisible(has_analysis and self.max_loudness_checkbox.isChecked())
        self.workflow_tabs.setTabEnabled(0, True)
        self.workflow_tabs.setTabEnabled(1, has_candidates)
        self.workflow_tabs.setTabEnabled(2, has_candidate)
        self._sync_control_visibility(has_input, has_analysis)
        self._schedule_window_fit()

    def _sync_control_visibility(self, has_input: bool, has_analysis: bool) -> None:
        self.session_box.setVisible(not has_input)
        self.analyze_box.setVisible(has_input and not has_analysis)
        if not has_analysis:
            self.source_box.setVisible(False)
            if hasattr(self, "source_review_button"):
                self.source_review_button.setText("Review source analysis")
        self.render_box.setVisible(has_analysis)
        for widget in self.mastering_widgets:
            widget.setVisible(has_analysis)
        for widget in self.advanced_widgets:
            widget.setVisible(self.advanced_options_visible)

    def _schedule_window_fit(self) -> None:
        QTimer.singleShot(0, self._fit_window_to_content)

    def _fit_window_to_content(self) -> None:
        if self.isMaximized() or self.isFullScreen():
            return

        current_step = self.workflow_tabs.currentWidget()
        content_hint = current_step.sizeHint().height() if current_step is not None else self.centralWidget().sizeHint().height()
        chrome_height = self.menuBar().sizeHint().height() + self.workflow_tabs.tabBar().sizeHint().height() + 120
        target_height = max(560, min(content_hint + chrome_height, 860))
        if abs(self.height() - target_height) > 28:
            self.resize(self.width(), target_height)

    def _render_story_text(self) -> str:
        if self.current_analysis is None:
            return "Source ready. Choose a target, then render versions."
        metrics = self.current_analysis.metrics
        source_name = self.current_analysis.source_path.name
        return (
            f"{source_name} is analyzed: "
            f"{metrics.integrated_lufs:.1f} LUFS, "
            f"{metrics.true_peak_dbtp:.1f} dBTP, "
            f"{metrics.lra_lu:.1f} LU dynamics. "
            "Choose an objective, then render versions."
        )

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "OptiMaster", message)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
