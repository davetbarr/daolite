from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QKeySequence
from .style_utils import save_theme, set_app_style
from .dialogs.misc_dialogs import ShortcutHelpDialog, StyledTextInputDialog
from .dialogs.resource_dialog import ResourceSelectionDialog
from daolite.gui.centroid_agenda_tool import show_centroid_agenda_tool

def create_menu(main_window):
    menu_bar = main_window.menuBar()

    # File menu
    file_menu = menu_bar.addMenu("&File")
    new_action = QAction("&New Pipeline", main_window)
    new_action.setShortcut(QKeySequence.New)
    new_action.triggered.connect(main_window._new_pipeline)
    file_menu.addAction(new_action)

    save_action = QAction("&Save Pipeline", main_window)
    save_action.setShortcut(QKeySequence.Save)
    save_action.triggered.connect(main_window._save_pipeline)
    file_menu.addAction(save_action)

    load_action = QAction("&Load Pipeline", main_window)
    load_action.setShortcut(QKeySequence.Open)
    load_action.triggered.connect(main_window._load_pipeline)
    file_menu.addAction(load_action)

    file_menu.addSeparator()

    generate_action = QAction("&Generate Code", main_window)
    generate_action.setShortcut("Ctrl+G")
    generate_action.triggered.connect(main_window._generate_code)
    file_menu.addAction(generate_action)

    export_config_action = QAction("Export Config &YAML", main_window)
    export_config_action.setShortcut("Ctrl+E")
    export_config_action.triggered.connect(main_window._export_config)
    file_menu.addAction(export_config_action)

    centroid_agenda_action = QAction("Centroid Agenda Tool", main_window)
    centroid_agenda_action.triggered.connect(lambda: show_centroid_agenda_tool(main_window))
    file_menu.addAction(centroid_agenda_action)

    file_menu.addSeparator()

    set_title_action = QAction("Set Pipeline Title...", main_window)
    set_title_action.triggered.connect(main_window._set_pipeline_title)
    file_menu.addAction(set_title_action)

    file_menu.addSeparator()

    exit_action = QAction("E&xit", main_window)
    exit_action.setShortcut(QKeySequence.Quit)
    exit_action.triggered.connect(main_window.close)
    file_menu.addAction(exit_action)

    # Edit menu
    edit_menu = menu_bar.addMenu("&Edit")
    undo_action = QAction("&Undo", main_window)
    undo_action.setShortcut(QKeySequence.Undo)
    undo_action.triggered.connect(main_window.undo_stack.undo)
    edit_menu.addAction(undo_action)

    redo_action = QAction("&Redo", main_window)
    redo_action.setShortcut(QKeySequence.Redo)
    redo_action.triggered.connect(main_window.undo_stack.redo)
    edit_menu.addAction(redo_action)

    rename_action = QAction("&Rename Selected", main_window)
    rename_action.setShortcut("Ctrl+R")
    rename_action.triggered.connect(main_window._rename_selected)
    edit_menu.addAction(rename_action)

    delete_action = QAction("&Delete Selected", main_window)
    delete_action.setShortcut(QKeySequence.Delete)
    delete_action.triggered.connect(main_window._delete_selected)
    edit_menu.addAction(delete_action)

    # View menu
    view_menu = menu_bar.addMenu("&View")
    zoom_in_action = QAction("Zoom &In", main_window)
    zoom_in_action.triggered.connect(lambda: main_window.view.scale(1.2, 1.2))
    view_menu.addAction(zoom_in_action)

    zoom_out_action = QAction("Zoom &Out", main_window)
    zoom_out_action.triggered.connect(lambda: main_window.view.scale(0.8, 0.8))
    view_menu.addAction(zoom_out_action)

    reset_zoom_action = QAction("&Reset Zoom", main_window)
    reset_zoom_action.triggered.connect(lambda: main_window.view.resetTransform())
    view_menu.addAction(reset_zoom_action)

    # --- Theme submenu ---
    view_menu.addSeparator()
    theme_menu = view_menu.addMenu("Theme")
    theme_group = []
    for label, key in [("System Default", "system"), ("Light", "light"), ("Dark", "dark")]:
        act = QAction(label, main_window, checkable=True)
        act.setChecked(main_window.theme == key)
        act.triggered.connect(lambda checked, k=key: main_window._set_theme(k))
        theme_menu.addAction(act)
        theme_group.append(act)
    main_window._theme_actions = theme_group

    # Help menu
    help_menu = menu_bar.addMenu("&Help")
    about_action = QAction("&About", main_window)
    about_action.triggered.connect(main_window._show_about)
    help_menu.addAction(about_action)

    shortcut_action = QAction("Keyboard Shortcuts", main_window)
    shortcut_action.setShortcut("Ctrl+H")
    shortcut_action.triggered.connect(main_window._show_shortcuts)
    help_menu.addAction(shortcut_action)
