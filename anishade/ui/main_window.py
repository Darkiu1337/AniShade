"""Main window: game library, detection panel, shader picker and actions."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import (
    APP_NAME,
    __version__,
    anime4k,
    detect,
    engines,
    installer,
    nwjs,
    renpy,
    reshade,
    rpgmaker,
    winapi,
)
from ..store import Game, Store, game_id_for
from .delegates import (
    ROLE_COST,
    ROLE_DESC,
    ROLE_FAMILY,
    ROLE_RESOLUTION,
    ROLE_STATUS,
    ROLE_STATUS_KIND,
    ROLE_SUBTITLE,
    ROLE_TITLE,
    GameDelegate,
    VariantDelegate,
)
from .icons import app_icon, make_logo
from .settings_dialog import SettingsDialog
from .theme import MUTED, SUCCESS
from .widgets import Banner, Card, Divider, ElidedLabel, ToggleSwitch
from .workers import run_task

ROLE_GAME_ID = Qt.UserRole
ROLE_VARIANT_KEY = Qt.UserRole + 1


class MainWindow(QMainWindow):
    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self.current_game: Game | None = None
        self.analysis: detect.GameAnalysis | None = None
        self.task = None
        self._loading = False
        self._refreshing = False

        self.setWindowTitle("AniShade — ReShade + Anime4K Restore")
        self.setWindowIcon(app_icon())
        self.setAcceptDrops(True)
        self.resize(store.settings.window_width, store.settings.window_height)
        self.setMinimumSize(980, 660)

        self._build_ui()
        self._refresh_games()
        self._setup_shortcuts()
        self._maybe_show_banner()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        root.addLayout(self._build_topbar())

        self.banner = Banner(
            "O ReShade ainda não foi baixado. Ele será obtido do site oficial (reshade.me) "
            "na primeira instalação — depois fica em cache para todos os jogos.",
            "Baixar agora",
            kind="warn",
        )
        self.banner.button.clicked.connect(self._download_reshade)
        self.banner.hide()
        root.addWidget(self.banner)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 850])
        self.splitter = splitter
        root.addWidget(splitter, 1)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(1200)
        self.log_box.setFixedHeight(120)
        self.log_box.setPlaceholderText("O registro das operações aparece aqui (Ctrl+L).")
        self.log_box.hide()
        root.addWidget(self.log_box)

        root.addWidget(Divider())
        root.addLayout(self._build_footer())
        self._log_lines: list[str] = []

    def _build_topbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(make_logo(34))
        logo.setFixedSize(34, 34)
        bar.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel("ReShade + Anime4K Restore para visual novels e jogos japoneses")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        bar.addLayout(titles)
        bar.addStretch(1)

        self.add_button = QPushButton("Adicionar jogo")
        self.add_button.setObjectName("primary")
        self.add_button.setIcon(QIcon())
        self.add_button.clicked.connect(self._pick_game)
        bar.addWidget(self.add_button)

        settings_button = QPushButton("Configurações")
        settings_button.setObjectName("ghost")
        settings_button.clicked.connect(self._open_settings)
        bar.addWidget(settings_button)

        self.log_button = QPushButton("Registro")
        self.log_button.setObjectName("ghost")
        self.log_button.setCheckable(True)
        self.log_button.toggled.connect(self._toggle_log)
        bar.addWidget(self.log_button)

        version = QLabel(f"v{__version__}")
        version.setObjectName("appSubtitle")
        version.setToolTip("AniShade — ReShade + Anime4K Restore")
        bar.addWidget(version)
        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 6, 6, 0)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar na biblioteca...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.game_list = QListWidget()
        self.game_list.setItemDelegate(GameDelegate(self.game_list))
        self.game_list.setMouseTracking(True)
        self.game_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.game_list.setSpacing(1)
        self.game_list.currentItemChanged.connect(self._on_game_selected)
        self.game_list.itemDoubleClicked.connect(lambda _: self._rename_game())
        self.game_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.game_list.customContextMenuRequested.connect(self._game_context_menu)
        layout.addWidget(self.game_list, 1)

        self.empty_hint = QLabel(
            "Nenhum jogo ainda.\n\nClique em “Adicionar jogo” e aponte para o .exe do jogo, "
            "ou arraste o executável para esta janela."
        )
        self.empty_hint.setObjectName("muted")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        layout.addWidget(self.empty_hint, 1)

        hint = QLabel("Duplo clique renomeia · Botão direito abre opções")
        hint.setObjectName("muted")
        hint.setStyleSheet("font-size: 8pt;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 6, 0, 0)
        layout.setSpacing(10)

        self.stack = QStackedWidget()
        placeholder = QLabel(
            "Selecione um jogo na lista para ver a detecção, escolher a variante do Anime4K "
            "e instalar o ReShade."
        )
        placeholder.setObjectName("muted")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setWordWrap(True)
        self.stack.addWidget(placeholder)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_scroll = scroll
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 10, 6)
        content_layout.setSpacing(12)
        content_layout.addWidget(self._build_game_header())
        content_layout.addWidget(self._build_detection_card())
        self.rpgmaker_card = self._build_rpgmaker_card()
        self.rpgmaker_card.hide()
        content_layout.addWidget(self.rpgmaker_card)
        self.renpy_card = self._build_renpy_card()
        self.renpy_card.hide()
        content_layout.addWidget(self.renpy_card)
        content_layout.addWidget(self._build_shader_card())
        content_layout.addWidget(self._build_install_card())
        content_layout.addStretch(1)
        scroll.setWidget(content)
        self.stack.addWidget(scroll)
        self.stack.setCurrentIndex(0)

        layout.addWidget(self.stack, 1)
        return panel

    def _build_game_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.game_title = QLabel("")
        self.game_title.setObjectName("gameTitle")
        self.game_title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.game_title, 1)

        self.play_button = QPushButton("Jogar")
        self.play_button.setObjectName("primary")
        self.play_button.setToolTip("Inicia o jogo com as correções de ambiente do engine")
        self.play_button.clicked.connect(self._launch_game)
        top.addWidget(self.play_button)

        folder_button = QPushButton("Pasta")
        folder_button.setObjectName("ghost")
        folder_button.clicked.connect(self._open_game_folder)
        top.addWidget(folder_button)

        self.remove_button = QPushButton("Remover")
        self.remove_button.setObjectName("ghost")
        self.remove_button.clicked.connect(self._remove_game)
        top.addWidget(self.remove_button)
        layout.addLayout(top)

        self.game_path = ElidedLabel("")
        self.game_path.setObjectName("path")
        layout.addWidget(self.game_path)
        return header

    def _label(self, text: str, muted: bool = True) -> QLabel:
        label = QLabel(text)
        if muted:
            label.setObjectName("muted")
        return label

    def _build_detection_card(self) -> Card:
        card = Card("Detecção")
        self.reanalyze_button = QPushButton("Reanalisar")
        self.reanalyze_button.setObjectName("chip")
        self.reanalyze_button.clicked.connect(self._reanalyze)
        card.add_header_widget(self.reanalyze_button)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(2, 1)

        grid.addWidget(self._label("Engine"), 0, 0)
        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(240)
        self.engine_combo.addItem("Detectar automaticamente", "")
        for key, engine in sorted(engines.ENGINES.items(), key=lambda item: item[1].name):
            self.engine_combo.addItem(engine.name, key)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_override)
        grid.addWidget(self.engine_combo, 0, 1)
        self.engine_evidence = ElidedLabel("")
        self.engine_evidence.setObjectName("muted")
        grid.addWidget(self.engine_evidence, 0, 2)

        grid.addWidget(self._label("API gráfica"), 1, 0)
        self.api_combo = QComboBox()
        self.api_combo.setMinimumWidth(240)
        self.api_combo.addItem("Detectar automaticamente", "")
        for key, label in detect.API_LABELS.items():
            if key != "desconhecida":
                self.api_combo.addItem(label, key)
        self.api_combo.currentIndexChanged.connect(self._on_api_override)
        grid.addWidget(self.api_combo, 1, 1)
        self.api_source = ElidedLabel("")
        self.api_source.setObjectName("muted")
        grid.addWidget(self.api_source, 1, 2)

        grid.addWidget(self._label("Arquitetura"), 2, 0)
        self.arch_label = QLabel("—")
        grid.addWidget(self.arch_label, 2, 1, 1, 2)

        grid.addWidget(self._label("ReShade"), 3, 0)
        self.reshade_state = QLabel("—")
        grid.addWidget(self.reshade_state, 3, 1, 1, 2)
        card.add_layout(grid)

        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        card.add(self.warning_label)

        self.notes_label = QLabel("")
        self.notes_label.setObjectName("muted")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet("font-size: 8.6pt;")
        self.notes_label.hide()
        card.add(self.notes_label)
        return card

    def _build_rpgmaker_card(self) -> Card:
        card = Card("RPG Maker MV/MZ")

        # 1. Immediate toggle for the Hide Textbox (H key) plugin
        plugin_row = QHBoxLayout()
        plugin_row.setSpacing(12)
        plugin_text = QVBoxLayout()
        plugin_text.setSpacing(2)
        plugin_title = QLabel("Ocultar caixa de texto com a tecla H")
        plugin_title.setStyleSheet("font-weight: 600;")
        self.rpgmaker_plugin_status = QLabel("—")
        self.rpgmaker_plugin_status.setObjectName("muted")
        self.rpgmaker_plugin_status.setWordWrap(True)
        self.rpgmaker_plugin_status.setStyleSheet("font-size: 8.6pt;")
        plugin_text.addWidget(plugin_title)
        plugin_text.addWidget(self.rpgmaker_plugin_status)
        plugin_row.addLayout(plugin_text, 1)

        self.rpgmaker_plugin_toggle = ToggleSwitch()
        self.rpgmaker_plugin_toggle.setToolTip(
            "Ativa ou remove AniShade_HideTextbox.js em js/plugins/ e plugins.js imediatamente."
        )
        self.rpgmaker_plugin_toggle.toggled.connect(
            lambda checked: self._on_rpgmaker_plugin_toggled("hide_textbox", checked)
        )
        plugin_row.addWidget(self.rpgmaker_plugin_toggle, 0, Qt.AlignVCenter)
        card.add_layout(plugin_row)

        card.add(Divider())

        # 2. Immediate toggle for the No-Alt-Skip (Alt / Alt+Tab) plugin
        alt_row = QHBoxLayout()
        alt_row.setSpacing(12)
        alt_text = QVBoxLayout()
        alt_text.setSpacing(2)
        alt_title = QLabel("Impedir Alt de pular texto (Alt+Tab)")
        alt_title.setStyleSheet("font-weight: 600;")
        self.rpgmaker_no_alt_status = QLabel("—")
        self.rpgmaker_no_alt_status.setObjectName("muted")
        self.rpgmaker_no_alt_status.setWordWrap(True)
        self.rpgmaker_no_alt_status.setStyleSheet("font-size: 8.6pt;")
        alt_text.addWidget(alt_title)
        alt_text.addWidget(self.rpgmaker_no_alt_status)
        alt_row.addLayout(alt_text, 1)

        self.rpgmaker_no_alt_toggle = ToggleSwitch()
        self.rpgmaker_no_alt_toggle.setToolTip(
            "Ativa ou remove AniShade_NoAltSkip.js para que Alt / Alt+Tab / Alt+Enter nunca pulem diálogos "
            "(Ctrl continua funcionando normalmente)."
        )
        self.rpgmaker_no_alt_toggle.toggled.connect(
            lambda checked: self._on_rpgmaker_plugin_toggled("no_alt_skip", checked)
        )
        alt_row.addWidget(self.rpgmaker_no_alt_toggle, 0, Qt.AlignVCenter)
        card.add_layout(alt_row)

        card.add(Divider())

        # 3. Immediate toggle for the 100 Save Slots plugin
        slots_row = QHBoxLayout()
        slots_row.setSpacing(12)
        slots_text = QVBoxLayout()
        slots_text.setSpacing(2)
        slots_title = QLabel("Expandir para 100 slots de save")
        slots_title.setStyleSheet("font-weight: 600;")
        self.rpgmaker_save_slots_status = QLabel("—")
        self.rpgmaker_save_slots_status.setObjectName("muted")
        self.rpgmaker_save_slots_status.setWordWrap(True)
        self.rpgmaker_save_slots_status.setStyleSheet("font-size: 8.6pt;")
        slots_text.addWidget(slots_title)
        slots_text.addWidget(self.rpgmaker_save_slots_status)
        slots_row.addLayout(slots_text, 1)

        self.rpgmaker_save_slots_toggle = ToggleSwitch()
        self.rpgmaker_save_slots_toggle.setToolTip(
            "Ativa ou remove AniShade_SaveSlots100.js para liberar 100 slots manuais de save "
            "(mantém o Autosave no MZ e nunca reduz se o jogo já tiver mais de 100)."
        )
        self.rpgmaker_save_slots_toggle.toggled.connect(
            lambda checked: self._on_rpgmaker_plugin_toggled("save_slots_100", checked)
        )
        slots_row.addWidget(self.rpgmaker_save_slots_toggle, 0, Qt.AlignVCenter)
        card.add_layout(slots_row)

        card.add(Divider())

        # 4. NW.js official runtime updater + package.json compatibility fixer
        nwjs_row = QHBoxLayout()
        nwjs_row.setSpacing(10)
        nwjs_text = QVBoxLayout()
        nwjs_text.setSpacing(2)
        nwjs_title = QLabel("Atualizar NW.js (oficial)")
        nwjs_title.setStyleSheet("font-weight: 600;")
        self.nwjs_status_label = QLabel("—")
        self.nwjs_status_label.setObjectName("muted")
        self.nwjs_status_label.setWordWrap(True)
        self.nwjs_status_label.setStyleSheet("font-size: 8.6pt;")
        nwjs_text.addWidget(nwjs_title)
        nwjs_text.addWidget(self.nwjs_status_label)
        nwjs_row.addLayout(nwjs_text, 1)

        self.nwjs_restore_button = QPushButton("Restaurar")
        self.nwjs_restore_button.setObjectName("ghost")
        self.nwjs_restore_button.setToolTip("Restaura o NW.js e o package.json originais do backup")
        self.nwjs_restore_button.clicked.connect(self._start_restore_nwjs)
        self.nwjs_restore_button.hide()
        nwjs_row.addWidget(self.nwjs_restore_button, 0, Qt.AlignVCenter)

        self.nwjs_update_button = QPushButton("Atualizar NW.js")
        self.nwjs_update_button.setToolTip(
            "Baixa o NW.js oficial de nwjs.io (uma única vez), atualiza o runtime do jogo "
            "e corrige problemas de compatibilidade no package.json (name ausente, autoplay, js-flags, etc.)."
        )
        self.nwjs_update_button.clicked.connect(self._start_update_nwjs)
        nwjs_row.addWidget(self.nwjs_update_button, 0, Qt.AlignVCenter)
        card.add_layout(nwjs_row)
        return card

    def _build_renpy_card(self) -> Card:
        card = Card("Ren'Py")
        mod_link = QPushButton("0x52.dev")
        mod_link.setObjectName("chip")
        mod_link.setToolTip(f"Abrir página oficial: {renpy.MOD_PAGE_URL}")
        mod_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(renpy.MOD_PAGE_URL)))
        card.add_header_widget(mod_link)

        urm_row = QHBoxLayout()
        urm_row.setSpacing(12)
        urm_text = QVBoxLayout()
        urm_text.setSpacing(2)
        urm_title = QLabel("Universal Ren'Py Mod (URM)")
        urm_title.setStyleSheet("font-weight: 600;")
        self.renpy_urm_status = QLabel("—")
        self.renpy_urm_status.setObjectName("muted")
        self.renpy_urm_status.setWordWrap(True)
        self.renpy_urm_status.setStyleSheet("font-size: 8.6pt;")
        urm_text.addWidget(urm_title)
        urm_text.addWidget(self.renpy_urm_status)
        urm_row.addLayout(urm_text, 1)

        self.renpy_urm_toggle = ToggleSwitch()
        self.renpy_urm_toggle.setToolTip(
            "Baixa o Universal Ren'Py Mod (0x52_URM.rpa) de 0x52.dev uma única vez, "
            "salva em cache e instala ou remove na pasta game/ imediatamente."
        )
        self.renpy_urm_toggle.toggled.connect(self._on_renpy_urm_toggled)
        urm_row.addWidget(self.renpy_urm_toggle, 0, Qt.AlignVCenter)
        card.add_layout(urm_row)
        return card

    def _build_shader_card(self) -> Card:
        card = Card("Shaders Anime4K (Restore)")
        intro = QLabel(
            "Restore reconstrói detalhes da arte que o jogo já ampliou. Escolha a variante pela "
            "resolução interna do jogo; quanto maior a rede, maior o custo de GPU."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 8.7pt;")
        card.add(intro)

        self.variant_list = QListWidget()
        self.variant_list.setItemDelegate(VariantDelegate(self.variant_list))
        self.variant_list.setMouseTracking(True)
        self.variant_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.variant_list.setFixedHeight(392)
        self.variant_list.setSpacing(1)
        for variant in anime4k.VARIANTS:
            item = QListWidgetItem()
            item.setData(ROLE_VARIANT_KEY, variant.key)
            item.setData(ROLE_TITLE, variant.label)
            item.setData(ROLE_DESC, variant.description)
            item.setData(ROLE_RESOLUTION, variant.resolution)
            item.setData(ROLE_COST, variant.weight)
            item.setData(ROLE_FAMILY, variant.family)
            self.variant_list.addItem(item)
        self.variant_list.currentRowChanged.connect(self._on_variant_changed)
        card.add(self.variant_list)

        divider = Divider()
        card.add(divider)

        margin_row = QHBoxLayout()
        margin_row.setSpacing(8)
        margin_label = QLabel("Margem superior (barra de título)")
        margin_label.setObjectName("muted")
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 200)
        self.margin_spin.setSuffix(" px")
        self.margin_spin.setToolTip(
            "Pixels do topo que não devem ser filtrados. Alguns jogos NW.js/Chromium "
            "incluem a barra de título no swapchain (ex.: buffer 1080x751 para conteúdo "
            "1080x720). Use 0 em fullscreen/borderless."
        )
        self.margin_spin.valueChanged.connect(self._on_margin_changed)
        margin_row.addWidget(margin_label)
        margin_row.addWidget(self.margin_spin, 1)
        card.add_layout(margin_row)

        margin_hint = QLabel(
            "Deixe 0 em fullscreen. Em janela, se a barra de título ficar distorcida, "
            "ajuste para a altura da barra (ex.: 31 px)."
        )
        margin_hint.setObjectName("muted")
        margin_hint.setWordWrap(True)
        margin_hint.setStyleSheet("font-size: 8.5pt;")
        card.add(margin_hint)

        aspect_row = QHBoxLayout()
        aspect_row.setSpacing(8)
        aspect_label = QLabel("Proporção do conteúdo (L/A)")
        aspect_label.setObjectName("muted")
        self.aspect_spin = QDoubleSpinBox()
        self.aspect_spin.setRange(0.0, 4.0)
        self.aspect_spin.setDecimals(3)
        self.aspect_spin.setSingleStep(0.01)
        self.aspect_spin.setToolTip(
            "Opcional: limita manualmente o shader a uma proporção (ex.: 1.5). "
            "Deixe 0 (recomendado): o shader já detecta e bloqueia feedback nas bordas automaticamente."
        )
        self.aspect_spin.valueChanged.connect(self._on_aspect_changed)
        aspect_row.addWidget(aspect_label)
        aspect_row.addWidget(self.aspect_spin, 1)
        card.add_layout(aspect_row)

        aspect_hint = QLabel(
            "Recomendado: 0 (tela inteira). A proteção contra ruído/feedback nas bordas pretas é automática no shader."
        )
        aspect_hint.setObjectName("muted")
        aspect_hint.setWordWrap(True)
        aspect_hint.setStyleSheet("font-size: 8.5pt;")
        card.add(aspect_hint)
        return card

    def _build_install_card(self) -> Card:
        card = Card("Instalação")
        self.install_refresh = QPushButton("Atualizar status")
        self.install_refresh.setObjectName("chip")
        self.install_refresh.clicked.connect(self._refresh_install_card)
        card.add_header_widget(self.install_refresh)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        self.reshade_value = QLabel("—")
        self.shaders_value = QLabel("—")
        self.launcher_value = QLabel("—")
        self.preset_value = ElidedLabel("—")
        self.rpgmaker_plugin_label = self._label("Plugin RPG Maker")
        self.rpgmaker_plugin_value = QLabel("—")
        self.renpy_urm_label = self._label("Mod Ren'Py")
        self.renpy_urm_value = QLabel("—")

        self.dll_combo = QComboBox()
        self.dll_combo.setToolTip(
            "Nome da DLL proxy. 'Automático' escolhe a melhor opção livre na pasta do jogo."
        )
        self.dll_combo.currentIndexChanged.connect(self._on_dll_changed)

        grid.addWidget(self._label("ReShade"), 0, 0)
        grid.addWidget(self.reshade_value, 0, 1)
        grid.addWidget(self._label("DLL proxy"), 1, 0)
        grid.addWidget(self.dll_combo, 1, 1)
        grid.addWidget(self._label("Preset"), 2, 0)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_row.addWidget(self.preset_value, 1)
        self.open_preset_button = QPushButton("Editar")
        self.open_preset_button.setObjectName("chip")
        self.open_preset_button.setToolTip("Abrir o preset no editor padrão (.ini)")
        self.open_preset_button.clicked.connect(self._open_preset)
        preset_row.addWidget(self.open_preset_button)
        grid.addLayout(preset_row, 2, 1)
        grid.addWidget(self._label("Shaders"), 3, 0)
        grid.addWidget(self.shaders_value, 3, 1)
        grid.addWidget(self._label("Launcher"), 4, 0)
        grid.addWidget(self.launcher_value, 4, 1)
        grid.addWidget(self.rpgmaker_plugin_label, 5, 0)
        grid.addWidget(self.rpgmaker_plugin_value, 5, 1)
        self.rpgmaker_plugin_label.hide()
        self.rpgmaker_plugin_value.hide()
        grid.addWidget(self.renpy_urm_label, 6, 0)
        grid.addWidget(self.renpy_urm_value, 6, 1)
        self.renpy_urm_label.hide()
        self.renpy_urm_value.hide()
        card.add_layout(grid)

        self.problems_label = QLabel("")
        self.problems_label.setObjectName("warning")
        self.problems_label.setWordWrap(True)
        self.problems_label.hide()
        card.add(self.problems_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.create_launcher_check = QCheckBox("Criar launcher .bat com correções do engine")
        self.create_launcher_check.setToolTip(
            "O launcher aplica variáveis de ambiente recomendadas (ex.: RENPY_RENDERER) "
            "antes de abrir o jogo."
        )
        self.create_launcher_check.toggled.connect(self._on_launcher_toggled)
        row.addWidget(self.create_launcher_check, 1)
        open_folder = QPushButton("Abrir pasta do jogo")
        open_folder.setObjectName("ghost")
        open_folder.clicked.connect(self._open_game_folder)
        row.addWidget(open_folder)
        card.add_layout(row)
        return card

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.footer_status = ElidedLabel("Adicione um jogo para começar.")
        self.footer_status.setObjectName("muted")
        footer.addWidget(self.footer_status, 1)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(160)
        self.progress.setRange(0, 100)
        self.progress.hide()
        footer.addWidget(self.progress)

        self.uninstall_button = QPushButton("Desinstalar")
        self.uninstall_button.setObjectName("danger")
        self.uninstall_button.clicked.connect(self._start_uninstall)
        self.uninstall_button.setEnabled(False)
        footer.addWidget(self.uninstall_button)

        self.install_button = QPushButton("Instalar ReShade + Anime4K")
        self.install_button.setObjectName("primary")
        self.install_button.clicked.connect(self._start_install)
        self.install_button.setEnabled(False)
        footer.addWidget(self.install_button)
        return footer

    # ------------------------------------------------------------------
    # log / banner / shortcuts
    # ------------------------------------------------------------------
    def _toggle_log(self, checked: bool) -> None:
        self.log_box.setVisible(checked)

    def _log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self._log_lines.append(line)
        del self._log_lines[:-800]
        if self.log_box is not None:
            self.log_box.appendPlainText(line)
        self.footer_status.setText(message)
        self.footer_status.setToolTip(message)

    def _setup_shortcuts(self) -> None:
        shortcuts = (
            (QKeySequence("Ctrl+O"), self._pick_game),
            (QKeySequence("F5"), self._reanalyze),
            (QKeySequence("Ctrl+L"), lambda: self.log_button.toggle()),
        )
        for sequence, callback in shortcuts:
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(callback)

    def _maybe_show_banner(self) -> None:
        if not reshade.list_cached():
            self.banner.show()

    def _download_reshade(self) -> None:
        if self.task is not None:
            return

        def body(log, progress):
            return reshade.ensure_release(None, progress=progress, status=log, allow_network=True)

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(done * 100 / total))
            else:
                self.progress.setRange(0, 0)

        def on_result(release) -> None:
            self._set_busy(False)
            self.banner.hide()
            self._log(f"ReShade {release.version} pronto no cache.")
            self._refresh_install_card()

        self._set_busy(True, "Baixando ReShade...")
        self.banner.button.setEnabled(False)
        self.task = run_task(body, self._log, on_progress, on_result, self._on_task_error)

    # ------------------------------------------------------------------
    # library
    # ------------------------------------------------------------------
    def _badge(self, game: Game) -> tuple[str, str]:
        manifest = installer.load_manifest(game.id)
        if not manifest:
            return "Não instalado", "pending"
        dll_name = manifest.get("dll_name", "")
        if not dll_name or not (game.game_dir / dll_name).is_file():
            return "Incompleto", "error"
        if (
            manifest.get("variant") != game.variant
            or int(manifest.get("top_margin", 0)) != int(game.top_margin)
            or int(manifest.get("shader_version", 1)) < anime4k.SHADER_VERSION
            or not manifest.get("splash_hidden", False)
            or (
                game.content_aspect >= 0
                and abs(float(manifest.get("content_aspect", 0)) - game.content_aspect) > 0.001
            )
            or (
                rpgmaker.is_supported_engine(game.engine_key)
                and rpgmaker.find_js_dir(game.game_dir) is not None
                and (
                    bool(manifest.get("rpgmaker_plugin")) != bool(game.rpgmaker_hide_textbox)
                    or bool((manifest.get("rpgmaker_plugins") or {}).get("no_alt_skip"))
                    != bool(game.rpgmaker_no_alt_skip)
                    or bool((manifest.get("rpgmaker_plugins") or {}).get("save_slots_100"))
                    != bool(game.rpgmaker_save_slots_100)
                )
            )
            or (
                renpy.is_supported_engine(game.engine_key)
                and renpy.find_game_dir(game.game_dir) is not None
                and bool(manifest.get("renpy_urm")) != bool(game.renpy_urm)
            )
        ):
            return "Pendente", "warn"
        return "Instalado", "ok"

    def _refresh_games(self, select_id: str | None = None) -> None:
        self._refreshing = True
        if select_id is None and self.current_game is not None:
            select_id = self.current_game.id
        self.game_list.clear()
        games = self.store.sorted_games()
        for game in games:
            item = QListWidgetItem()
            item.setData(ROLE_GAME_ID, game.id)
            item.setData(ROLE_TITLE, game.name)
            api_label = detect.API_LABELS.get(game.api, game.api)
            item.setData(ROLE_SUBTITLE, f"{game.engine_name} · {api_label} · {game.bits} bits")
            status, kind = self._badge(game)
            item.setData(ROLE_STATUS, status)
            item.setData(ROLE_STATUS_KIND, kind)
            self.game_list.addItem(item)
        self._refreshing = False

        has_games = bool(games)
        self.game_list.setVisible(has_games)
        self.empty_hint.setVisible(not has_games)
        self._apply_filter(self.search.text())

        if select_id:
            for index in range(self.game_list.count()):
                item = self.game_list.item(index)
                if item.data(ROLE_GAME_ID) == select_id:
                    self.game_list.setCurrentItem(item)
                    return
        if games:
            self.game_list.setCurrentRow(0)
        else:
            self._clear_selection()

    def _apply_filter(self, text: str) -> None:
        needle = (text or "").strip().lower()
        for index in range(self.game_list.count()):
            item = self.game_list.item(index)
            haystack = f"{item.data(ROLE_TITLE)} {item.data(ROLE_SUBTITLE)}".lower()
            item.setHidden(bool(needle) and needle not in haystack)

    def _clear_selection(self) -> None:
        self.current_game = None
        self.analysis = None
        self.stack.setCurrentIndex(0)
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.footer_status.setText("Adicione um jogo para começar.")

    def _on_game_selected(self, current: QListWidgetItem | None, previous) -> None:
        if self._refreshing or current is None:
            return
        game = self.store.get(current.data(ROLE_GAME_ID))
        if game is None:
            return
        self.current_game = game
        self._load_game(game)

    def _load_game(self, game: Game) -> None:
        self._loading = True
        try:
            try:
                analysis = detect.analyze(
                    game.exe_path,
                    game.api_override or None,
                    game.engine_override or None,
                )
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Erro ao analisar", str(exc))
                return
            self.analysis = analysis
            self.stack.setCurrentIndex(1)
            self.content_scroll.verticalScrollBar().setValue(0)
            self.play_button.setEnabled(True)
            self.remove_button.setEnabled(True)

            self.game_title.setText(game.name)
            self.game_path.setText(str(game.exe_path))

            engine_index = self.engine_combo.findData(game.engine_override or "")
            self.engine_combo.setCurrentIndex(max(0, engine_index))
            api_index = self.api_combo.findData(game.api_override or "")
            self.api_combo.setCurrentIndex(max(0, api_index))

            evidence = "; ".join(analysis.engine_evidence) or "heurística padrão"
            self.engine_evidence.setText(f"{analysis.engine.name} — {evidence}")
            self.api_source.setText(f"{detect.API_LABELS.get(analysis.api, analysis.api)} — {analysis.api_source}")

            bits = analysis.bits or 0
            module = "ReShade64.dll" if bits == 64 else "ReShade32.dll" if bits == 32 else "?"
            self.arch_label.setText(f"{bits} bits" if bits else "desconhecida")
            self.arch_label.setToolTip(f"Módulo usado: {module}")
            self._refresh_dll_combo(analysis)

            if analysis.existing_reshade:
                state = analysis.existing_reshade_version or "instalado"
                self.reshade_state.setText(f"{state} ({analysis.existing_reshade_dll})")
                self.reshade_state.setStyleSheet(f"color: {SUCCESS};")
            else:
                self.reshade_state.setText("não instalado")
                self.reshade_state.setStyleSheet(f"color: {MUTED};")

            all_warnings = list(analysis.warnings)
            if analysis.conflicting_dlls:
                all_warnings.append(
                    "Conflito de nome: " + ", ".join(analysis.conflicting_dlls) + " (será evitado)."
                )
            if all_warnings:
                self.warning_label.setText("\n".join(f"• {item}" for item in all_warnings))
                self.warning_label.show()
            else:
                self.warning_label.hide()

            notes = list(analysis.notes)
            if notes:
                self.notes_label.setText("\n".join(f"• {note}" for note in notes))
                self.notes_label.show()
            else:
                self.notes_label.hide()

            self._select_variant(game.variant)
            self.margin_spin.setValue(int(game.top_margin))
            # Migrate games that previously received an auto-detected package.json aspect
            # under shader_version < 2 back to 0.0 (full screen with automatic feedback guard).
            manifest = installer.load_manifest(game.id)
            if (
                game.content_aspect > 0
                and int(manifest.get("shader_version", 1)) < anime4k.SHADER_VERSION
                and analysis.content_size
            ):
                old_auto = round(analysis.content_size[0] / analysis.content_size[1], 4)
                if abs(game.content_aspect - old_auto) < 0.002:
                    game.content_aspect = 0.0
                    self._persist_current()
            resolved_aspect = (
                analysis.content_aspect if game.content_aspect < 0 else game.content_aspect
            )
            self.aspect_spin.setValue(float(resolved_aspect or 0.0))
            self.create_launcher_check.setChecked(self.store.settings.create_launcher)
            is_rpgm = rpgmaker.is_supported_engine(analysis.engine.key)
            self.rpgmaker_card.setVisible(is_rpgm)
            self.rpgmaker_plugin_label.setVisible(is_rpgm)
            self.rpgmaker_plugin_value.setVisible(is_rpgm)
            self._refresh_rpgmaker_card()
            is_renpy = renpy.is_supported_engine(analysis.engine.key)
            self.renpy_card.setVisible(is_renpy)
            self.renpy_urm_label.setVisible(is_renpy)
            self.renpy_urm_value.setVisible(is_renpy)
            self._refresh_renpy_card()
            self._refresh_install_card()
            self._update_footer()
        finally:
            self._loading = False

    def _select_variant(self, key: str) -> None:
        for row in range(self.variant_list.count()):
            item = self.variant_list.item(row)
            if item.data(ROLE_VARIANT_KEY) == key:
                self.variant_list.setCurrentRow(row)
                return
        self.variant_list.setCurrentRow(0)

    def _refresh_dll_combo(self, analysis: detect.GameAnalysis) -> None:
        self.dll_combo.blockSignals(True)
        self.dll_combo.clear()
        auto = "automático"
        try:
            auto = installer.resolve_dll_name(analysis.game_dir, analysis, "")
        except installer.InstallError:
            auto = "conflito de nomes"
        self.dll_combo.addItem(f"Automático ({auto})", "")
        for name in detect.DLL_CHOICES.get(analysis.api, ()):
            self.dll_combo.addItem(name, name)
        override = self.current_game.dll_override if self.current_game else ""
        index = self.dll_combo.findData(override)
        if index < 0:
            if self.current_game is not None:
                self.current_game.dll_override = ""
            index = 0
        self.dll_combo.setCurrentIndex(index)
        self.dll_combo.blockSignals(False)

    def _on_dll_changed(self, _index: int) -> None:
        if self._loading or self.current_game is None:
            return
        self.current_game.dll_override = self.dll_combo.currentData() or ""
        self._persist_current()
        self._refresh_install_card()
        self._update_footer()

    # ------------------------------------------------------------------
    # user edits
    # ------------------------------------------------------------------
    def _on_variant_changed(self, row: int) -> None:
        if self._loading or row < 0:
            return
        item = self.variant_list.item(row)
        if item is None or self.current_game is None:
            return
        self.current_game.variant = item.data(ROLE_VARIANT_KEY)
        self._persist_current()
        self._update_footer()

    def _on_margin_changed(self, value: int) -> None:
        if self._loading or self.current_game is None:
            return
        self.current_game.top_margin = int(value)
        self._persist_current()
        self._update_footer()

    def _on_aspect_changed(self, value: float) -> None:
        if self._loading or self.current_game is None:
            return
        self.current_game.content_aspect = float(value)
        self._persist_current()
        self._update_footer()

    def _on_launcher_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        self.store.settings.create_launcher = checked
        self.store.save_settings()

    def _on_rpgmaker_plugin_toggled(self, plugin_key: str, checked: bool) -> None:
        if self._loading or self.current_game is None:
            return
        game = self.current_game
        toggle = {
            "hide_textbox": self.rpgmaker_plugin_toggle,
            "no_alt_skip": self.rpgmaker_no_alt_toggle,
            "save_slots_100": self.rpgmaker_save_slots_toggle,
        }[plugin_key]
        try:
            installer.set_rpgmaker_plugin(self.store, game, plugin_key, checked, status=self._log)
        except Exception as exc:  # noqa: BLE001
            toggle.blockSignals(True)
            toggle.setChecked(not checked)
            toggle.blockSignals(False)
            self._on_task_error(str(exc), "", exc)
            return
        self._refresh_rpgmaker_card()
        self._refresh_install_card()
        self._update_footer()
        self._refresh_games(select_id=game.id)

    def _on_renpy_urm_toggled(self, checked: bool) -> None:
        if self._loading or self.current_game is None or self.task is not None:
            return
        game = self.current_game
        preferred = self.store.settings.urm_version

        def body(log, progress):
            return installer.set_renpy_urm(
                self.store,
                game,
                checked,
                preferred_version=preferred,
                status=log,
                progress=progress,
            )

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(done * 100 / total))
                self.footer_status.setText(
                    f"Baixando Universal Ren'Py Mod... {done / 1048576:.1f} / {total / 1048576:.1f} MB"
                )
            else:
                self.progress.setRange(0, 0)

        def on_result(_result) -> None:
            self._set_busy(False)
            self._refresh_renpy_card()
            self._refresh_install_card()
            self._update_footer()
            self._refresh_games(select_id=game.id)

        def on_error(message: str, trace: str, error: object | None = None) -> None:
            self.renpy_urm_toggle.blockSignals(True)
            self.renpy_urm_toggle.setChecked(not checked)
            self.renpy_urm_toggle.blockSignals(False)
            self._on_task_error(message, trace, error)

        verb = "Instalando Universal Ren'Py Mod..." if checked else "Removendo Universal Ren'Py Mod..."
        self._set_busy(True, verb)
        self.task = run_task(body, self._log, on_progress, on_result, on_error)

    def _on_engine_override(self, _index: int) -> None:
        if self._loading or self.current_game is None:
            return
        self.current_game.engine_override = self.engine_combo.currentData() or ""
        self._persist_current()
        game = self.current_game
        QTimer.singleShot(0, lambda: self._load_game(game))

    def _on_api_override(self, _index: int) -> None:
        if self._loading or self.current_game is None:
            return
        self.current_game.api_override = self.api_combo.currentData() or ""
        self._persist_current()
        game = self.current_game
        QTimer.singleShot(0, lambda: self._load_game(game))

    def _persist_current(self) -> None:
        if self.current_game is not None:
            self.store.add_or_update(self.current_game)

    def _resolved_aspect(self) -> float:
        if self.current_game is None:
            return 0.0
        if self.current_game.content_aspect >= 0:
            return self.current_game.content_aspect
        return self.analysis.content_aspect if self.analysis else 0.0

    def _options(self) -> installer.InstallOptions:
        variant_item = self.variant_list.currentItem()
        return installer.InstallOptions(
            variant=variant_item.data(ROLE_VARIANT_KEY) if variant_item else anime4k.DEFAULT_VARIANT,
            top_margin=int(self.margin_spin.value()),
            content_aspect=self._resolved_aspect(),
            dll_name=self.dll_combo.currentData() or "",
            reshade_version=self.store.settings.reshade_version,
            create_launcher=self.create_launcher_check.isChecked(),
            rpgmaker_hide_textbox=(
                bool(self.current_game.rpgmaker_hide_textbox) if self.current_game else True
            ),
            rpgmaker_no_alt_skip=(
                bool(self.current_game.rpgmaker_no_alt_skip) if self.current_game else True
            ),
            rpgmaker_save_slots_100=(
                bool(self.current_game.rpgmaker_save_slots_100) if self.current_game else True
            ),
            renpy_urm=(
                bool(self.current_game.renpy_urm) if self.current_game else False
            ),
            urm_version=self.store.settings.urm_version,
        )

    def _refresh_rpgmaker_card(self) -> None:
        game = self.current_game
        analysis = self.analysis
        if game is None or analysis is None or not rpgmaker.is_supported_engine(analysis.engine.key):
            return

        has_plugins = bool(analysis.rpgmaker_plugins_js)
        can_toggle = has_plugins and game.exe_path.is_file() and self.task is None

        hide_active = installer.is_rpgmaker_plugin_active(game.game_dir, "hide_textbox") if has_plugins else False
        self.rpgmaker_plugin_toggle.blockSignals(True)
        self.rpgmaker_plugin_toggle.setEnabled(can_toggle)
        self.rpgmaker_plugin_toggle.setChecked(hide_active)
        self.rpgmaker_plugin_toggle.blockSignals(False)

        if not has_plugins:
            self.rpgmaker_plugin_status.setText(
                "plugins.js não encontrado (jogo compactado ou estrutura NW.js não padrão)."
            )
        elif hide_active:
            self.rpgmaker_plugin_status.setText(
                f"Ativo ({rpgmaker.PLUGIN_FILE} registrado em {analysis.rpgmaker_plugins_js}). "
                "Pressione H no jogo para ocultar/exibir a caixa de texto."
            )
        elif game.rpgmaker_hide_textbox:
            self.rpgmaker_plugin_status.setText(
                "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
            )
        else:
            self.rpgmaker_plugin_status.setText("Desativado — ative o interruptor para adicionar ao jogo.")

        no_alt_active = installer.is_rpgmaker_plugin_active(game.game_dir, "no_alt_skip") if has_plugins else False
        self.rpgmaker_no_alt_toggle.blockSignals(True)
        self.rpgmaker_no_alt_toggle.setEnabled(can_toggle)
        self.rpgmaker_no_alt_toggle.setChecked(no_alt_active)
        self.rpgmaker_no_alt_toggle.blockSignals(False)

        if not has_plugins:
            self.rpgmaker_no_alt_status.setText(
                "plugins.js não encontrado (jogo compactado ou estrutura NW.js não padrão)."
            )
        elif no_alt_active:
            self.rpgmaker_no_alt_status.setText(
                f"Ativo ({rpgmaker.NO_ALT_SKIP_FILE}). Alt e Alt+Tab não pulam diálogos; Ctrl continua funcionando."
            )
        elif game.rpgmaker_no_alt_skip:
            self.rpgmaker_no_alt_status.setText(
                "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
            )
        else:
            self.rpgmaker_no_alt_status.setText(
                "Desativado — ative o interruptor para impedir que Alt / Alt+Tab pule texto."
            )

        save_slots_active = (
            installer.is_rpgmaker_plugin_active(game.game_dir, "save_slots_100") if has_plugins else False
        )
        self.rpgmaker_save_slots_toggle.blockSignals(True)
        self.rpgmaker_save_slots_toggle.setEnabled(can_toggle)
        self.rpgmaker_save_slots_toggle.setChecked(save_slots_active)
        self.rpgmaker_save_slots_toggle.blockSignals(False)

        if not has_plugins:
            self.rpgmaker_save_slots_status.setText(
                "plugins.js não encontrado (jogo compactado ou estrutura NW.js não padrão)."
            )
        elif save_slots_active:
            self.rpgmaker_save_slots_status.setText(
                f"Ativo ({rpgmaker.SAVE_SLOTS_100_FILE}). 100 slots manuais de save liberados (MV e MZ)."
            )
        elif game.rpgmaker_save_slots_100:
            self.rpgmaker_save_slots_status.setText(
                "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
            )
        else:
            self.rpgmaker_save_slots_status.setText(
                "Desativado — ative o interruptor para expandir o limite para 100 slots de save."
            )

        record = nwjs.load_update_record(game.id)
        current_ver = record.get("version") or analysis.nwjs_version or "desconhecida"
        bits_text = f"{analysis.bits} bits" if analysis.bits else "? bits"
        cached = nwjs.newest_cached(nwjs.DEFAULT_ARCH)
        cache_hint = (
            f"Cache local: NW.js {cached.version} ({cached.bits} bits)"
            if cached
            else "Baixa o NW.js oficial de nwjs.io 1x e reutiliza em todos os jogos"
        )
        updated_tag = " · atualizado pelo AniShade" if record else ""
        self.nwjs_status_label.setText(
            f"No jogo: {current_ver} ({bits_text}{updated_tag})\n"
            f"{cache_hint} · corrige package.json (name ausente, autoplay, js-flags, compatibilidade MV)."
        )
        self.nwjs_restore_button.setVisible(nwjs.has_backup(game.id))
        self.nwjs_update_button.setEnabled(game.exe_path.is_file() and self.task is None)
        self.nwjs_restore_button.setEnabled(game.exe_path.is_file() and self.task is None)

    def _refresh_renpy_card(self) -> None:
        game = self.current_game
        analysis = self.analysis
        if game is None or analysis is None or not renpy.is_supported_engine(analysis.engine.key):
            return

        has_game_dir = bool(analysis.renpy_game_dir)
        can_toggle = has_game_dir and game.exe_path.is_file() and self.task is None
        urm_active = installer.is_renpy_urm_active(game.game_dir) if has_game_dir else False

        self.renpy_urm_toggle.blockSignals(True)
        self.renpy_urm_toggle.setEnabled(can_toggle)
        self.renpy_urm_toggle.setChecked(urm_active)
        self.renpy_urm_toggle.blockSignals(False)

        cached = renpy.newest_cached()
        if not has_game_dir:
            self.renpy_urm_status.setText(
                "Pasta game/ não encontrada ao lado do executável."
            )
        elif urm_active:
            meta = installer.load_renpy_meta(game.id)
            version = str(meta.get("version") or "")
            ver_tag = f"v{version} · " if version else ""
            self.renpy_urm_status.setText(
                f"Ativo ({ver_tag}{analysis.renpy_game_dir}/{renpy.URM_FILENAME}). "
                "Menu de variáveis, cenas, escolhas, saves e customização dentro do jogo."
            )
        elif game.renpy_urm:
            self.renpy_urm_status.setText(
                "Não instalado ainda — ative o interruptor agora ou ele será instalado junto com o ReShade."
            )
        elif cached:
            self.renpy_urm_status.setText(
                f"Desativado — ative para instalar {renpy.URM_FILENAME} em {analysis.renpy_game_dir}/ "
                f"(cache local: v{cached.version})."
            )
        else:
            self.renpy_urm_status.setText(
                f"Desativado — baixa {renpy.URM_FILENAME} de 0x52.dev uma única vez, salva em cache "
                f"e instala em {analysis.renpy_game_dir}/."
            )

    # ------------------------------------------------------------------
    # status / install
    # ------------------------------------------------------------------
    def _refresh_install_card(self) -> None:
        game = self.current_game
        if game is None:
            return
        manifest = installer.load_manifest(game.id)
        state = installer.inspect(game)
        if manifest:
            version = manifest.get("reshade_version", "?")
            bits = manifest.get("bits", game.bits)
            self.reshade_value.setText(f"{version} ({bits} bits)")
            self.dll_combo.setToolTip(f"Instalado como {manifest.get('dll_name', '—')}")
            self.preset_value.setText(str(game.preset_path))
            self.shaders_value.setText(
                f"{len(manifest.get('techniques', []))} técnicas em {anime4k.SHADER_SUBDIR.as_posix()}"
            )
            self.launcher_value.setText(manifest.get("launcher") or "—")
            self.open_preset_button.setEnabled(True)
            if state.problems:
                self.problems_label.setText("\n".join(f"• {item}" for item in state.problems))
                self.problems_label.show()
            else:
                self.problems_label.hide()
        else:
            self.reshade_value.setText("não instalado")
            self.dll_combo.setToolTip(
                "Nome da DLL proxy. 'Automático' escolhe a melhor opção livre na pasta do jogo."
            )
            self.preset_value.setText(str(game.preset_path))
            self.shaders_value.setText(
                f"{len(game.techniques())} técnicas planejadas"
            )
            self.launcher_value.setText("—")
            self.open_preset_button.setEnabled(game.preset_path.is_file())
            self.problems_label.hide()

        if self.analysis and rpgmaker.is_supported_engine(self.analysis.engine.key):
            active_labels: list[str] = []
            if installer.is_rpgmaker_plugin_active(game.game_dir, "hide_textbox"):
                active_labels.append("Ocultar texto (H)")
            if installer.is_rpgmaker_plugin_active(game.game_dir, "no_alt_skip"):
                active_labels.append("Sem pular com Alt")
            if installer.is_rpgmaker_plugin_active(game.game_dir, "save_slots_100"):
                active_labels.append("100 slots de save")
            if active_labels:
                self.rpgmaker_plugin_value.setText(" · ".join(active_labels))
            elif self.analysis.rpgmaker_plugins_js:
                if game.rpgmaker_hide_textbox or game.rpgmaker_no_alt_skip or game.rpgmaker_save_slots_100:
                    self.rpgmaker_plugin_value.setText("serão instalados com o ReShade")
                else:
                    self.rpgmaker_plugin_value.setText("desativados")
            else:
                self.rpgmaker_plugin_value.setText("plugins.js não encontrado")

        if self.analysis and renpy.is_supported_engine(self.analysis.engine.key):
            if installer.is_renpy_urm_active(game.game_dir):
                meta = installer.load_renpy_meta(game.id)
                ver = str(meta.get("version") or "")
                suffix = f" v{ver}" if ver else ""
                self.renpy_urm_value.setText(f"Universal Ren'Py Mod{suffix} ({renpy.URM_FILENAME})")
            elif self.analysis.renpy_game_dir:
                if game.renpy_urm:
                    self.renpy_urm_value.setText("será instalado com o ReShade")
                else:
                    self.renpy_urm_value.setText("desativado")
            else:
                self.renpy_urm_value.setText("pasta game/ não encontrada")

    def _update_footer(self) -> None:
        game = self.current_game
        analysis = self.analysis
        if game is None or analysis is None:
            self.install_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)
            return

        manifest = installer.load_manifest(game.id)
        installed = bool(manifest) and (game.game_dir / manifest.get("dll_name", "")).is_file()
        differs = False
        if manifest:
            try:
                expected_dll = installer.resolve_dll_name(
                    game.game_dir, analysis, game.dll_override
                )
            except installer.InstallError:
                expected_dll = ""
            differs = (
                manifest.get("variant") != game.variant
                or int(manifest.get("top_margin", 0)) != int(game.top_margin)
                or int(manifest.get("shader_version", 1)) < anime4k.SHADER_VERSION
                or not manifest.get("splash_hidden", False)
                or abs(float(manifest.get("content_aspect", 0)) - self._resolved_aspect()) > 0.001
                or manifest.get("api") != analysis.api
                or (expected_dll and manifest.get("dll_name") != expected_dll)
                or (
                    rpgmaker.is_supported_engine(analysis.engine.key)
                    and bool(analysis.rpgmaker_plugins_js)
                    and (
                        bool(manifest.get("rpgmaker_plugin")) != bool(game.rpgmaker_hide_textbox)
                        or bool((manifest.get("rpgmaker_plugins") or {}).get("no_alt_skip"))
                        != bool(game.rpgmaker_no_alt_skip)
                        or bool((manifest.get("rpgmaker_plugins") or {}).get("save_slots_100"))
                        != bool(game.rpgmaker_save_slots_100)
                    )
                )
                or (
                    renpy.is_supported_engine(analysis.engine.key)
                    and bool(analysis.renpy_game_dir)
                    and bool(manifest.get("renpy_urm")) != bool(game.renpy_urm)
                )
            )

        if analysis.api == "vulkan":
            self.install_button.setText("Vulkan não suportado")
            self.install_button.setEnabled(False)
            self.footer_status.setText(
                "Este jogo usa Vulkan: o ReShade não carrega por proxy DLL. "
                "Inicie em Direct3D 11/OpenGL ou use a injeção global."
            )
        elif not installed:
            self.install_button.setText("Instalar ReShade + Anime4K")
            self.install_button.setEnabled(True)
            self.footer_status.setText("Pronto para instalar. O ReShade é baixado apenas uma vez.")
        elif differs:
            self.install_button.setText("Aplicar alterações")
            self.install_button.setEnabled(True)
            self.footer_status.setText("Alterações de shader pendentes (não instaladas ainda).")
        else:
            self.install_button.setText("Reinstalar")
            self.install_button.setEnabled(True)
            self.footer_status.setText(
                "Instalado. Abra o jogo e pressione Home para abrir o overlay do ReShade."
            )

        self.uninstall_button.setEnabled(installed)
        self.play_button.setEnabled(game.exe_path.is_file())
        if not game.exe_path.is_file():
            self.footer_status.setText("Executável não encontrado — o jogo foi movido ou removido?")
            self.install_button.setEnabled(False)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.install_button.setEnabled(not busy)
        self.uninstall_button.setEnabled(not busy)
        self.add_button.setEnabled(not busy)
        self.reanalyze_button.setEnabled(not busy)
        self.rpgmaker_plugin_toggle.setEnabled(not busy and bool(self.analysis and self.analysis.rpgmaker_plugins_js))
        self.rpgmaker_no_alt_toggle.setEnabled(not busy and bool(self.analysis and self.analysis.rpgmaker_plugins_js))
        self.rpgmaker_save_slots_toggle.setEnabled(
            not busy and bool(self.analysis and self.analysis.rpgmaker_plugins_js)
        )
        self.renpy_urm_toggle.setEnabled(
            not busy and bool(self.analysis and self.analysis.renpy_game_dir)
        )
        self.nwjs_update_button.setEnabled(not busy)
        self.nwjs_restore_button.setEnabled(not busy)
        if busy:
            self.progress.show()
            if message:
                self.footer_status.setText(message)
        else:
            self.task = None
            self.banner.button.setEnabled(True)
            self.progress.hide()
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self._refresh_rpgmaker_card()
            self._refresh_renpy_card()
            self._update_footer()

    def _start_install(self) -> None:
        game = self.current_game
        analysis = self.analysis
        if game is None or analysis is None or self.task is not None:
            return
        options = self._options()

        def body(log, progress):
            return installer.install(
                self.store,
                game,
                options,
                status=log,
                progress=progress,
                analysis=analysis,
            )

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(done * 100 / total))

        def on_result(report: installer.InstallReport) -> None:
            self._set_busy(False)
            self._log(
                f"Instalado: {report.dll_name} + {len(report.techniques)} passes "
                f"(ReShade {report.reshade_version})."
            )
            self._refresh_games(select_id=game.id)
            self._refresh_rpgmaker_card()
            self._refresh_renpy_card()
            self._refresh_install_card()
            self._update_footer()
            self._show_success(report)

        self._set_busy(True, "Instalando...")
        self.task = run_task(body, self._log, on_progress, on_result, self._on_task_error)

    def _show_success(self, report: installer.InstallReport) -> None:
        plugin_lines: list[str] = []
        for path_str in report.rpgmaker_plugins:
            fname = Path(path_str).name
            if fname == rpgmaker.PLUGIN_FILE:
                plugin_lines.append(f"• Plugin RPG Maker: {fname} (tecla H oculta a caixa de texto)\n")
            elif fname == rpgmaker.NO_ALT_SKIP_FILE:
                plugin_lines.append(f"• Plugin RPG Maker: {fname} (Alt / Alt+Tab não pula texto)\n")
            elif fname == rpgmaker.SAVE_SLOTS_100_FILE:
                plugin_lines.append(f"• Plugin RPG Maker: {fname} (100 slots de save)\n")
            else:
                plugin_lines.append(f"• Plugin RPG Maker: {fname}\n")
        if report.renpy_urm:
            ver_suffix = f" v{report.renpy_urm_version}" if report.renpy_urm_version else ""
            plugin_lines.append(
                f"• Mod Ren'Py: Universal Ren'Py Mod{ver_suffix} ({Path(report.renpy_urm).name})\n"
            )
        plugin_line = "".join(plugin_lines)
        extra = ""
        if report.launcher:
            extra = f"\n\nLauncher criado: {report.launcher}"
        QMessageBox.information(
            self,
            "AniShade",
            "Pronto!\n\n"
            f"• DLL: {report.dll_name}\n"
            f"• Preset: {anime4k.PRESET_NAME}\n"
            f"• Cadeia: {', '.join(report.techniques)}\n"
            f"{plugin_line}\n"
            "Abra o jogo e pressione Home para abrir o overlay do ReShade."
            f"{extra}",
        )

    def _start_uninstall(self) -> None:
        game = self.current_game
        if game is None or self.task is not None:
            return
        confirm = QMessageBox.question(
            self,
            "Desinstalar",
            f"Remover o ReShade e os shaders Anime4K de “{game.name}”?\n\n"
            "Somente arquivos criados pelo AniShade são removidos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        def body(log, progress):
            return installer.uninstall(self.store, game, status=log)

        def on_result(removed) -> None:
            self._set_busy(False)
            self._log(f"ReShade removido ({len(removed)} arquivos).")
            self._refresh_games(select_id=game.id)
            self._refresh_rpgmaker_card()
            self._refresh_renpy_card()
            self._refresh_install_card()
            self._update_footer()

        self._set_busy(True, "Desinstalando...")
        self.task = run_task(body, self._log, lambda *_: None, on_result, self._on_task_error)

    def _start_update_nwjs(self) -> None:
        game = self.current_game
        if game is None or self.task is not None:
            return
        cached = nwjs.newest_cached(nwjs.DEFAULT_ARCH)
        source_note = (
            f"Usará o NW.js {cached.version} (64 bits) do cache local."
            if cached
            else "O NW.js oficial (64 bits) será baixado de nwjs.io uma única vez e salvo em cache para os próximos jogos."
        )
        confirm = QMessageBox.question(
            self,
            "Atualizar NW.js",
            f"Atualizar o runtime NW.js de “{game.name}”?\n\n"
            f"{source_note}\n"
            "Os arquivos originais do NW.js e o package.json serão salvos em backup "
            "(você pode restaurar depois).\n"
            "Correções automáticas aplicadas: campo 'name' ausente no package.json, "
            "autoplay de áudio, flags V8 obsoletas e compatibilidade process.mainModule.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        preferred = self.store.settings.nwjs_version

        def body(log, progress):
            return installer.update_nwjs(
                self.store,
                game,
                preferred_version=preferred,
                arch=nwjs.DEFAULT_ARCH,
                status=log,
                progress=progress,
            )

        def on_progress(done: int, total: int) -> None:
            if total > 0:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(done * 100 / total))
                self.footer_status.setText(
                    f"Baixando NW.js... {done / 1048576:.1f} / {total / 1048576:.1f} MB"
                )
            else:
                self.progress.setRange(0, 0)

        def on_result(report: nwjs.NwjsUpdateReport) -> None:
            self._set_busy(False)
            self._log(f"NW.js atualizado para {report.version} ({report.arch}).")
            self._load_game(game)
            self._refresh_games(select_id=game.id)
            self._show_nwjs_success(report)

        self._set_busy(True, "Atualizando NW.js...")
        self.task = run_task(body, self._log, on_progress, on_result, self._on_task_error)

    def _show_nwjs_success(self, report: nwjs.NwjsUpdateReport) -> None:
        lines = [
            "NW.js atualizado com sucesso!",
            "",
            f"• Versão: NW.js {report.version} ({report.arch})",
            f"• Arquivos atualizados: {report.files_updated}",
        ]
        if report.reshade_realigned:
            lines.append("• DLL do ReShade atualizada automaticamente para 64 bits.")
        if report.fixes_applied:
            lines.append("")
            lines.append("Correções aplicadas:")
            for fix in report.fixes_applied:
                lines.append(f"  - {fix}")
        if report.warnings:
            lines.append("")
            lines.append("Avisos:")
            for warning in report.warnings:
                lines.append(f"  ! {warning}")
        QMessageBox.information(self, "NW.js atualizado", "\n".join(lines))

    def _start_restore_nwjs(self) -> None:
        game = self.current_game
        if game is None or self.task is not None:
            return
        confirm = QMessageBox.question(
            self,
            "Restaurar NW.js original",
            f"Restaurar os arquivos originais do NW.js e o package.json de “{game.name}”?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        def body(log, progress):
            return installer.restore_nwjs(self.store, game, status=log)

        def on_result(restored) -> None:
            self._set_busy(False)
            self._log(f"NW.js original restaurado ({len(restored)} arquivos).")
            self._load_game(game)
            self._refresh_games(select_id=game.id)

        self._set_busy(True, "Restaurando NW.js...")
        self.task = run_task(body, self._log, lambda *_: None, on_result, self._on_task_error)

    def _on_task_error(self, message: str, trace: str, error: object | None = None) -> None:
        self.task = None
        self._set_busy(False)
        self._log(f"Erro: {message}")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("Falha na operação")
        box.setText(message)
        if trace:
            box.setDetailedText(trace)
        box.exec()
        if isinstance(error, installer.AdminRequired) or "administrador" in message.lower():
            answer = QMessageBox.question(
                self,
                "Permissão necessária",
                "Reiniciar o AniShade como administrador para continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                if winapi.relaunch_as_admin(sys.argv):
                    self.close()

    # ------------------------------------------------------------------
    # game management
    # ------------------------------------------------------------------
    def _pick_game(self) -> None:
        start = self.store.settings.last_dir or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolha o executável do jogo",
            start,
            "Executáveis (*.exe);;Todos os arquivos (*.*)",
        )
        if path:
            self._add_game(path)

    def _add_game(self, path: str) -> None:
        exe = Path(path).resolve()
        if exe.suffix.lower() != ".exe" or not exe.is_file():
            QMessageBox.warning(self, "Arquivo inválido", "Selecione um arquivo .exe válido.")
            return
        existing = self.store.find_by_exe(exe)
        if existing:
            self._refresh_games(select_id=existing.id)
            self._log(f"“{existing.name}” já está na biblioteca.")
            return

        try:
            analysis = detect.analyze(exe)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Não foi possível analisar o executável:\n{exc}")
            return

        game = Game(
            id=game_id_for(exe),
            name=analysis.suggested_name(),
            exe=str(exe),
            engine_key=analysis.engine.key,
            engine_name=analysis.engine.name,
            api=analysis.api,
            dll_name=analysis.dll_name,
            bits=analysis.bits or 64,
            variant=self.store.settings.default_variant,
            top_margin=self.store.settings.default_top_margin,
            content_aspect=-1.0,
            rpgmaker_hide_textbox=self.store.settings.rpgmaker_hide_textbox,
            rpgmaker_no_alt_skip=self.store.settings.rpgmaker_no_alt_skip,
            rpgmaker_save_slots_100=self.store.settings.rpgmaker_save_slots_100,
            renpy_urm=self.store.settings.renpy_urm,
            detected={
                "evidence": analysis.engine_evidence,
                "warnings": analysis.warnings,
                "notes": analysis.notes,
            },
        )
        self.store.add_or_update(game)
        self.store.settings.last_dir = str(exe.parent)
        self.store.save_settings()
        self._refresh_games(select_id=game.id)
        self._log(f"Adicionado: {game.name} ({analysis.engine.name}).")

    def _rename_game(self) -> None:
        game = self.current_game
        if game is None:
            return
        name, ok = QInputDialog.getText(self, "Renomear", "Nome exibido:", text=game.name)
        if ok and name.strip():
            game.name = name.strip()
            self.store.add_or_update(game)
            self._refresh_games(select_id=game.id)
            self.game_title.setText(game.name)

    def _game_context_menu(self, position) -> None:
        item = self.game_list.itemAt(position)
        if item is None:
            return
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        play = menu.addAction("Jogar")
        rename = menu.addAction("Renomear")
        folder = menu.addAction("Abrir pasta")
        menu.addSeparator()
        remove = menu.addAction("Remover da biblioteca")
        chosen = menu.exec(self.game_list.mapToGlobal(position))
        if chosen == play:
            self._launch_game()
        elif chosen == rename:
            self._rename_game()
        elif chosen == folder:
            self._open_game_folder()
        elif chosen == remove:
            self._remove_game()

    def _remove_game(self) -> None:
        game = self.current_game
        if game is None:
            return
        installed = bool(installer.load_manifest(game.id))
        box = QMessageBox(self)
        box.setWindowTitle("Remover jogo")
        box.setText(f"Remover “{game.name}” da biblioteca?")
        if installed:
            box.setInformativeText(
                "O jogo tem o ReShade instalado pelo AniShade. Você pode desinstalar antes de remover."
            )
        remove_only = box.addButton("Só remover da lista", QMessageBox.AcceptRole)
        uninstall_button = box.addButton("Desinstalar e remover", QMessageBox.DestructiveRole) if installed else None
        cancel = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == cancel:
            return

        if clicked == uninstall_button and installed:
            def body(log, progress):
                installer.uninstall(self.store, game, status=log)
                self.store.remove(game.id)

            def on_result(_):
                self.current_game = None
                self._set_busy(False)
                self._log(f"“{game.name}” desinstalado e removido.")
                self._refresh_games()

            self._set_busy(True, "Desinstalando...")
            self.task = run_task(body, self._log, lambda *_: None, on_result, self._on_task_error)
        elif clicked == remove_only:
            self.store.remove(game.id)
            self.current_game = None
            self._refresh_games()
            self._log("Jogo removido da biblioteca.")

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def _launch_game(self) -> None:
        game = self.current_game
        if game is None:
            return
        if not game.exe_path.is_file():
            QMessageBox.warning(self, "Jogo ausente", "O executável não existe mais neste caminho.")
            return
        env = self.analysis.env if self.analysis else {}
        args = self.analysis.args if self.analysis else []
        try:
            winapi.launch(game.exe_path, args=list(args), env=dict(env))
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao iniciar", str(exc))
            return
        self.store.touch_played(game)
        detail = ""
        if env:
            detail = " (" + ", ".join(f"{k}={v}" for k, v in env.items()) + ")"
        self._log(f"Iniciando {game.exe_path.name}{detail}")

    def _open_game_folder(self) -> None:
        if self.current_game is None:
            return
        folder = self.current_game.game_dir
        if not folder.is_dir():
            QMessageBox.warning(self, "Pasta ausente", f"A pasta não existe mais:\n{folder}")
            return
        winapi.open_folder(folder)

    def _open_preset(self) -> None:
        game = self.current_game
        if game is None:
            return
        if not game.preset_path.is_file():
            QMessageBox.information(
                self, "Preset ausente", "O preset AniShade.ini ainda não foi criado. Instale primeiro."
            )
            return
        try:
            winapi.open_file(game.preset_path)
        except OSError as exc:
            QMessageBox.warning(self, "Erro ao abrir", str(exc))

    def _reanalyze(self) -> None:
        if self.current_game is not None:
            self._load_game(self.current_game)
            self._refresh_games(select_id=self.current_game.id)
            self._log("Detecção atualizada.")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.store, self)
        if dialog.exec() == QDialog.Accepted:
            self._log("Configurações salvas.")
            self.banner.setVisible(not reshade.list_cached())
            if self.current_game is not None:
                self._load_game(self.current_game)

    # ------------------------------------------------------------------
    # window events
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".exe"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".exe"):
                self._add_game(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.task is not None:
            QMessageBox.information(
                self,
                "Operação em andamento",
                "Aguarde a operação atual terminar antes de fechar o AniShade.",
            )
            event.ignore()
            return
        self.store.settings.window_width = self.width()
        self.store.settings.window_height = self.height()
        self.store.save_settings()
        super().closeEvent(event)
