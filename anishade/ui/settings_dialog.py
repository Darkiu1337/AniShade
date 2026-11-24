"""Preferences dialog: language, ReShade/NW.js/URM cache management, and default choices."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import anime4k, i18n, nwjs, paths, renpy, reshade, winapi
from ..i18n import tr
from ..store import Store
from .theme import MUTED
from .widgets import Card, Divider
from .workers import run_task


class SettingsDialog(QDialog):
    def __init__(self, store: Store, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.settings = store.settings
        self.task = None
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(650)
        self.resize(670, 720)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(2, 2, 8, 2)
        body.setSpacing(12)
        body.addWidget(self._build_general_card())
        body.addWidget(self._build_reshade_card())
        body.addWidget(self._build_nwjs_card())
        body.addWidget(self._build_urm_card())
        body.addWidget(self._build_defaults_card())
        body.addWidget(self._build_about())
        body.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.Save).setObjectName("primary")
        buttons.button(QDialogButtonBox.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_cache_info()
        self._refresh_nwjs_cache_info()
        self._refresh_urm_cache_info()

    # -- cards -----------------------------------------------------------
    def _build_general_card(self) -> Card:
        card = Card(tr("settings.general_card"))
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(tr("settings.language"))
        label.setObjectName("muted")
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(260)
        for code, display in i18n.SUPPORTED_LANGUAGES:
            self.language_combo.addItem(display, code)
        index = self.language_combo.findData(i18n.normalize_language(self.settings.language))
        self.language_combo.setCurrentIndex(max(0, index))
        row.addWidget(label)
        row.addWidget(self.language_combo, 1)
        card.add_layout(row)

        hint = QLabel(tr("settings.language_hint"))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 8.5pt;")
        card.add(hint)
        return card

    def _build_reshade_card(self) -> Card:
        card = Card(tr("settings.reshade_card"))
        self.cache_label = QLabel()
        self.cache_label.setObjectName("muted")
        self.cache_label.setWordWrap(True)
        card.add(self.cache_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(tr("settings.version_used"))
        label.setObjectName("muted")
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(260)
        row.addWidget(label)
        row.addWidget(self.version_combo, 1)
        card.add_layout(row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.download_button = QPushButton(tr("settings.download_now"))
        self.download_button.setObjectName("primary")
        self.download_button.clicked.connect(self._download)
        self.prune_button = QPushButton(tr("settings.prune_old"))
        self.prune_button.clicked.connect(self._prune)
        self.open_cache_button = QPushButton(tr("settings.open_cache"))
        self.open_cache_button.setObjectName("ghost")
        self.open_cache_button.clicked.connect(lambda: winapi.open_folder(paths.RESHADE_CACHE_DIR))
        actions.addWidget(self.download_button)
        actions.addWidget(self.prune_button)
        actions.addStretch(1)
        actions.addWidget(self.open_cache_button)
        card.add_layout(actions)

        self.download_status = QLabel("")
        self.download_status.setObjectName("muted")
        self.download_status.setWordWrap(True)
        self.download_status.hide()
        card.add(self.download_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        card.add(self.progress)
        return card

    def _build_nwjs_card(self) -> Card:
        card = Card(tr("settings.nwjs_card"))
        self.nwjs_cache_label = QLabel()
        self.nwjs_cache_label.setObjectName("muted")
        self.nwjs_cache_label.setWordWrap(True)
        card.add(self.nwjs_cache_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(tr("settings.version_used"))
        label.setObjectName("muted")
        self.nwjs_version_combo = QComboBox()
        self.nwjs_version_combo.setMinimumWidth(260)
        row.addWidget(label)
        row.addWidget(self.nwjs_version_combo, 1)
        card.add_layout(row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.nwjs_download_button = QPushButton(tr("settings.download_now"))
        self.nwjs_download_button.setObjectName("primary")
        self.nwjs_download_button.clicked.connect(self._download_nwjs)
        self.nwjs_prune_button = QPushButton(tr("settings.prune_old"))
        self.nwjs_prune_button.clicked.connect(self._prune_nwjs)
        self.nwjs_open_cache_button = QPushButton(tr("settings.open_cache"))
        self.nwjs_open_cache_button.setObjectName("ghost")
        self.nwjs_open_cache_button.clicked.connect(lambda: winapi.open_folder(paths.NWJS_CACHE_DIR))
        actions.addWidget(self.nwjs_download_button)
        actions.addWidget(self.nwjs_prune_button)
        actions.addStretch(1)
        actions.addWidget(self.nwjs_open_cache_button)
        card.add_layout(actions)

        self.nwjs_status = QLabel("")
        self.nwjs_status.setObjectName("muted")
        self.nwjs_status.setWordWrap(True)
        self.nwjs_status.hide()
        card.add(self.nwjs_status)

        self.nwjs_progress = QProgressBar()
        self.nwjs_progress.setRange(0, 100)
        self.nwjs_progress.setValue(0)
        self.nwjs_progress.hide()
        card.add(self.nwjs_progress)
        return card

    def _build_urm_card(self) -> Card:
        card = Card(tr("settings.urm_card"))
        self.urm_cache_label = QLabel()
        self.urm_cache_label.setObjectName("muted")
        self.urm_cache_label.setWordWrap(True)
        card.add(self.urm_cache_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(tr("settings.version_used"))
        label.setObjectName("muted")
        self.urm_version_combo = QComboBox()
        self.urm_version_combo.setMinimumWidth(260)
        row.addWidget(label)
        row.addWidget(self.urm_version_combo, 1)
        card.add_layout(row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.urm_download_button = QPushButton(tr("settings.download_now"))
        self.urm_download_button.setObjectName("primary")
        self.urm_download_button.clicked.connect(self._download_urm)
        self.urm_prune_button = QPushButton(tr("settings.prune_old"))
        self.urm_prune_button.clicked.connect(self._prune_urm)
        self.urm_open_cache_button = QPushButton(tr("settings.open_cache"))
        self.urm_open_cache_button.setObjectName("ghost")
        self.urm_open_cache_button.clicked.connect(lambda: winapi.open_folder(paths.URM_CACHE_DIR))
        actions.addWidget(self.urm_download_button)
        actions.addWidget(self.urm_prune_button)
        actions.addStretch(1)
        actions.addWidget(self.urm_open_cache_button)
        card.add_layout(actions)

        self.urm_status = QLabel("")
        self.urm_status.setObjectName("muted")
        self.urm_status.setWordWrap(True)
        self.urm_status.hide()
        card.add(self.urm_status)

        self.urm_progress = QProgressBar()
        self.urm_progress.setRange(0, 100)
        self.urm_progress.setValue(0)
        self.urm_progress.hide()
        card.add(self.urm_progress)
        return card

    def _build_defaults_card(self) -> Card:
        card = Card(tr("settings.defaults_card"))
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(tr("settings.variant"))
        label.setObjectName("muted")
        self.variant_combo = QComboBox()
        for variant in anime4k.VARIANTS:
            self.variant_combo.addItem(f"{variant.label} — {variant.resolution}", variant.key)
        index = self.variant_combo.findData(self.settings.default_variant)
        self.variant_combo.setCurrentIndex(max(0, index))
        row.addWidget(label)
        row.addWidget(self.variant_combo, 1)
        card.add_layout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        label2 = QLabel(tr("settings.default_top_margin"))
        label2.setObjectName("muted")
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 200)
        self.margin_spin.setSuffix(" px")
        self.margin_spin.setValue(int(self.settings.default_top_margin))
        self.margin_spin.setToolTip(tr("settings.default_top_margin_tooltip"))
        row2.addWidget(label2)
        row2.addWidget(self.margin_spin, 1)
        card.add_layout(row2)

        self.launcher_check = QCheckBox(tr("settings.create_launcher"))
        self.launcher_check.setChecked(self.settings.create_launcher)
        card.add(self.launcher_check)

        self.rpgmaker_plugin_check = QCheckBox(tr("settings.rpgm_hide_textbox"))
        self.rpgmaker_plugin_check.setChecked(self.settings.rpgmaker_hide_textbox)
        card.add(self.rpgmaker_plugin_check)

        self.rpgmaker_no_alt_check = QCheckBox(tr("settings.rpgm_no_alt"))
        self.rpgmaker_no_alt_check.setChecked(self.settings.rpgmaker_no_alt_skip)
        card.add(self.rpgmaker_no_alt_check)

        self.rpgmaker_save_slots_check = QCheckBox(tr("settings.rpgm_save_slots"))
        self.rpgmaker_save_slots_check.setChecked(self.settings.rpgmaker_save_slots_100)
        card.add(self.rpgmaker_save_slots_check)

        self.renpy_urm_check = QCheckBox(tr("settings.renpy_urm"))
        self.renpy_urm_check.setChecked(self.settings.renpy_urm)
        card.add(self.renpy_urm_check)

        divider = Divider()
        card.add(divider)

        data_row = QHBoxLayout()
        data_row.setSpacing(8)
        data_label = QLabel(tr("settings.app_data", path=paths.DATA_DIR))
        data_label.setObjectName("muted")
        data_label.setWordWrap(True)
        data_row.addWidget(data_label, 1)
        open_data = QPushButton(tr("common.open"))
        open_data.setObjectName("ghost")
        open_data.clicked.connect(lambda: winapi.open_folder(paths.DATA_DIR))
        data_row.addWidget(open_data)
        card.add_layout(data_row)
        return card

    def _build_about(self) -> QLabel:
        label = QLabel(tr("settings.about"))
        label.setObjectName("muted")
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {MUTED}; font-size: 8.5pt;")
        return label

    # -- data ------------------------------------------------------------
    def _set_downloading(self, busy: bool) -> None:
        self.download_button.setEnabled(not busy)
        self.nwjs_download_button.setEnabled(not busy)
        self.urm_download_button.setEnabled(not busy)

    def _refresh_cache_info(self) -> None:
        cached = reshade.list_cached()
        if cached:
            versions = ", ".join(item.version for item in cached)
            self.cache_label.setText(
                tr("settings.reshade_cache_present", versions=versions, folder=paths.RESHADE_CACHE_DIR)
            )
        else:
            self.cache_label.setText(tr("settings.reshade_cache_empty"))

        current = self.version_combo.currentData()
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        self.version_combo.addItem(tr("settings.reshade_latest_option"), "")
        for item in cached:
            label = tr("settings.cached_suffix", version=item.version)
            if self.settings.reshade_version == item.version:
                label += tr("settings.preferred_suffix")
            self.version_combo.addItem(label, item.version)
        if current:
            index = self.version_combo.findData(current)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        elif self.settings.reshade_version:
            index = self.version_combo.findData(self.settings.reshade_version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
        self.version_combo.blockSignals(False)
        self.prune_button.setEnabled(len(cached) > 1)

    def _refresh_nwjs_cache_info(self) -> None:
        cached = nwjs.list_cached()
        if cached:
            versions = ", ".join(
                f"{item.version} ({tr('common.bits', bits=item.bits)})" for item in cached
            )
            self.nwjs_cache_label.setText(
                tr("settings.nwjs_cache_present", versions=versions, folder=paths.NWJS_CACHE_DIR)
            )
        else:
            self.nwjs_cache_label.setText(tr("settings.nwjs_cache_empty"))

        current = self.nwjs_version_combo.currentData()
        self.nwjs_version_combo.blockSignals(True)
        self.nwjs_version_combo.clear()
        self.nwjs_version_combo.addItem(tr("settings.stable_latest_option"), "")
        for item in cached:
            label = tr("settings.nwjs_cached_item", version=item.version, bits=item.bits)
            if self.settings.nwjs_version == item.version:
                label += tr("settings.preferred_suffix")
            self.nwjs_version_combo.addItem(label, item.version)
        if current:
            index = self.nwjs_version_combo.findData(current)
            if index >= 0:
                self.nwjs_version_combo.setCurrentIndex(index)
        elif self.settings.nwjs_version:
            index = self.nwjs_version_combo.findData(self.settings.nwjs_version)
            if index >= 0:
                self.nwjs_version_combo.setCurrentIndex(index)
        self.nwjs_version_combo.blockSignals(False)
        self.nwjs_prune_button.setEnabled(len(cached) > 1)

    def _refresh_urm_cache_info(self) -> None:
        cached = renpy.list_cached()
        if cached:
            versions = ", ".join(item.version for item in cached)
            self.urm_cache_label.setText(
                tr("settings.urm_cache_present", versions=versions, folder=paths.URM_CACHE_DIR)
            )
        else:
            self.urm_cache_label.setText(tr("settings.urm_cache_empty"))

        current = self.urm_version_combo.currentData()
        self.urm_version_combo.blockSignals(True)
        self.urm_version_combo.clear()
        self.urm_version_combo.addItem(tr("settings.stable_latest_option"), "")
        for item in cached:
            label = tr("settings.cached_suffix", version=item.version)
            if self.settings.urm_version == item.version:
                label += tr("settings.preferred_suffix")
            self.urm_version_combo.addItem(label, item.version)
        if current:
            index = self.urm_version_combo.findData(current)
            if index >= 0:
                self.urm_version_combo.setCurrentIndex(index)
        elif self.settings.urm_version:
            index = self.urm_version_combo.findData(self.settings.urm_version)
            if index >= 0:
                self.urm_version_combo.setCurrentIndex(index)
        self.urm_version_combo.blockSignals(False)
        self.urm_prune_button.setEnabled(len(cached) > 1)

    def _download(self) -> None:
        if self.task is not None:
            return
        version = self.version_combo.currentData() or None
        self._set_downloading(True)
        self.progress.show()
        self.progress.setValue(0)
        self.download_status.show()

        def body(log, progress):
            return reshade.ensure_release(
                version,
                progress=lambda done, total: progress(done, total),
                status=log,
                allow_network=True,
            )

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(done * 100 / total))
                self.download_status.setText(
                    tr("settings.downloading_progress", done=done / 1048576, total=total / 1048576)
                )
            else:
                self.progress.setRange(0, 0)

        def on_result(release) -> None:
            self.task = None
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self._set_downloading(False)
            self.download_status.setText(
                tr("settings.reshade_ready", version=release.version, folder=release.folder)
            )
            self._refresh_cache_info()

        def on_error(message: str, trace: str, error: object | None = None) -> None:
            self.task = None
            self.progress.hide()
            self._set_downloading(False)
            self.download_status.setText(tr("settings.download_failed", message=message))
            box = QMessageBox(
                QMessageBox.Critical,
                tr("settings.download_failed_title"),
                message,
                QMessageBox.Ok,
                self,
            )
            box.setDetailedText(trace)
            box.exec()

        self.task = run_task(body, lambda text: self.download_status.setText(text), on_progress, on_result, on_error)

    def _download_nwjs(self) -> None:
        if self.task is not None:
            return
        self._set_downloading(True)
        self.nwjs_progress.show()
        self.nwjs_progress.setValue(0)
        self.nwjs_status.show()

        def body(log, progress):
            release = nwjs.fetch_latest_release(arch=nwjs.DEFAULT_ARCH)
            cached = nwjs.list_cached(arch=nwjs.DEFAULT_ARCH)
            for item in cached:
                if item.version == release.version:
                    log(tr("settings.nwjs_already_latest", version=item.version))
                    return item
            archive = nwjs.download_archive(release, progress=progress, status=log)
            return nwjs.cache_from_archive(archive, release, status=log)

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.nwjs_progress.setRange(0, 100)
                self.nwjs_progress.setValue(int(done * 100 / total))
                self.nwjs_status.setText(
                    tr("settings.nwjs_downloading_progress", done=done / 1048576, total=total / 1048576)
                )
            else:
                self.nwjs_progress.setRange(0, 0)

        def on_result(cached_build) -> None:
            self.task = None
            self.nwjs_progress.setRange(0, 100)
            self.nwjs_progress.setValue(100)
            self._set_downloading(False)
            self.nwjs_status.setText(
                tr("settings.nwjs_ready", version=cached_build.version, bits=cached_build.bits)
            )
            self._refresh_nwjs_cache_info()

        def on_error(message: str, trace: str, error: object | None = None) -> None:
            self.task = None
            self.nwjs_progress.hide()
            self._set_downloading(False)
            self.nwjs_status.setText(tr("settings.download_failed", message=message))
            box = QMessageBox(
                QMessageBox.Critical,
                tr("settings.nwjs_download_failed_title"),
                message,
                QMessageBox.Ok,
                self,
            )
            box.setDetailedText(trace)
            box.exec()

        self.task = run_task(body, lambda text: self.nwjs_status.setText(text), on_progress, on_result, on_error)

    def _download_urm(self) -> None:
        if self.task is not None:
            return
        self._set_downloading(True)
        self.urm_progress.show()
        self.urm_progress.setValue(0)
        self.urm_status.show()

        def body(log, progress):
            release = renpy.fetch_latest_release()
            cached = renpy.list_cached()
            for item in cached:
                if item.version == release.version:
                    log(tr("settings.urm_already_latest", version=item.version))
                    return item
            archive = renpy.download_archive(release, progress=progress, status=log)
            return renpy.cache_from_archive(archive, release)

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.urm_progress.setRange(0, 100)
                self.urm_progress.setValue(int(done * 100 / total))
                self.urm_status.setText(
                    tr("settings.urm_downloading_progress", done=done / 1048576, total=total / 1048576)
                )
            else:
                self.urm_progress.setRange(0, 0)

        def on_result(cached_build) -> None:
            self.task = None
            self.urm_progress.setRange(0, 100)
            self.urm_progress.setValue(100)
            self._set_downloading(False)
            self.urm_status.setText(tr("settings.urm_ready", version=cached_build.version))
            self._refresh_urm_cache_info()

        def on_error(message: str, trace: str, error: object | None = None) -> None:
            self.task = None
            self.urm_progress.hide()
            self._set_downloading(False)
            self.urm_status.setText(tr("settings.download_failed", message=message))
            box = QMessageBox(
                QMessageBox.Critical,
                tr("settings.urm_download_failed_title"),
                message,
                QMessageBox.Ok,
                self,
            )
            box.setDetailedText(trace)
            box.exec()

        self.task = run_task(body, lambda text: self.urm_status.setText(text), on_progress, on_result, on_error)

    def _prune(self) -> None:
        removed = reshade.prune_cache(keep=1)
        self._refresh_cache_info()
        if removed:
            self.download_status.show()
            self.download_status.setText(tr("settings.pruned", items=", ".join(removed)))

    def _prune_nwjs(self) -> None:
        removed = nwjs.prune_cache(keep=1)
        self._refresh_nwjs_cache_info()
        if removed:
            self.nwjs_status.show()
            self.nwjs_status.setText(tr("settings.pruned", items=", ".join(removed)))

    def _prune_urm(self) -> None:
        removed = renpy.prune_cache(keep=1)
        self._refresh_urm_cache_info()
        if removed:
            self.urm_status.show()
            self.urm_status.setText(tr("settings.pruned", items=", ".join(removed)))

    def _save(self) -> None:
        selected_lang = i18n.normalize_language(self.language_combo.currentData())
        self.settings.language = selected_lang
        i18n.set_language(selected_lang)
        self.settings.reshade_version = self.version_combo.currentData() or ""
        self.settings.nwjs_version = self.nwjs_version_combo.currentData() or ""
        self.settings.urm_version = self.urm_version_combo.currentData() or ""
        self.settings.default_variant = self.variant_combo.currentData()
        self.settings.default_top_margin = int(self.margin_spin.value())
        self.settings.create_launcher = self.launcher_check.isChecked()
        self.settings.rpgmaker_hide_textbox = self.rpgmaker_plugin_check.isChecked()
        self.settings.rpgmaker_no_alt_skip = self.rpgmaker_no_alt_check.isChecked()
        self.settings.rpgmaker_save_slots_100 = self.rpgmaker_save_slots_check.isChecked()
        self.settings.renpy_urm = self.renpy_urm_check.isChecked()
        self.store.save_settings()
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.task is not None:
            QMessageBox.information(
                self,
                tr("settings.download_in_progress_title"),
                tr("settings.download_in_progress_body"),
            )
            event.ignore()
            return
        super().closeEvent(event)
