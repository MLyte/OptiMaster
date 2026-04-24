from __future__ import annotations

import shutil
import sys
import threading
import time
from dataclasses import dataclass
from html import escape
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QSettings, QSize, QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QPixmap
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
    QSlider,
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
from optimaster import __version__
from optimaster.models import CandidateResult, OptimizationMode, OptimizationSession, SourceAnalysis, SourceProfile
from optimaster.service import EngineService


APP_TITLE = "OptiMaster"
APP_VERSION = __version__
APP_RUNTIME = "exe" if getattr(sys, "frozen", False) else "python"
APP_DISPLAY_VERSION = f"{APP_VERSION}-{APP_RUNTIME}"
APP_ICON = "optimaster_icon.ico"
APP_ICON_FALLBACK = "optimaster_icon.svg"
BRAND_ACCENT = "#e5b94d"
CTA_ICON_COLOR = "#071111"
PRIMARY_ICON_COLOR = "#18181b"
SUPPORT_ICON_COLOR = BRAND_ACCENT
SUPPORTED_EXTENSIONS = {".wav", ".flac"}
LANGUAGES = {"en": "English", "fr": "Français"}
UI_TEXT = {
    "en": {
        "menu_file": "File",
        "menu_settings": "Settings",
        "menu_language": "Language",
        "menu_connect": "Connect",
        "menu_choose_audio": "Choose audio file",
        "menu_choose_output": "Choose output folder",
        "menu_quit": "Quit",
        "menu_maker": "Meet the maker",
        "tab_source": "Source",
        "tab_versions": "Versions",
        "tab_listen": "Listen / Export",
        "session": "Session",
        "hero_title": "Drop a WAV or FLAC premaster",
        "hero_subtitle": "Classic path: choose a file, analyze it, then render candidates. Beta {version}.",
        "choose_file": "Choose file",
        "analyze_box": "Analyze source",
        "source_selected": "Source selected. Analyze it to unlock mastering choices.",
        "change_source": "Change source",
        "analyze_source": "Analyze source",
        "analyzed": "Analyzed",
        "processing_time": "Time available",
        "processing_fast": "Fast preview",
        "processing_balanced": "Balanced",
        "processing_best": "Most careful",
        "processing_hint_fast": "Fewer test passes. Good when you want a quick direction.",
        "processing_hint_balanced": "Normal passes. Best default balance between wait time and confidence.",
        "processing_hint_best": "More comparison passes. Slower, but gives OptiMaster more evidence to rank versions.",
        "step_choose_source": "Step 1: choose a source file to begin.",
        "render_box": "Render candidates",
        "render_context_ready": "Source ready. Choose a target, then render versions.",
        "review_source": "Review source analysis",
        "hide_source": "Hide source analysis",
        "optional_config": "Optional YAML config",
        "mode_safe": "Clean / safe",
        "mode_balanced": "Balanced master",
        "mode_louder": "Push louder",
        "destination_streaming": "Streaming clean",
        "destination_soundcloud": "SoundCloud / DJ loud",
        "destination_archive": "Archive safe",
        "tp_strict": "True peak strict (safer after encoding)",
        "target_auto": "Auto recommended",
        "target_streaming": "Clean streaming master (-14 LUFS)",
        "target_soundcloud": "SoundCloud loud clean (-10.5 LUFS)",
        "target_club": "Club / DJ loud (-9 LUFS)",
        "target_hard": "Hard / raw test (-8 LUFS)",
        "target_extreme": "Extreme loudness check (-7 LUFS)",
        "hint_auto": "Auto uses the source analysis to suggest a sane target.",
        "hint_streaming": "Clean, conservative export for normalized streaming platforms.",
        "hint_soundcloud": "Louder and direct for SoundCloud, while staying reasonably clean.",
        "hint_club": "More pressure for DJ sets and club playback; listen for kick and sub control.",
        "hint_hard": "Aggressive test for hard techno/raw energy; compare carefully before export.",
        "hint_extreme": "Stress test only: high risk of crushed kick, harsh hats, and fatigue.",
        "target_tooltip": "Target loudness for rendered candidates. Higher, closer to zero, sounds louder.",
        "max_loudness": "Find the loudest clean version",
        "max_loudness_tip": "Try several louder LUFS targets and rank the best loud/safe compromise.",
        "max_loudness_warning": "Before exporting, listen A/B and check kick attack, sub control, distortion, and hat fatigue.",
        "ab_check": "Go to A/B check",
        "ab_unlock": "A/B check unlocks after versions are created.",
        "choose_output": "Choose output",
        "load_config": "Load config",
        "create_template": "Create template",
        "show_advanced": "Show advanced options",
        "hide_advanced": "Hide advanced options",
        "create_versions": "Create versions",
        "export_final": "Export final",
        "ready_render": "Ready to render candidate versions.",
        "cancel": "Cancel",
        "master_goal": "Master goal",
        "quick_target": "Quick target",
        "level_target": "Level target",
        "usage": "Usage",
        "output_folder": "Output folder",
        "config_file": "Config file",
        "source_analysis": "Source analysis",
        "not_analyzed": "Not analyzed",
        "diagnostics_pending": "Step 2 appears here after analysis.",
        "acoustic_note": "Meters are technical indicators. Final validation depends on monitoring level and room acoustics.",
        "profile": "Profile",
        "true_peak": "True peak",
        "dynamics": "Dynamics",
        "show_waveform": "Show waveform and diagnostics",
        "hide_waveform": "Hide waveform and diagnostics",
        "waveform_pending": "Waveform preview appears after file selection.",
        "best_box": "Best measured compromise",
        "no_candidate_yet": "No candidate yet",
        "candidate_pending": "Step 4: select a candidate after rendering.",
        "listen_selected": "Listen to selected version",
        "save_note": "Save listening note",
        "chosen_version": "Chosen version",
        "score": "Score",
        "metrics": "Metrics",
        "why_choose": "Why choose it",
        "rendered_file": "Rendered file",
        "next": "Next",
        "rating": "Rating (1-5)",
        "preferences": "Preferences",
        "compare_export": "Compare and export",
        "play_source": "Play source (A)",
        "play_candidate": "Play candidate (B)",
        "stop": "Stop",
        "new_analysis": "New analysis",
        "playback_pending": "Step 5: select a candidate, then compare A and B.",
        "metric": "Metric",
        "before": "Before",
        "after": "After",
        "change": "Change",
        "verdict": "Verdict",
        "loudness": "Loudness",
        "show_history": "Show session history",
        "hide_history": "Hide session history",
        "choose_version": "Choose a version",
        "choice": "Choice",
        "version": "Version",
        "show_scoring": "Show scoring details",
        "hide_scoring": "Hide scoring details",
        "details_placeholder": "Step 4: select the recommended version, or an alternative if you want to compare.",
        "select_source_dialog": "Select source file",
        "select_output_dialog": "Select output folder",
        "select_config_dialog": "Select config file",
        "create_config_dialog": "Create OptiMaster config template",
        "config_created_title": "Config template created",
        "config_created_body": "Created a commented YAML template:\n{path}",
        "choose_audio_first": "Choose a WAV or FLAC file first.",
        "step_analyze_next": "Step 1 complete. Step 2: analyze the source.",
        "preparing_render": "Preparing render...",
        "preparing_analysis": "Preparing analysis...",
        "cancelling": "Cancelling after the current FFmpeg step...",
        "selected_source_next": "Selected source: {name}. Next: analyze it.",
        "source_ready_story": "Source ready. Choose a target, then render versions.",
        "analyzed_story": "{name} is analyzed: {lufs:.1f} LUFS, {peak:.1f} dBTP, {lra:.1f} LU dynamics. Choose an objective, then render versions.",
        "auto_recommendation": "Auto recommendation: {lufs:.1f} LUFS because {reason}.",
        "step2_complete": "Step 2 complete. Suggested target: {lufs:.1f} LUFS ({reason}).",
        "step3_complete": "Step 3 complete. Step 4: select a candidate.",
        "render_complete": "Rendering complete. Review the recommended version.",
        "render_cancelled": "Render cancelled. Adjust settings or create versions again.",
        "cancelled": "Cancelled",
        "analysis_cancelled": "Analysis cancelled.",
        "render_failed": "Render failed. Check the error dialog for details.",
        "task_failed": "Task failed. Check the error dialog for details.",
    },
    "fr": {
        "menu_file": "Fichier",
        "menu_settings": "Réglages",
        "menu_language": "Langue",
        "menu_connect": "Contact",
        "menu_choose_audio": "Choisir un fichier audio",
        "menu_choose_output": "Choisir le dossier de sortie",
        "menu_quit": "Quitter",
        "menu_maker": "Qui suis-je ?",
        "tab_source": "Source",
        "tab_versions": "Versions",
        "tab_listen": "Écoute / Export",
        "session": "Session",
        "hero_title": "Dépose un premaster WAV ou FLAC",
        "hero_subtitle": "Parcours simple : choisis un fichier, analyse-le, puis crée les versions. Beta {version}.",
        "choose_file": "Choisir fichier",
        "analyze_box": "Analyser la source",
        "source_selected": "Source choisie. Analyse-la pour débloquer les réglages de mastering.",
        "change_source": "Changer source",
        "analyze_source": "Analyser source",
        "analyzed": "Analysé",
        "processing_time": "Temps disponible",
        "processing_fast": "Apercu rapide",
        "processing_balanced": "Equilibre",
        "processing_best": "Le plus soigne",
        "processing_hint_fast": "Moins de passes testees. Pratique pour obtenir une direction vite.",
        "processing_hint_balanced": "Passes normales. Le meilleur compromis entre attente et confiance.",
        "processing_hint_best": "Plus de passes comparees. Plus lent, mais le classement est mieux informe.",
        "step_choose_source": "Étape 1 : choisis un fichier source.",
        "render_box": "Créer les versions",
        "render_context_ready": "Source prête. Choisis un objectif, puis crée les versions.",
        "review_source": "Voir analyse source",
        "hide_source": "Masquer analyse source",
        "optional_config": "Config YAML optionnelle",
        "mode_safe": "Propre / safe",
        "mode_balanced": "Master équilibré",
        "mode_louder": "Plus fort",
        "destination_streaming": "Streaming propre",
        "destination_soundcloud": "SoundCloud / DJ fort",
        "destination_archive": "Archive safe",
        "tp_strict": "True peak strict (plus safe après encodage)",
        "target_auto": "Recommandé auto",
        "target_streaming": "Master streaming propre (-14 LUFS)",
        "target_soundcloud": "SoundCloud fort propre (-10.5 LUFS)",
        "target_club": "Club / DJ fort (-9 LUFS)",
        "target_hard": "Hard / raw test (-8 LUFS)",
        "target_extreme": "Test extrême loudness (-7 LUFS)",
        "hint_auto": "Auto utilise l’analyse source pour proposer une cible saine.",
        "hint_streaming": "Export propre et prudent pour les plateformes avec normalisation.",
        "hint_soundcloud": "Plus fort et direct pour SoundCloud, tout en restant raisonnablement propre.",
        "hint_club": "Plus de pression pour DJ sets et club ; écoute le kick et le sub.",
        "hint_hard": "Test agressif hard techno/raw ; compare avant d’exporter.",
        "hint_extreme": "Stress test seulement : gros risque de kick écrasé, hats durs et fatigue.",
        "target_tooltip": "Loudness cible des versions créées. Plus proche de zéro = plus fort.",
        "max_loudness": "Trouver la version propre la plus forte",
        "max_loudness_tip": "Teste plusieurs cibles LUFS plus fortes et classe le meilleur compromis loud/safe.",
        "max_loudness_warning": "Avant export, écoute A/B et vérifie l’attaque du kick, le sub, la distorsion et la fatigue des hats.",
        "ab_check": "Aller au check A/B",
        "ab_unlock": "Le check A/B se débloque après création des versions.",
        "choose_output": "Sortie",
        "load_config": "Charger config",
        "create_template": "Template YAML",
        "show_advanced": "Afficher options avancées",
        "hide_advanced": "Masquer options avancées",
        "create_versions": "Créer versions",
        "export_final": "Exporter final",
        "ready_render": "Prêt à créer les versions candidates.",
        "cancel": "Annuler",
        "master_goal": "Objectif",
        "quick_target": "Cible rapide",
        "level_target": "Niveau cible",
        "usage": "Usage",
        "output_folder": "Dossier sortie",
        "config_file": "Config",
        "source_analysis": "Analyse source",
        "not_analyzed": "Non analysé",
        "diagnostics_pending": "L’étape 2 apparaîtra ici après analyse.",
        "acoustic_note": "Les mesures sont des indicateurs techniques. La validation finale dépend du niveau d’écoute et de la pièce.",
        "profile": "Profil",
        "true_peak": "True peak",
        "dynamics": "Dynamique",
        "show_waveform": "Afficher onde et diagnostics",
        "hide_waveform": "Masquer onde et diagnostics",
        "waveform_pending": "L’aperçu d’onde apparaît après sélection du fichier.",
        "best_box": "Meilleur compromis mesuré",
        "no_candidate_yet": "Aucune version",
        "candidate_pending": "Étape 4 : sélectionne une version après rendu.",
        "listen_selected": "Écouter la version choisie",
        "save_note": "Sauver note d’écoute",
        "chosen_version": "Version choisie",
        "score": "Score",
        "metrics": "Mesures",
        "why_choose": "Pourquoi",
        "rendered_file": "Fichier rendu",
        "next": "Suite",
        "rating": "Note (1-5)",
        "preferences": "Préférences",
        "compare_export": "Comparer et exporter",
        "play_source": "Lire source (A)",
        "play_candidate": "Lire version (B)",
        "stop": "Stop",
        "new_analysis": "Nouvelle analyse",
        "playback_pending": "Étape 5 : sélectionne une version, puis compare A et B.",
        "metric": "Mesure",
        "before": "Avant",
        "after": "Après",
        "change": "Différence",
        "verdict": "Avis",
        "loudness": "Loudness",
        "show_history": "Afficher historique",
        "hide_history": "Masquer historique",
        "choose_version": "Choisir une version",
        "choice": "Choix",
        "version": "Version",
        "show_scoring": "Afficher scoring",
        "hide_scoring": "Masquer scoring",
        "details_placeholder": "Étape 4 : sélectionne la version recommandée, ou une alternative à comparer.",
        "select_source_dialog": "Choisir un fichier source",
        "select_output_dialog": "Choisir le dossier de sortie",
        "select_config_dialog": "Choisir un fichier config",
        "create_config_dialog": "Créer un template OptiMaster",
        "config_created_title": "Template config créé",
        "config_created_body": "Template YAML commenté créé :\n{path}",
        "choose_audio_first": "Choisis d’abord un fichier WAV ou FLAC.",
        "step_analyze_next": "Étape 1 terminée. Étape 2 : analyser la source.",
        "preparing_render": "Préparation du rendu...",
        "preparing_analysis": "Préparation de l’analyse...",
        "cancelling": "Annulation après l’étape FFmpeg en cours...",
        "selected_source_next": "Source choisie : {name}. Prochaine étape : analyse.",
        "source_ready_story": "Source prête. Choisis une cible, puis crée les versions.",
        "analyzed_story": "{name} est analysé : {lufs:.1f} LUFS, {peak:.1f} dBTP, {lra:.1f} LU de dynamique. Choisis un objectif, puis crée les versions.",
        "auto_recommendation": "Recommandation auto : {lufs:.1f} LUFS car {reason}.",
        "step2_complete": "Étape 2 terminée. Cible suggérée : {lufs:.1f} LUFS ({reason}).",
        "step3_complete": "Étape 3 terminée. Étape 4 : sélectionne une version.",
        "render_complete": "Rendu terminé. Vérifie la version recommandée.",
        "render_cancelled": "Rendu annulé. Ajuste les réglages ou recrée les versions.",
        "cancelled": "Annulé",
        "analysis_cancelled": "Analyse annulée.",
        "render_failed": "Le rendu a échoué. Vérifie le message d’erreur.",
        "task_failed": "La tâche a échoué. Vérifie le message d’erreur.",
    },
}
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
LUCIDE_ICON_PATHS = {
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "audio-lines": '<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "eye": '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "file-cog": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h6"/><path d="M14 2v6h6"/><path d="M12 18h.01"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 11.6 15a1.65 1.65 0 0 0-.6-1l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 15 11.6a1.65 1.65 0 0 0 1-.6l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 15Z"/><circle cx="15" cy="15" r="1"/>',
    "file-plus": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="M9 15h6"/>',
    "folder-open": '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6A2 2 0 0 1 18.46 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v2"/>',
    "headphones": '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    "list": '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "refresh": '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M16 8h5V3"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.72l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
    "square": '<rect width="14" height="14" x="5" y="5" rx="2"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    "wand": '<path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9H6"/><path d="M20 9h-2"/><path d="m17.8 6.2 1.4-1.4"/><path d="m10.8 13.2-1.4 1.4"/><path d="m10.8 4.8-1.4-1.4"/><path d="m17.8 11.8 1.4 1.4"/><path d="M4 20 14 10"/>',
    "waveform": '<path d="M2 13h2l2-7 4 14 4-18 4 11h4"/>',
}


def format_metric(value: float, unit: str) -> str:
    return f"{value:.1f} {unit}"


def app_asset_path(filename: str):
    try:
        return resources.files("optimaster.assets").joinpath(filename)
    except ModuleNotFoundError:
        frozen_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        candidates = [
            frozen_root / "optimaster" / "assets" / filename,
            Path(__file__).resolve().parent / "assets" / filename,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]


def app_icon() -> QIcon:
    icon_path = app_asset_path(APP_ICON)
    if not icon_path.is_file():
        icon_path = app_asset_path(APP_ICON_FALLBACK)
    return QIcon(str(icon_path))


def lucide_icon(name: str, color: str = SUPPORT_ICON_COLOR) -> QIcon:
    path = LUCIDE_ICON_PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
    )
    pixmap = QPixmap()
    pixmap.loadFromData(svg.encode("utf-8"), "SVG")
    return QIcon(pixmap)


def set_lucide_icon(button: QPushButton, name: str, color: str = SUPPORT_ICON_COLOR) -> None:
    button.setIcon(lucide_icon(name, color))
    button.setIconSize(QSize(17, 17))


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
    processing_quality: int
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
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            config = load_config(self.request.config_path)
            service = EngineService(config=config)
            if self.request.kind == "analyze":
                result = service.analyze_source(
                    self.request.input_file,
                    progress_callback=self._emit_progress,
                    cancel_callback=self._cancelled.is_set,
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
                    processing_quality=self.request.processing_quality,
                    progress_callback=self._emit_progress,
                    cancel_callback=self._cancelled.is_set,
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


class ComparisonRow(QFrame):
    def __init__(self, metric: str) -> None:
        super().__init__()
        self.setObjectName("comparisonRow")
        layout = QGridLayout(self)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 2)
        layout.setColumnStretch(3, 2)
        layout.setColumnStretch(4, 4)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(4)

        self.metric_label = QLabel(metric)
        self.metric_label.setObjectName("comparisonMetric")
        self.before_label = QLabel("--")
        self.before_label.setObjectName("comparisonValue")
        self.after_label = QLabel("--")
        self.after_label.setObjectName("comparisonValue")
        self.change_label = QLabel("--")
        self.change_label.setObjectName("comparisonChange")
        self.verdict_label = QLabel("--")
        self.verdict_label.setObjectName("comparisonVerdict")
        self.verdict_label.setWordWrap(True)

        layout.addWidget(self.metric_label, 0, 0)
        layout.addWidget(self.before_label, 0, 1)
        layout.addWidget(self.after_label, 0, 2)
        layout.addWidget(self.change_label, 0, 3)
        layout.addWidget(self.verdict_label, 0, 4)

    def set_values(self, before: str, after: str, change: str, verdict: str, good: bool | None = None) -> None:
        self.before_label.setText(before)
        self.after_label.setText(after)
        self.change_label.setText(change)
        self.verdict_label.setText(verdict)
        if good is None:
            self.change_label.setProperty("tone", "")
        else:
            self.change_label.setProperty("tone", "good" if good else "warn")
        self.change_label.style().unpolish(self.change_label)
        self.change_label.style().polish(self.change_label)


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


class RenderBusyOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("renderBusyOverlay")
        self._message = "Creating versions..."
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self, message: str) -> None:
        self._message = message
        self._phase = 0
        self._timer.start()
        self.show()
        self.raise_()
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def set_message(self, message: str) -> None:
        self._message = message
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 12) % 360
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(9, 9, 11, 52))

        panel_width = min(560, max(360, self.width() - 120))
        panel_height = 104
        panel = QRectF(
            (self.width() - panel_width) / 2,
            (self.height() - panel_height) / 2,
            panel_width,
            panel_height,
        )
        painter.setPen(QPen(QColor("#3f3f46"), 1))
        painter.setBrush(QColor("#111113"))
        painter.drawRoundedRect(panel, 12, 12)

        spinner = QRectF(panel.left() + 24, panel.top() + 33, 38, 38)
        painter.setPen(QPen(QColor("#27272a"), 4))
        painter.drawArc(spinner, 0, 360 * 16)
        painter.setPen(QPen(QColor("#2dd4bf"), 4))
        painter.drawArc(spinner, -self._phase * 16, 110 * 16)

        text_rect = panel.adjusted(78, 18, -22, -18)
        painter.setPen(QColor("#fafafa"))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self._message,
        )


class AnimatedProgressBar(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self._phase = 0
        self._is_animating = False
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)

    def start_animation(self) -> None:
        self._is_animating = True
        self._timer.start()
        self.update()

    def stop_animation(self) -> None:
        self._is_animating = False
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 10) % 1000
        self.update()

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        if not self._is_animating or self.value() <= self.minimum():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        progress_ratio = (self.value() - self.minimum()) / max(self.maximum() - self.minimum(), 1)
        chunk_width = int(self.width() * progress_ratio)
        if chunk_width <= 0:
            return

        shimmer_width = max(48, self.width() // 7)
        x = int((self._phase / 1000) * (chunk_width + shimmer_width * 2)) - shimmer_width * 2
        shimmer_rect = QRectF(x, 2, shimmer_width, max(4, self.height() - 4))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 48))
        painter.drawRoundedRect(shimmer_rect, 6, 6)


class WorkPulse(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("workPulse")
        self.setMinimumSize(92, 30)
        self.setMaximumHeight(30)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(65)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self) -> None:
        self._phase = 0
        self._timer.start()
        self.show()
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 24
        self.update()

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        rect = self.rect().adjusted(8, 5, -8, -5)
        bar_count = 9
        gap = 4
        bar_width = max(4, int((rect.width() - gap * (bar_count - 1)) / bar_count))
        center_y = rect.center().y()
        max_height = rect.height()
        for idx in range(bar_count):
            wave = ((idx * 3 + self._phase) % 12) / 11
            height = 6 + int(max_height * (0.25 + 0.65 * wave))
            x = rect.left() + idx * (bar_width + gap)
            y = center_y - height / 2
            color = QColor("#4de0d2" if idx % 2 else "#d7c6a1")
            color.setAlpha(130 + int(90 * wave))
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_width, height), 3, 3)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} - {APP_DISPLAY_VERSION}")
        self.setWindowIcon(app_icon())
        self.resize(1240, 760)
        self.setMinimumSize(1080, 640)
        self.settings = QSettings("OptiMaster", "OptiMaster")
        self.language = str(self.settings.value("language", "en"))
        if self.language not in UI_TEXT:
            self.language = "en"

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
        self._progress_started_at: float | None = None
        self._last_progress_message: str | None = None
        self._last_progress_percent: int = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(1000)
        self._progress_timer.timeout.connect(self._refresh_elapsed_progress)

        self._build_ui()
        self._apply_language_texts()
        self._apply_styles()
        self._load_history()
        self._update_actions()
        self._schedule_window_fit()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(18)

        root.addWidget(self._build_brand_header())

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

    def _build_brand_header(self) -> QFrame:
        brand = QFrame()
        brand.setObjectName("brandHeader")
        brand.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QHBoxLayout(brand)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("brandLogo")
        logo.setPixmap(app_icon().pixmap(38, 38))
        name = QLabel(APP_TITLE)
        name.setObjectName("brandName")
        self.version_label = QLabel(f"Beta {APP_DISPLAY_VERSION}")
        self.version_label.setObjectName("brandVersion")

        layout.addWidget(logo)
        layout.addWidget(name)
        layout.addWidget(self.version_label)
        layout.addStretch(1)
        return brand

    def _build_header(self) -> QGroupBox:
        self.session_box = QGroupBox("Session")
        self.session_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(self.session_box)

        self.drop_frame = DropFrame()
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(18, 18, 18, 18)

        title_row = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(lucide_icon("waveform", BRAND_ACCENT).pixmap(28, 28))
        title_icon.setObjectName("heroIcon")
        self.hero_title = QLabel("Drop a WAV or FLAC premaster")
        self.hero_title.setObjectName("heroTitle")
        title_row.addWidget(title_icon)
        title_row.addWidget(self.hero_title)
        title_row.addStretch(1)
        self.hero_subtitle = QLabel(
            f"Classic path: choose a file, analyze it, then render candidates. Beta {APP_DISPLAY_VERSION}."
        )
        self.hero_subtitle.setWordWrap(True)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(r"C:\path\to\track.wav")
        self.input_edit.textChanged.connect(self._update_actions)
        self.browse_button = QPushButton("Choose file")
        self.browse_button.setObjectName("secondaryAction")
        set_lucide_icon(self.browse_button, "upload")
        self.browse_button.clicked.connect(self._browse_input_file)
        row.addWidget(self.input_edit, stretch=1)
        row.addWidget(self.browse_button)

        drop_layout.addLayout(title_row)
        drop_layout.addWidget(self.hero_subtitle)
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
        set_lucide_icon(self.change_source_button, "refresh")
        self.change_source_button.clicked.connect(self._browse_input_file)
        self.analyze_button = QPushButton("Analyze source")
        self.analyze_button.setObjectName("stepAction")
        set_lucide_icon(self.analyze_button, "activity", CTA_ICON_COLOR)
        self.analyze_button.clicked.connect(self._run_analyze)
        self.processing_label = QLabel("Time available")
        self.processing_label.setObjectName("formLabel")
        self.processing_slider = QSlider(Qt.Orientation.Horizontal)
        self.processing_slider.setRange(0, 2)
        self.processing_slider.setValue(1)
        self.processing_slider.setTickInterval(1)
        self.processing_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.processing_slider.valueChanged.connect(self._update_processing_hint)
        processing_scale = QHBoxLayout()
        processing_scale.setSpacing(8)
        self.processing_fast_label = QLabel("Fast preview")
        self.processing_balanced_label = QLabel("Balanced")
        self.processing_best_label = QLabel("Most careful")
        for label in (self.processing_fast_label, self.processing_balanced_label, self.processing_best_label):
            label.setObjectName("sliderScaleLabel")
        processing_scale.addWidget(self.processing_fast_label)
        processing_scale.addStretch(1)
        processing_scale.addWidget(self.processing_balanced_label)
        processing_scale.addStretch(1)
        processing_scale.addWidget(self.processing_best_label)
        processing_slider_layout = QVBoxLayout()
        processing_slider_layout.setSpacing(4)
        processing_slider_layout.addWidget(self.processing_slider)
        processing_slider_layout.addLayout(processing_scale)
        self.processing_hint_label = QLabel("Normal passes. Best default balance between wait time and confidence.")
        self.processing_hint_label.setObjectName("targetHint")
        self.processing_hint_label.setWordWrap(True)
        self.status_label = QLabel("Step 1: choose a source file to begin.")
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        layout.addWidget(self.selected_source_label, 0, 0, 1, 3)
        layout.addWidget(self.change_source_button, 0, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.processing_label, 1, 0)
        layout.addLayout(processing_slider_layout, 1, 1, 1, 2)
        layout.addWidget(self.processing_hint_label, 1, 3)
        layout.addWidget(self.analyze_button, 2, 0)
        layout.addWidget(self.status_label, 2, 1, 1, 2)
        layout.addWidget(self.progress_bar, 2, 3)
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
        set_lucide_icon(self.source_review_button, "eye")
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
        self.max_loudness_checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.max_loudness_checkbox.setToolTip(
            "Try several louder LUFS targets and rank the best loud/safe compromise."
        )
        self.max_loudness_checkbox.toggled.connect(self._update_actions)
        self.max_loudness_warning = QLabel(
            "Before exporting, listen A/B and check kick attack, sub control, distortion, and hat fatigue."
        )
        self.max_loudness_warning.setObjectName("warningHint")
        self.max_loudness_warning.setWordWrap(True)
        self.max_loudness_warning.setVisible(False)
        self.listen_check_button = QPushButton("Go to A/B check")
        self.listen_check_button.setObjectName("secondaryAction")
        self.listen_check_button.setMinimumWidth(220)
        set_lucide_icon(self.listen_check_button, "headphones")
        self.listen_check_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self.listen_check_button.setVisible(False)
        self.listen_check_hint = QLabel("A/B check unlocks after versions are created.")
        self.listen_check_hint.setObjectName("statusHint")
        self.listen_check_hint.setWordWrap(True)
        self.listen_check_hint.setVisible(False)

        self.output_button = QPushButton("Choose output")
        self.output_button.setObjectName("utilityAction")
        set_lucide_icon(self.output_button, "folder-open")
        self.output_button.clicked.connect(self._browse_output_dir)
        self.config_button = QPushButton("Load config")
        self.config_button.setObjectName("utilityAction")
        set_lucide_icon(self.config_button, "file-cog")
        self.config_button.clicked.connect(self._browse_config_file)
        self.template_button = QPushButton("Create template")
        self.template_button.setObjectName("utilityAction")
        set_lucide_icon(self.template_button, "file-plus")
        self.template_button.clicked.connect(self._create_config_template)
        self.advanced_button = QPushButton("Show advanced options")
        self.advanced_button.setObjectName("secondaryAction")
        set_lucide_icon(self.advanced_button, "settings")
        self.advanced_button.clicked.connect(self._toggle_advanced_options)
        self.advanced_options_visible = False

        self.optimize_button = QPushButton("Create versions")
        self.export_button = QPushButton("Export final")
        self.optimize_button.setObjectName("stepAction")
        self.export_button.setObjectName("primaryAction")
        set_lucide_icon(self.optimize_button, "audio-lines", CTA_ICON_COLOR)
        set_lucide_icon(self.export_button, "download", PRIMARY_ICON_COLOR)
        self.optimize_button.clicked.connect(self._run_optimize)
        self.export_button.clicked.connect(self._export_selected_candidate)
        self.render_status_label = QLabel("Ready to render candidate versions.")
        self.render_status_label.setObjectName("renderStatus")
        self.render_status_label.setWordWrap(True)
        self.render_status_label.setMinimumHeight(52)
        self.render_progress_bar = AnimatedProgressBar()
        self.render_progress_bar.setRange(0, 100)
        self.render_progress_bar.setValue(0)
        self.render_progress_bar.setVisible(False)
        self.render_work_pulse = WorkPulse()
        self.cancel_render_button = QPushButton("Cancel")
        self.cancel_render_button.setObjectName("secondaryAction")
        self.cancel_render_button.setMinimumWidth(110)
        set_lucide_icon(self.cancel_render_button, "square")
        self.cancel_render_button.clicked.connect(self._cancel_active_worker)
        self.cancel_render_button.setVisible(False)

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
        layout.addWidget(self.target_hint_label, 3, 0, 1, 4)
        layout.addWidget(self.max_loudness_checkbox, 4, 0, 1, 2)
        layout.addWidget(self.strict_tp_checkbox, 4, 2, 1, 2)
        layout.addWidget(self.max_loudness_warning, 5, 0, 1, 4)
        layout.addWidget(self.listen_check_button, 6, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.listen_check_hint, 6, 0, 1, 4)
        layout.addWidget(self.output_label, 7, 0)
        layout.addWidget(self.output_edit, 7, 1)
        layout.addWidget(self.output_button, 7, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.config_label, 8, 0)
        layout.addWidget(self.config_edit, 8, 1)
        layout.addWidget(self.config_button, 8, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.template_button, 8, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.advanced_button, 9, 0, 1, 4)
        layout.addWidget(self.render_status_label, 10, 0)
        layout.addWidget(self.render_work_pulse, 10, 1, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.render_progress_bar, 10, 2)
        layout.addWidget(self.cancel_render_button, 10, 3, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.optimize_button, 11, 0, 1, 4)

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
            self.listen_check_hint,
            self.strict_tp_checkbox,
            self.render_status_label,
            self.render_work_pulse,
            self.render_progress_bar,
            self.optimize_button,
        ]
        self.advanced_widgets = [
            self.output_label,
            self.output_edit,
            self.output_button,
            self.config_label,
            self.config_edit,
            self.config_button,
            self.template_button,
        ]
        self.render_overlay = RenderBusyOverlay(self.render_box)
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
        self.metric_labels["diagnostics"].setObjectName("sourceDetailValue")
        self.metric_labels["acoustic_note"].setObjectName("sourceDetailValue")
        self.metric_labels["diagnostics"].setMinimumHeight(46)
        self.metric_labels["acoustic_note"].setMinimumHeight(46)
        self.metric_labels["diagnostics"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.metric_labels["acoustic_note"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        summary_layout = QGridLayout()
        summary_layout.setSpacing(10)
        self.source_metric_titles: dict[str, QLabel] = {}
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
            self.source_metric_titles[key] = title
            self.metric_labels[key].setObjectName("sourceMetricValue")
            tile_layout.addWidget(title)
            tile_layout.addWidget(self.metric_labels[key])
            summary_layout.addWidget(tile, 0, index)
        source_layout.addLayout(summary_layout)

        self.source_details_button = QPushButton("Show waveform and diagnostics")
        self.source_details_button.setObjectName("secondaryAction")
        set_lucide_icon(self.source_details_button, "waveform")
        self.source_details_button.clicked.connect(self._toggle_source_details)
        source_layout.addWidget(self.source_details_button)

        self.source_details_panel = QFrame()
        self.source_details_panel.setObjectName("sourceDetailsPanel")
        details_layout = QFormLayout(self.source_details_panel)
        details_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        details_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        details_layout.setVerticalSpacing(12)
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
        best_layout = QGridLayout(self.best_box)
        best_layout.setContentsMargins(18, 18, 18, 18)
        best_layout.setColumnStretch(0, 0)
        best_layout.setColumnStretch(1, 1)
        best_layout.setHorizontalSpacing(14)
        best_layout.setVerticalSpacing(14)
        self.best_labels = {
            "name": QLabel("No candidate yet"),
            "score": QLabel("--"),
            "metrics": QLabel("--"),
            "reasons": QLabel("Step 4: select a candidate after rendering."),
            "path": QLabel("--"),
        }
        for label in self.best_labels.values():
            label.setObjectName("bestValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.best_labels["reasons"].setMinimumHeight(76)
        self.best_labels["path"].setMinimumHeight(48)
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 5)
        self.rating_spin.setValue(3)
        self.rating_spin.setMinimumHeight(44)
        self.listen_selected_button = QPushButton("Listen to selected version")
        self.listen_selected_button.setMinimumHeight(44)
        self.listen_selected_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        set_lucide_icon(self.listen_selected_button, "headphones")
        self.listen_selected_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self.save_note_button = QPushButton("Save listening note")
        self.save_note_button.setObjectName("secondaryAction")
        self.save_note_button.setMinimumHeight(44)
        self.save_note_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        set_lucide_icon(self.save_note_button, "save")
        self.save_note_button.clicked.connect(self._save_listening_note)

        self.best_row_labels: dict[str, QLabel] = {}

        def add_best_row(row: int, key: str, label_text: str, widget: QWidget) -> None:
            label = QLabel(label_text)
            label.setObjectName("formLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.best_row_labels[key] = label
            best_layout.addWidget(label, row, 0)
            best_layout.addWidget(widget, row, 1)

        add_best_row(0, "chosen_version", "Chosen version", self.best_labels["name"])
        add_best_row(1, "score", "Score", self.best_labels["score"])
        add_best_row(2, "metrics", "Metrics", self.best_labels["metrics"])
        add_best_row(3, "why_choose", "Why choose it", self.best_labels["reasons"])
        add_best_row(4, "rendered_file", "Rendered file", self.best_labels["path"])
        add_best_row(5, "next", "Next", self.listen_selected_button)
        add_best_row(6, "rating", "Rating (1-5)", self.rating_spin)
        add_best_row(7, "preferences", "Preferences", self.save_note_button)
        for row in (5, 6, 7):
            best_layout.setRowMinimumHeight(row, 48)
        return self.best_box

    def _build_listening_tools(self) -> QGroupBox:
        self.listening_box = QGroupBox("Compare and export")
        layout = QVBoxLayout(self.listening_box)

        listening_row = QHBoxLayout()
        self.play_source_button = QPushButton("Play source (A)")
        self.play_candidate_button = QPushButton("Play candidate (B)")
        self.stop_audio_button = QPushButton("Stop")
        self.new_analysis_button = QPushButton("New analysis")
        self.play_source_button.setObjectName("secondaryAction")
        self.play_candidate_button.setObjectName("secondaryAction")
        self.stop_audio_button.setObjectName("secondaryAction")
        self.new_analysis_button.setObjectName("primaryAction")
        set_lucide_icon(self.play_source_button, "play")
        set_lucide_icon(self.play_candidate_button, "headphones")
        set_lucide_icon(self.stop_audio_button, "square")
        set_lucide_icon(self.new_analysis_button, "refresh", PRIMARY_ICON_COLOR)
        self.play_source_button.clicked.connect(self._play_source)
        self.play_candidate_button.clicked.connect(self._play_selected_candidate)
        self.stop_audio_button.clicked.connect(self._stop_playback)
        self.new_analysis_button.clicked.connect(self._start_new_analysis)
        self.new_analysis_button.setVisible(False)
        listening_row.addWidget(self.play_source_button)
        listening_row.addWidget(self.play_candidate_button)
        listening_row.addWidget(self.stop_audio_button)
        listening_row.addWidget(self.export_button)
        listening_row.addWidget(self.new_analysis_button)

        self.playback_label = QLabel("Step 5: select a candidate, then compare A and B.")
        self.playback_label.setWordWrap(True)
        self.playback_waveform = PlaybackWaveform()
        self.audio_player.positionChanged.connect(self.playback_waveform.set_position)
        self.audio_player.durationChanged.connect(self.playback_waveform.set_duration)

        self.before_after_panel = QFrame()
        self.before_after_panel.setObjectName("beforeAfterPanel")
        before_after_layout = QGridLayout(self.before_after_panel)
        before_after_layout.setHorizontalSpacing(12)
        before_after_layout.setVerticalSpacing(8)
        self.comparison_header_labels: dict[str, QLabel] = {}
        for col, (key, title) in enumerate(
            [
                ("metric", "Metric"),
                ("before", "Before"),
                ("after", "After"),
                ("change", "Change"),
                ("verdict", "Verdict"),
            ]
        ):
            header = QLabel(title)
            header.setObjectName("comparisonColumnTitle")
            self.comparison_header_labels[key] = header
            before_after_layout.addWidget(header, 0, col)
        self.comparison_rows = {
            "loudness": ComparisonRow("Loudness"),
            "peak": ComparisonRow("True peak"),
            "lra": ComparisonRow("Dynamics"),
            "score": ComparisonRow("Score"),
        }
        for row, comparison_row in enumerate(self.comparison_rows.values(), start=1):
            before_after_layout.addWidget(comparison_row, row, 0, 1, 5)
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
        set_lucide_icon(self.history_button, "history")
        self.history_button.clicked.connect(self._toggle_history)

        layout.addLayout(listening_row)
        layout.addWidget(self.playback_waveform)
        layout.addWidget(self.playback_label)
        layout.addWidget(self.before_after_panel)
        layout.addWidget(self.history_button)
        layout.addWidget(self.history_table)
        return self.listening_box

    def _build_results(self) -> QGroupBox:
        self.results_box = QGroupBox("Choose a version")
        layout = QVBoxLayout(self.results_box)

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
        set_lucide_icon(self.details_button, "list")
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
        return self.results_box

    def _build_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu("File")
        self.choose_input_action = QAction("Choose audio file", self)
        self.choose_input_action.triggered.connect(self._browse_input_file)
        self.file_menu.addAction(self.choose_input_action)

        self.choose_output_action = QAction("Choose output folder", self)
        self.choose_output_action.triggered.connect(self._browse_output_dir)
        self.file_menu.addAction(self.choose_output_action)

        self.file_menu.addSeparator()
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)

        self.settings_menu = self.menuBar().addMenu("Settings")
        self.language_menu = self.settings_menu.addMenu("Language")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.language_actions: dict[str, QAction] = {}
        for code, label in LANGUAGES.items():
            action = QAction(label, self, checkable=True)
            action.setData(code)
            action.setChecked(code == self.language)
            action.triggered.connect(lambda _checked=False, language=code: self._set_language(language))
            self.language_group.addAction(action)
            self.language_menu.addAction(action)
            self.language_actions[code] = action

        self.connect_menu = self.menuBar().addMenu("Connect")
        self.maker_action = QAction("Meet the maker", self)
        self.maker_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://mathieuluyten.be/")))
        self.connect_menu.addAction(self.maker_action)

    def _t(self, key: str, **kwargs: object) -> str:
        text = UI_TEXT.get(self.language, UI_TEXT["en"]).get(key, UI_TEXT["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def _set_language(self, language: str) -> None:
        if language not in UI_TEXT or language == self.language:
            return
        self.language = language
        self.settings.setValue("language", language)
        self._apply_language_texts()
        self._update_actions()

    def _set_combo_text(self, combo: QComboBox, data: object, text: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == data:
                combo.setItemText(index, text)
                return

    def _apply_language_texts(self) -> None:
        self.setWindowTitle(f"{APP_TITLE} - {APP_DISPLAY_VERSION}")
        self.version_label.setText(f"Beta {APP_DISPLAY_VERSION}")
        self.file_menu.setTitle(self._t("menu_file"))
        self.settings_menu.setTitle(self._t("menu_settings"))
        self.language_menu.setTitle(self._t("menu_language"))
        self.connect_menu.setTitle(self._t("menu_connect"))
        self.choose_input_action.setText(self._t("menu_choose_audio"))
        self.choose_output_action.setText(self._t("menu_choose_output"))
        self.quit_action.setText(self._t("menu_quit"))
        self.maker_action.setText(self._t("menu_maker"))

        self.workflow_tabs.setTabText(0, self._t("tab_source"))
        self.workflow_tabs.setTabText(1, self._t("tab_versions"))
        self.workflow_tabs.setTabText(2, self._t("tab_listen"))
        self.session_box.setTitle(self._t("session"))
        self.hero_title.setText(self._t("hero_title"))
        self.hero_subtitle.setText(self._t("hero_subtitle", version=APP_DISPLAY_VERSION))
        self.browse_button.setText(self._t("choose_file"))

        self.analyze_box.setTitle(self._t("analyze_box"))
        self.selected_source_label.setText(self._t("source_selected"))
        self.change_source_button.setText(self._t("change_source"))
        self.analyze_button.setText(self._t("analyzed") if self.current_analysis else self._t("analyze_source"))
        self.processing_label.setText(self._t("processing_time"))
        self.processing_fast_label.setText(self._t("processing_fast"))
        self.processing_balanced_label.setText(self._t("processing_balanced"))
        self.processing_best_label.setText(self._t("processing_best"))
        self._update_processing_hint()
        if not self.input_edit.text().strip():
            self.status_label.setText(self._t("step_choose_source"))

        self.render_box.setTitle(self._t("render_box"))
        if self.current_analysis is None:
            self.render_context_label.setText(self._t("render_context_ready"))
        self.source_review_button.setText(
            self._t("hide_source") if not self.source_box.isHidden() else self._t("review_source")
        )
        self.config_edit.setPlaceholderText(self._t("optional_config"))
        self._set_combo_text(self.mode_combo, OptimizationMode.SAFE, self._t("mode_safe"))
        self._set_combo_text(self.mode_combo, OptimizationMode.BALANCED, self._t("mode_balanced"))
        self._set_combo_text(self.mode_combo, OptimizationMode.LOUDER, self._t("mode_louder"))
        self._set_combo_text(self.destination_combo, "streaming_prudent", self._t("destination_streaming"))
        self._set_combo_text(self.destination_combo, "club_loud", self._t("destination_soundcloud"))
        self._set_combo_text(self.destination_combo, "archive_safe", self._t("destination_archive"))
        self.strict_tp_checkbox.setText(self._t("tp_strict"))
        self._set_combo_text(self.quick_target_combo, None, self._t("target_auto"))
        self._set_combo_text(self.quick_target_combo, -14.0, self._t("target_streaming"))
        self._set_combo_text(self.quick_target_combo, -10.5, self._t("target_soundcloud"))
        self._set_combo_text(self.quick_target_combo, -9.0, self._t("target_club"))
        self._set_combo_text(self.quick_target_combo, -8.0, self._t("target_hard"))
        self._set_combo_text(self.quick_target_combo, -7.0, self._t("target_extreme"))
        self.target_lufs_spin.setToolTip(self._t("target_tooltip"))
        self.max_loudness_checkbox.setText(self._t("max_loudness"))
        self.max_loudness_checkbox.setToolTip(self._t("max_loudness_tip"))
        self.max_loudness_warning.setText(self._t("max_loudness_warning"))
        self.listen_check_button.setText(self._t("ab_check"))
        self.listen_check_hint.setText(self._t("ab_unlock"))
        self.output_button.setText(self._t("choose_output"))
        self.config_button.setText(self._t("load_config"))
        self.template_button.setText(self._t("create_template"))
        self.advanced_button.setText(self._t("hide_advanced") if self.advanced_options_visible else self._t("show_advanced"))
        self.optimize_button.setText(self._t("create_versions"))
        self.export_button.setText(self._t("export_final"))
        if self._thread is None:
            self.render_status_label.setText(self._t("ready_render"))
        self.cancel_render_button.setText(self._t("cancel"))
        self.mode_label.setText(self._t("master_goal"))
        self.quick_target_label.setText(self._t("quick_target"))
        self.target_lufs_label.setText(self._t("level_target"))
        self.destination_label.setText(self._t("usage"))
        self.output_label.setText(self._t("output_folder"))
        self.config_label.setText(self._t("config_file"))

        self.source_box.setTitle(self._t("source_analysis"))
        if self.current_analysis is None:
            self.metric_labels["profile"].setText(self._t("not_analyzed"))
            self.metric_labels["diagnostics"].setText(self._t("diagnostics_pending"))
        self.metric_labels["acoustic_note"].setText(self._t("acoustic_note"))
        self.source_metric_titles["profile"].setText(self._t("profile"))
        self.source_metric_titles["true_peak"].setText(self._t("true_peak"))
        self.source_metric_titles["lra"].setText(self._t("dynamics"))
        self.source_details_button.setText(
            self._t("hide_waveform") if not self.source_details_panel.isHidden() else self._t("show_waveform")
        )
        if self.waveform_label.pixmap() is None or self.waveform_label.pixmap().isNull():
            self.waveform_label.setText(self._t("waveform_pending"))

        self.best_box.setTitle(self._t("best_box"))
        if self.current_session is None:
            self.best_labels["name"].setText(self._t("no_candidate_yet"))
            self.best_labels["reasons"].setText(self._t("candidate_pending"))
        self.listen_selected_button.setText(self._t("listen_selected"))
        self.save_note_button.setText(self._t("save_note"))
        for key, label in self.best_row_labels.items():
            label.setText(self._t(key))

        self.listening_box.setTitle(self._t("compare_export"))
        self.play_source_button.setText(self._t("play_source"))
        self.play_candidate_button.setText(self._t("play_candidate"))
        self.stop_audio_button.setText(self._t("stop"))
        self.new_analysis_button.setText(self._t("new_analysis"))
        if self.current_playback is None:
            self.playback_label.setText(self._t("playback_pending"))
        for key, label in self.comparison_header_labels.items():
            label.setText(self._t(key))
        self.comparison_rows["loudness"].metric_label.setText(self._t("loudness"))
        self.comparison_rows["peak"].metric_label.setText(self._t("true_peak"))
        self.comparison_rows["lra"].metric_label.setText(self._t("dynamics"))
        self.comparison_rows["score"].metric_label.setText(self._t("score"))
        self.history_button.setText(self._t("hide_history") if not self.history_table.isHidden() else self._t("show_history"))
        self.history_table.setHorizontalHeaderLabels(["Date (UTC)", "Session", self._t("master_goal"), self._t("best_box"), self._t("tab_source")])

        self.results_box.setTitle(self._t("choose_version"))
        self.results_table.setHorizontalHeaderLabels(
            [self._t("choice"), self._t("version"), self._t("score"), "LUFS", "TP", "LRA"]
        )
        self.details_button.setText(self._t("hide_scoring") if self.details_panel.isVisible() else self._t("show_scoring"))
        self.details_panel.setPlaceholderText(self._t("details_placeholder"))
        self._apply_quick_target()
        for action_code, action in self.language_actions.items():
            action.setChecked(action_code == self.language)
        self._schedule_window_fit()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #0b0b0f;
                color: #f7f3ea;
                font-size: 13px;
            }
            QMainWindow, QMenuBar, QMenu {
                background: #0b0b0f;
                color: #e8dfd0;
            }
            QMenuBar {
                border-bottom: 1px solid #202026;
                padding: 4px 6px;
            }
            QMenuBar::item:selected, QMenu::item:selected {
                background: #17171d;
                border-radius: 8px;
            }
            #brandHeader {
                background: transparent;
            }
            #brandLogo {
                background: transparent;
            }
            #brandName {
                background: transparent;
                color: #f7f3ea;
                font-family: "Space Grotesk", "Segoe UI Variable Display", "Segoe UI", sans-serif;
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 0;
            }
            #brandVersion {
                background: #17171d;
                border: 1px solid #e5b94d;
                border-radius: 8px;
                color: #e5b94d;
                font-weight: 700;
                padding: 5px 9px;
            }
            QTabWidget::pane {
                border: 0;
                padding-top: 14px;
            }
            QTabBar::tab {
                background: #121219;
                color: #a6a0aa;
                border: 1px solid #2b2b33;
                border-radius: 12px;
                margin-right: 10px;
                padding: 12px 24px;
                min-width: 136px;
            }
            QTabBar::tab:selected {
                background: #0fb7a7;
                border-color: #e5b94d;
                color: #071111;
                font-weight: 700;
            }
            QTabBar::tab:disabled {
                color: #52525b;
            }
            QGroupBox {
                background: #121219;
                border: 1px solid #2b2b33;
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
                color: #e5b94d;
                background: #0b0b0f;
                border-radius: 999px;
            }
            #dropFrame {
                border: 1px solid #4de0d2;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121219, stop:1 #14201f);
            }
            #heroTitle {
                font-size: 24px;
                font-weight: 700;
                color: #f7f3ea;
                font-family: "Space Grotesk", "Segoe UI Variable Display", "Segoe UI", sans-serif;
            }
            #heroIcon {
                background: transparent;
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
            #formLabel {
                color: #f7f3ea;
                background: transparent;
                font-weight: 600;
                padding: 9px 0;
                min-width: 86px;
            }
            #bestValue {
                color: #f7f3ea;
                background: #09090b;
                border-radius: 8px;
                padding: 10px 12px;
                line-height: 1.35;
                min-height: 20px;
            }
            #sourceDetailsPanel {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #0f0f11;
                padding: 10px;
            }
            #sourceDetailValue {
                color: #f7f3ea;
                background: #09090b;
                border-radius: 8px;
                padding: 10px 12px;
                line-height: 1.35;
            }
            #targetHint {
                color: #a1a1aa;
                padding: 4px 2px;
            }
            #sliderScaleLabel {
                color: #a1a1aa;
                font-size: 11px;
                font-weight: 600;
            }
            #statusHint {
                color: #a1a1aa;
                background: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 9px 12px;
            }
            #warningHint {
                color: #e5b94d;
                background: #18130a;
                border: 0;
                border-left: 3px solid #e5b94d;
                border-radius: 8px;
                padding: 8px 12px;
            }
            #renderStatus {
                color: #e4e4e7;
                background: #09090b;
                border: 1px solid #18181b;
                border-radius: 8px;
                padding: 8px 10px;
            }
            #workPulse {
                background: #09090b;
                border: 1px solid #2b2b33;
                border-radius: 8px;
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
            #comparisonRow {
                border: 1px solid #27272a;
                border-radius: 12px;
                background: #18181b;
                padding: 10px;
            }
            #comparisonMetric {
                color: #5eead4;
                font-weight: 700;
            }
            #comparisonColumnTitle {
                color: #a1a1aa;
                font-weight: 700;
                padding: 4px 8px;
            }
            #comparisonValue {
                background: #09090b;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            #comparisonChange {
                color: #e5b94d;
                background: #09090b;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            #comparisonChange[tone="good"] {
                color: #5eead4;
            }
            #comparisonChange[tone="warn"] {
                color: #e5b94d;
            }
            #comparisonVerdict {
                color: #d4d4d8;
                padding: 6px 0;
            }
            QPushButton {
                background: #14b8a6;
                border: 0;
                border-radius: 8px;
                padding: 10px 14px;
                color: #042f2e;
                font-weight: 700;
                min-height: 40px;
            }
            QPushButton:hover {
                background: #2dd4bf;
            }
            QPushButton:disabled {
                background: #27272a;
                color: #71717a;
            }
            #primaryAction {
                background: #e5b94d;
                color: #18181b;
            }
            #primaryAction:hover {
                background: #f0c96a;
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
                min-height: 40px;
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
                min-height: 34px;
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
            QSlider {
                min-height: 30px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #27272a;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #14b8a6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e5b94d;
                border: 2px solid #0b0b0f;
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:disabled {
                background: #71717a;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QSpinBox, QDoubleSpinBox {
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 8px;
                background: #09090b;
                selection-background-color: #14b8a6;
                min-height: 38px;
            }
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #e5b94d;
            }
            QComboBox {
                padding-right: 32px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #27272a;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background: #121219;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #e5b94d;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #121219;
                color: #f7f3ea;
                border: 1px solid #3f3f46;
                selection-background-color: #14b8a6;
                selection-color: #071111;
                padding: 6px;
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
            self._t("select_source_dialog"),
            str(Path.home()),
            "Audio files (*.wav *.flac)",
        )
        if file_path:
            self._set_input_path(file_path)

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            self._t("select_output_dialog"),
            self.output_edit.text() or str(Path.cwd()),
        )
        if folder:
            self.output_edit.setText(folder)

    def _browse_config_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("select_config_dialog"),
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
            self._t("create_config_dialog"),
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
            self._t("config_created_title"),
            self._t("config_created_body", path=destination),
        )

    def _toggle_advanced_options(self) -> None:
        self.advanced_options_visible = not self.advanced_options_visible
        self.advanced_button.setText(
            self._t("hide_advanced") if self.advanced_options_visible else self._t("show_advanced")
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
            self.new_analysis_button.setVisible(False)
            self.source_details_panel.setVisible(False)
            self.source_details_button.setText(self._t("show_waveform"))
            self.source_box.setVisible(False)
            self.source_review_button.setText(self._t("review_source"))
        self.status_label.setText(self._t("step_analyze_next"))
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
            self._show_error(self._t("choose_audio_first"))
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
            processing_quality=self.processing_slider.value(),
            source_analysis=source_analysis,
        )

    def _update_processing_hint(self, *_args: object) -> None:
        hints = {
            0: self._t("processing_hint_fast"),
            1: self._t("processing_hint_balanced"),
            2: self._t("processing_hint_best"),
        }
        self.processing_hint_label.setText(hints.get(self.processing_slider.value(), hints[1]))

    def _apply_quick_target(self, *_args: object) -> None:
        target = self.quick_target_combo.currentData()
        if isinstance(target, float):
            self.target_lufs_spin.setValue(target)
        elif self.current_analysis is not None:
            recommended_lufs, _ = self._recommended_target_lufs(self.current_analysis)
            self.target_lufs_spin.setValue(recommended_lufs)

        hints = {
            None: self._t("hint_auto"),
            -14.0: self._t("hint_streaming"),
            -10.5: self._t("hint_soundcloud"),
            -9.0: self._t("hint_club"),
            -8.0: self._t("hint_hard"),
            -7.0: self._t("hint_extreme"),
        }
        self.target_hint_label.setText(hints.get(target, ""))

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
        self._progress_started_at = time.monotonic()
        self._last_progress_message = None
        self._last_progress_percent = 0
        self._progress_timer.start()
        self.current_output_dir = Path(request.output_dir)
        if request.kind == "optimize":
            self.source_box.setVisible(False)
            self.source_review_button.setText("Review source analysis")
            self.render_progress_bar.setValue(0)
            self.render_progress_bar.setVisible(True)
            self.render_progress_bar.start_animation()
            self.render_work_pulse.start()
            self.render_status_label.setText(self._t("preparing_render"))
            self.cancel_render_button.setVisible(True)
            self.cancel_render_button.setEnabled(True)
            self._position_render_overlay()
            self.render_overlay.start("Creating versions...")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.status_label.setText(self._t("preparing_analysis"))
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

    def _cancel_active_worker(self) -> None:
        if self._worker is None:
            return
        self.cancel_render_button.setEnabled(False)
        self.render_status_label.setText(self._t("cancelling"))
        self.render_overlay.set_message("Cancelling...")
        self._worker.cancel()
        self._sync_button_cursors()

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
        self._progress_timer.stop()
        self._progress_started_at = None
        self._last_progress_message = None
        self._last_progress_percent = 0
        self._set_busy(False)
        if finished_kind == "optimize":
            self.render_progress_bar.stop_animation()
            self.render_work_pulse.stop()
            self.render_progress_bar.setVisible(False)
            self.cancel_render_button.setVisible(False)
            self.render_overlay.stop()
        else:
            self.progress_bar.setVisible(False)
        self._update_actions()

    def _on_progress(self, message: str, percent: int) -> None:
        message = self._display_progress_message(message)
        self._last_progress_message = message
        self._last_progress_percent = percent
        self._refresh_elapsed_progress()

    def _refresh_elapsed_progress(self) -> None:
        if self._progress_started_at is None:
            return
        message = self._last_progress_message
        percent = self._last_progress_percent
        if message is None:
            message = self._t("preparing_render") if self._active_worker_kind == "optimize" else self._t("preparing_analysis")
        if self._active_worker_kind == "optimize":
            self.render_status_label.setText(self._rich_progress_text(message, percent, animated=True))
            self.render_progress_bar.setValue(percent)
            self.render_overlay.set_message(self._plain_progress_text(message, percent))
            return
        self.status_label.setText(self._rich_progress_text(message, percent))
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
                self._t("auto_recommendation", lufs=recommended_lufs, reason=lufs_reason)
            )
            self.source_box.setVisible(False)
            self.source_review_button.setText(self._t("review_source"))
            self._update_waveform_preview(result.source_path)
            self._clear_results()
            self.status_label.setText(
                self._t("step2_complete", lufs=recommended_lufs, reason=lufs_reason)
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
            self.status_label.setText(self._t("step3_complete"))
            self.render_status_label.setText(self._t("render_complete"))
            self.render_progress_bar.setValue(100)
            self.progress_bar.setValue(100)
            self.workflow_tabs.setCurrentIndex(1)

    def _on_worker_failed(self, message: str) -> None:
        if "operation_cancelled" in message:
            if self._active_worker_kind == "optimize":
                self.render_status_label.setText(self._t("render_cancelled"))
                self.render_progress_bar.setValue(0)
                self.render_overlay.set_message(self._t("cancelled"))
            else:
                self.status_label.setText(self._t("analysis_cancelled"))
                self.progress_bar.setValue(0)
            return
        if self._active_worker_kind == "optimize":
            self.render_progress_bar.stop_animation()
            self.render_work_pulse.stop()
            self.render_status_label.setText(self._t("render_failed"))
            self.render_progress_bar.setValue(0)
            self.render_overlay.set_message(self._t("render_failed"))
        else:
            self.status_label.setText(self._t("task_failed"))
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
            f"Use it when: {self._human_preset_description(selected.preset.name, getattr(selected.preset, 'description', ''))}",
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
        if self.current_session and getattr(self.current_session, "best_candidate", None) is selected:
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
        if "_target_" in candidate.preset.name:
            return "Careful comparison"
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
        if "_target_" in candidate.preset.name:
            name = f"{name} - Careful comparison"
        if candidate.preset.name.endswith("_optimaster"):
            name = f"{name} - Clean fallback"
        if rank is None:
            return name
        return f"Version {rank}: {name}"

    def _base_preset_name(self, preset_name: str) -> str:
        name = preset_name.removesuffix("_optimaster")
        if "_loudest_" in name:
            name = name.split("_loudest_", 1)[0]
        if "_target_" in name:
            name = name.split("_target_", 1)[0]
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
                version_label = ""
                if ":" in preset_name:
                    version_token, preset_name = preset_name.split(":", 1)
                    version_token = version_token.strip()
                    if "/" in version_token:
                        version_label = f"V{version_token} - "
                return f"{version_label}{prefix}{self._human_preset_name(preset_name.strip())}"
        return message

    def _animated_status_text(self, message: str) -> str:
        dots = "." * ((self.render_progress_bar._phase // 250) % 4)
        return f"{message}{dots}"

    def _progress_parts(self, message: str, percent: int, animated: bool = False) -> tuple[str | None, str, str]:
        version = None
        title = message
        if message.startswith("V") and " - " in message:
            version, title = message.split(" - ", 1)
        if animated:
            title = self._animated_status_text(title)
        if percent <= 0:
            meta = "Starting"
        elif percent >= 100:
            meta = "100% complete"
        else:
            meta_parts = [f"{percent}% complete"]
            elapsed = self._elapsed_work_time()
            if elapsed:
                meta_parts.append(f"{elapsed} elapsed")
            meta = " · ".join(meta_parts)
        return version, title, meta

    def _plain_progress_text(self, message: str, percent: int) -> str:
        version, title, meta = self._progress_parts(message, percent)
        detail = f"{version} · {meta}" if version else meta
        return f"{title}\n{detail}"

    def _rich_progress_text(self, message: str, percent: int, animated: bool = False) -> str:
        version, title, meta = self._progress_parts(message, percent, animated=animated)
        detail = f"{version} · {meta}" if version else meta
        return (
            '<div style="line-height:1.25;">'
            f'<span style="color:#f7f3ea;font-size:14px;font-weight:800;">{escape(title)}</span><br>'
            f'<span style="color:#a1a1aa;font-size:12px;font-weight:600;">{escape(detail)}</span>'
            "</div>"
        )

    def _progress_text(self, message: str, percent: int) -> str:
        if percent <= 0:
            return f"{message} - starting"
        if percent >= 100:
            return f"{message} - 100%"
        elapsed = self._elapsed_work_time()
        if elapsed:
            return f"{message} - {percent}% - {elapsed} elapsed"
        return f"{message} - {percent}%"

    def _elapsed_work_time(self) -> str | None:
        if self._progress_started_at is None:
            return None
        elapsed = int(max(time.monotonic() - self._progress_started_at, 0.0))
        if elapsed < 3:
            return None
        minutes, seconds = divmod(elapsed, 60)
        if minutes == 0:
            return f"{seconds}s"
        return f"{minutes}m {seconds:02d}s"

    def _candidate_rank(self, candidate: CandidateResult) -> int | None:
        if self.current_session is None:
            return None
        for idx, session_candidate in enumerate(self.current_session.candidates, start=1):
            if session_candidate is candidate:
                return idx
        return None

    def _clear_before_after(self) -> None:
        self.comparison_rows["loudness"].set_values("--", "--", "--", "Select a version to compare loudness.", None)
        self.comparison_rows["peak"].set_values("--", "--", "--", "Peak safety appears here.", None)
        self.comparison_rows["lra"].set_values("--", "--", "--", "Dynamics change appears here.", None)
        self.comparison_rows["score"].set_values("--", "--", "--", "Technical score appears here.", None)

    def _populate_before_after(self, candidate: CandidateResult) -> None:
        source = candidate.source_metrics
        output = candidate.output_metrics
        loudness_delta = output.integrated_lufs - source.integrated_lufs
        peak_delta = output.true_peak_dbtp - source.true_peak_dbtp
        lra_delta = output.lra_lu - source.lra_lu

        self.comparison_rows["loudness"].set_values(
            format_metric(source.integrated_lufs, "LUFS"),
            format_metric(output.integrated_lufs, "LUFS"),
            f"{loudness_delta:+.1f} LUFS",
            "Louder" if loudness_delta > 0 else "Quieter" if loudness_delta < 0 else "Same loudness",
            abs(loudness_delta) <= 3.0,
        )
        self.comparison_rows["peak"].set_values(
            format_metric(source.true_peak_dbtp, "dBTP"),
            format_metric(output.true_peak_dbtp, "dBTP"),
            f"{peak_delta:+.1f} dB",
            "More headroom" if peak_delta < 0 else "Hotter peak" if peak_delta > 0 else "Same peak",
            output.true_peak_dbtp <= -1.0,
        )
        self.comparison_rows["lra"].set_values(
            format_metric(source.lra_lu, "LU"),
            format_metric(output.lra_lu, "LU"),
            f"{lra_delta:+.1f} LU",
            "More dynamic" if lra_delta > 0 else "Tighter" if lra_delta < 0 else "Dynamics preserved",
            lra_delta >= -2.0,
        )
        self.comparison_rows["score"].set_values(
            "--",
            f"{candidate.score:.1f}",
            "Best compromise" if self._candidate_rank(candidate) == 1 else "Alternative",
            "Technical compromise between loudness, safety, and dynamics.",
            candidate.score >= 70,
        )

    def _delta_magnitude(self, delta: float, full_scale: float) -> int:
        return int(round(min(abs(delta) / full_scale, 1.0) * 100))

    def _export_selected_candidate(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            self._show_error("Select a rendered candidate before exporting.")
            return
        if not self._candidate_in_current_session(candidate):
            self._show_error("This candidate is no longer part of the current session. Create versions again.")
            return
        if not candidate.output_path.exists():
            self._show_error(f"Cannot export missing rendered file:\n{candidate.output_path}")
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export final version",
            str(self._default_export_path(candidate)),
            "WAV files (*.wav);;FLAC files (*.flac);;All files (*.*)",
        )
        if not destination:
            return

        try:
            shutil.copy2(candidate.output_path, destination)
        except OSError as exc:
            self._show_error(f"Export failed:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Copied {self._candidate_version_label(candidate)} to:\n{destination}",
        )
        self.playback_label.setText("Export complete. Start a new analysis when you are ready.")
        self.new_analysis_button.setVisible(True)
        self.new_analysis_button.setEnabled(True)
        self._schedule_window_fit()

    def _candidate_in_current_session(self, candidate: CandidateResult) -> bool:
        return bool(
            self.current_session
            and any(session_candidate is candidate for session_candidate in self.current_session.candidates)
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

    def _start_new_analysis(self) -> None:
        self._stop_playback()
        self.current_analysis = None
        self.current_session = None
        self.current_output_dir = None
        self.waveform_preview_path = None
        self.input_edit.clear()
        self.output_edit.setText(str(Path.cwd() / "renders"))
        self.config_edit.clear()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.render_progress_bar.stop_animation()
        self.render_work_pulse.stop()
        self.render_progress_bar.setValue(0)
        self.render_progress_bar.setVisible(False)
        self.render_status_label.setText("Ready to render candidate versions.")
        self.render_overlay.stop()
        self.status_label.setText("Choose a source file to begin.")
        self.source_box.setVisible(False)
        self.source_details_panel.setVisible(False)
        self.source_details_button.setText("Show waveform and diagnostics")
        self.source_review_button.setText("Review source analysis")
        self.metric_labels["profile"].setText("Not analyzed")
        self.metric_labels["integrated"].setText("--")
        self.metric_labels["true_peak"].setText("--")
        self.metric_labels["lra"].setText("--")
        self.metric_labels["diagnostics"].setText("Analyze a source to see diagnostics.")
        self.waveform_label.setPixmap(QPixmap())
        self.waveform_label.setText("Waveform preview appears after file selection.")
        self.results_table.setRowCount(0)
        self.details_panel.clear()
        self.details_panel.setVisible(False)
        self.details_button.setText("Show scoring details")
        self._clear_before_after()
        self._populate_best_candidate(None)
        self.new_analysis_button.setVisible(False)
        self.workflow_tabs.setCurrentIndex(0)
        self._update_actions()

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
        self.history_button.setText(self._t("hide_history") if visible else self._t("show_history"))

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
        self.workflow_tabs.tabBar().setDisabled(busy)
        for widget in [*self.mastering_widgets, *self.advanced_widgets]:
            widget.setDisabled(busy)
        for widget in [
            self.analyze_button,
            self.processing_slider,
            self.export_button,
            self.new_analysis_button,
            self.play_source_button,
            self.play_candidate_button,
            self.listen_selected_button,
            self.save_note_button,
            self.listen_check_button,
            self.change_source_button,
            self.input_edit,
        ]:
            widget.setDisabled(busy)
        self._sync_button_cursors()

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
            self.selected_source_label.setText(self._t("selected_source_next", name=input_path.name))
        if has_analysis:
            self.render_context_label.setText(self._render_story_text())
        self.analyze_button.setEnabled(has_input and not has_analysis and self._thread is None)
        self.analyze_button.setText(self._t("analyzed") if has_analysis else self._t("analyze_source"))
        self.optimize_button.setEnabled(has_analysis and self._thread is None)
        self.export_button.setEnabled(self._thread is None and has_candidate)
        self.new_analysis_button.setEnabled(self._thread is None)
        self.play_candidate_button.setEnabled(self._thread is None and has_candidate)
        self.listen_selected_button.setEnabled(self._thread is None and has_candidate)
        self.save_note_button.setEnabled(self._thread is None and has_candidate)
        can_choose_target = self._thread is None and not self.max_loudness_checkbox.isChecked()
        self.quick_target_combo.setEnabled(can_choose_target)
        self.target_lufs_spin.setEnabled(can_choose_target)
        self.max_loudness_warning.setVisible(has_analysis and self.max_loudness_checkbox.isChecked())
        show_listen_check = has_analysis and self.max_loudness_checkbox.isChecked()
        can_listen_check = self._thread is None and has_candidates and has_candidate
        self.listen_check_button.setVisible(show_listen_check and can_listen_check)
        self.listen_check_button.setEnabled(can_listen_check)
        self.listen_check_hint.setVisible(show_listen_check and not can_listen_check)
        self.workflow_tabs.setTabEnabled(0, True)
        self.workflow_tabs.setTabEnabled(1, has_candidates)
        self.workflow_tabs.setTabEnabled(2, has_candidate)
        self._sync_control_visibility(has_input, has_analysis)
        self._sync_button_cursors()
        self._schedule_window_fit()

    def _sync_control_visibility(self, has_input: bool, has_analysis: bool) -> None:
        self.session_box.setVisible(not has_input)
        self.analyze_box.setVisible(has_input and not has_analysis)
        if not has_analysis:
            self.source_box.setVisible(False)
            if hasattr(self, "source_review_button"):
                self.source_review_button.setText(self._t("review_source"))
        self.render_box.setVisible(has_analysis)
        for widget in self.mastering_widgets:
            widget.setVisible(has_analysis)
        for widget in self.advanced_widgets:
            widget.setVisible(self.advanced_options_visible)
        if has_analysis:
            show_listen_check = self.max_loudness_checkbox.isChecked()
            has_candidate = self._selected_candidate() is not None
            has_candidates = bool(self.current_session and self.current_session.candidates)
            can_listen_check = self._thread is None and has_candidates and has_candidate
            self.max_loudness_warning.setVisible(show_listen_check)
            self.listen_check_button.setVisible(show_listen_check and can_listen_check)
            self.listen_check_hint.setVisible(show_listen_check and not can_listen_check)

    def _sync_button_cursors(self) -> None:
        for button in self.findChildren(QPushButton):
            cursor = Qt.CursorShape.PointingHandCursor if button.isEnabled() and button.isVisible() else Qt.CursorShape.ArrowCursor
            button.setCursor(cursor)

    def _schedule_window_fit(self) -> None:
        QTimer.singleShot(0, self._fit_window_to_content)

    def _fit_window_to_content(self) -> None:
        if self.isMaximized() or self.isFullScreen():
            return

        target_height = self._target_window_height()
        if abs(self.height() - target_height) > 28:
            self.resize(self.width(), target_height)

    def _target_window_height(self) -> int:
        current_index = self.workflow_tabs.currentIndex()
        has_input = bool(self.input_edit.text().strip())
        has_analysis = (
            self.current_analysis is not None
            and has_input
            and self.current_analysis.source_path == Path(self.input_edit.text()).resolve()
        )
        if current_index == 0:
            if not has_input:
                return 640
            if not has_analysis:
                return 640
            height = 760
            if not self.source_box.isHidden():
                height += 190
            if not self.source_details_panel.isHidden():
                height += 170
            if self.advanced_options_visible:
                height += 95
            return min(height, 940)
        if current_index == 1:
            return 900 if self.details_panel.isVisible() else 780
        return 820 if not self.history_table.isHidden() else 740

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._position_render_overlay()

    def _position_render_overlay(self) -> None:
        if hasattr(self, "render_overlay"):
            self.render_overlay.setGeometry(self.render_box.rect())
            self.render_overlay.raise_()

    def _render_story_text(self) -> str:
        if self.current_analysis is None:
            return self._t("source_ready_story")
        metrics = self.current_analysis.metrics
        source_name = self.current_analysis.source_path.name
        return self._t(
            "analyzed_story",
            name=source_name,
            lufs=metrics.integrated_lufs,
            peak=metrics.true_peak_dbtp,
            lra=metrics.lra_lu,
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
