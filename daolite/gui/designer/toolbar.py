from PyQt5.QtWidgets import QToolBar, QToolButton, QFrame, QSizePolicy, QLabel, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from .components import ComponentType

def create_toolbar(main_window):
    print('[DEBUG] Entering create_toolbar')
    # Remove any existing toolbars
    for tb in main_window.findChildren(QToolBar):
        print(f'[DEBUG] Removing toolbar: {tb}')
        main_window.removeToolBar(tb)
        print(f'[DEBUG] Removed toolbar: {tb}')

    toolbar = QToolBar("Main Toolbar")
    print('[DEBUG] Created QToolBar')
    toolbar.setMovable(False)
    toolbar.setFloatable(False)
    toolbar.setIconSize(QSize(32, 32))
    toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    main_window.addToolBar(Qt.TopToolBarArea, toolbar)
    print('[DEBUG] Added toolbar to main window')

    theme = getattr(main_window, 'theme', 'light')
    print(f'[DEBUG] Toolbar theme: {theme}')
    if theme == 'dark':
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #27304a, stop:1 #232b3a);
                border: none;
                padding: 8px 4px;
            }
            QToolBar QLabel, QToolBar QPushButton, QToolBar QToolButton {
                color: #f2f6fa;
                font-weight: 500;
            }
            QToolBar QToolButton {
                background: #2d3952;
                border: 1.5px solid #3a4660;
                border-radius: 7px;
                padding: 6px 14px;
                margin: 2px 0;
                font-size: 13px;
            }
            QToolBar QToolButton:hover {
                background: #36415a;
                border: 1.5px solid #4a90e2;
                color: #b3e1ff;
            }
            QToolBar QToolButton:pressed {
                background: #232b3a;
            }
        """)
    else:
        toolbar.setStyleSheet("QToolBar { background: #e7f2fa; border: none; padding: 8px 4px; } QToolBar QLabel, QToolBar QPushButton, QToolBar QToolButton { color: #375a7f; }")
    print('[DEBUG] Set toolbar stylesheet')

    def add_section_label(text):
        print(f'[DEBUG] Adding section label: {text}')
        label = QLabel(f"  <b>{text}</b>  ")
        label.setStyleSheet("font-size: 14px; color: #1a1a1a; margin: 0 8px; letter-spacing: 0.5px;")
        toolbar.addWidget(label)

    def add_separator():
        print('[DEBUG] Adding separator')
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("color: #b0c4de; margin: 0 8px;")
        sep.setFixedHeight(40)
        toolbar.addWidget(sep)

    # --- Add Computer Button ---
    print('[DEBUG] Adding Add Computer button')
    btn_add_computer = QToolButton()
    btn_add_computer.setIcon(QIcon.fromTheme("computer"))
    btn_add_computer.setText("Add Computer")
    btn_add_computer.setToolTip("Add a compute box (computer node) to the scene")
    btn_add_computer.clicked.connect(main_window._add_compute_box)
    btn_add_computer.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 15px; margin-right: 12px;")
    toolbar.addWidget(btn_add_computer)
    add_separator()

    # --- File Dropdown ---
    print('[DEBUG] Adding File dropdown')
    file_menu_btn = QToolButton()
    file_menu_btn.setIcon(QIcon.fromTheme("document-new"))
    file_menu_btn.setText("File")
    file_menu_btn.setPopupMode(QToolButton.InstantPopup)
    file_menu_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    file_menu_btn.setStyleSheet("color: #444; font-weight: bold; font-size: 13px;")
    file_menu = QMenu()
    act_new = file_menu.addAction(QIcon.fromTheme("document-new"), "New Pipeline")
    act_new.triggered.connect(main_window._new_pipeline)
    act_open = file_menu.addAction(QIcon.fromTheme("document-open"), "Open Pipeline")
    act_open.triggered.connect(main_window._load_pipeline)
    act_save = file_menu.addAction(QIcon.fromTheme("document-save"), "Save Pipeline")
    act_save.triggered.connect(main_window._save_pipeline)
    file_menu_btn.setMenu(file_menu)
    toolbar.addWidget(file_menu_btn)
    add_separator()

    # --- Components Section ---
    add_section_label("Components")
    comp_buttons = [
        ("Camera", ComponentType.CAMERA, "camera-photo"),
        ("Network", ComponentType.NETWORK, "network-wired"),
        ("Calibration", ComponentType.CALIBRATION, "color-balance"),
        ("Centroider", ComponentType.CENTROIDER, "view-split-left-right"),
        ("Reconstruction", ComponentType.RECONSTRUCTION, "system-run"),
        ("Control", ComponentType.CONTROL, "media-playback-start"),
    ]
    for label, ctype, icon in comp_buttons:
        print(f'[DEBUG] Adding component button: {label}')
        btn = QToolButton()
        btn.setIcon(QIcon.fromTheme(icon))
        btn.setText(label)
        btn.setToolTip(f"Add a {label.lower()} component")
        btn.clicked.connect(lambda _, t=ctype: main_window._add_component(t))
        btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn.setStyleSheet("color: #222; font-weight: 500;")
        toolbar.addWidget(btn)
    add_separator()

    # --- Actions Section ---
    add_section_label("Actions")
    print('[DEBUG] Adding Generate button')
    btn_generate = QToolButton()
    btn_generate.setIcon(QIcon.fromTheme("document-export"))
    btn_generate.setText("Generate")
    btn_generate.setToolTip("Generate pipeline code")
    btn_generate.setStyleSheet("color: #222; font-weight: 500;")
    btn_generate.setPopupMode(QToolButton.MenuButtonPopup)
    generate_menu = QMenu()
    act_gen_python = generate_menu.addAction("Generate Python")
    act_gen_json = generate_menu.addAction("Generate JSON")
    def gen_python():
        main_window.execution_method.setCurrentText("Python")
        main_window._generate_code()
    def gen_json():
        main_window.execution_method.setCurrentText("JSON")
        main_window._generate_code()
    act_gen_python.triggered.connect(gen_python)
    act_gen_json.triggered.connect(gen_json)
    btn_generate.setMenu(generate_menu)
    btn_generate.clicked.connect(gen_python)
    toolbar.addWidget(btn_generate)

    print('[DEBUG] Adding Run button')
    btn_run = QToolButton()
    btn_run.setIcon(QIcon.fromTheme("system-run"))
    btn_run.setText("Run")
    btn_run.setToolTip("Execute pipeline and display visualization")
    btn_run.setStyleSheet("color: #222; font-weight: 500;")
    btn_run.setPopupMode(QToolButton.MenuButtonPopup)
    run_menu = QMenu()
    act_run_python = run_menu.addAction("Run as Python")
    act_run_json = run_menu.addAction("Run as JSON")
    def run_python():
        main_window.execution_method.setCurrentText("Python")
        main_window._run_pipeline()
    def run_json():
        main_window.execution_method.setCurrentText("JSON")
        main_window._run_pipeline()
    act_run_python.triggered.connect(run_python)
    act_run_json.triggered.connect(run_json)
    btn_run.setMenu(run_menu)
    btn_run.clicked.connect(run_python)
    toolbar.addWidget(btn_run)
    add_separator()

    # --- View Section ---
    add_section_label("View")
    print('[DEBUG] Adding Zoom In button')
    btn_zoom_in = QToolButton()
    btn_zoom_in.setIcon(QIcon.fromTheme("zoom-in"))
    btn_zoom_in.setText("Zoom In")
    btn_zoom_in.setToolTip("Zoom in on the pipeline view")
    btn_zoom_in.clicked.connect(lambda: main_window.view.scale(1.2, 1.2))
    btn_zoom_in.setStyleSheet("color: #222; font-weight: 500;")
    toolbar.addWidget(btn_zoom_in)
    print('[DEBUG] Adding Zoom Out button')
    btn_zoom_out = QToolButton()
    btn_zoom_out.setIcon(QIcon.fromTheme("zoom-out"))
    btn_zoom_out.setText("Zoom Out")
    btn_zoom_out.setToolTip("Zoom out on the pipeline view")
    btn_zoom_out.clicked.connect(lambda: main_window.view.scale(0.8, 0.8))
    btn_zoom_out.setStyleSheet("color: #222; font-weight: 500;")
    toolbar.addWidget(btn_zoom_out)
    add_separator()

    print('[DEBUG] Exiting create_toolbar')
    main_window.statusBar().showMessage("Ready")
    return toolbar
