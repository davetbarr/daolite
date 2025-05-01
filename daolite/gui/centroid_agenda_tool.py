"""
Centroid Agenda Generator GUI Tool

This tool allows users to load a readout order and sub-aperture map, set sub-aperture size and readout groups, and generate a centroid agenda.
"""

import sys
import numpy as np
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, QSpinBox, QComboBox, QStatusBar, QDialog
)
from daolite.utils.sh_utility import getAvailableSubAps, genSHSubApMap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class CentroidAgendaTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Centroid Agenda Generator")
        self.readout_map = None
        self.subap_map = None
        self.subap_map_full = None
        self.logger = logging.getLogger("CentroidAgendaTool")
        logging.basicConfig(level=logging.INFO)
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready.")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Readout order loader
        self.readout_label = QLabel("Readout Order: Not loaded")
        btn_load_readout = QPushButton("Load Readout Order (.npy or .csv)")
        btn_load_readout.clicked.connect(self.load_readout)
        layout.addWidget(self.readout_label)
        layout.addWidget(btn_load_readout)

        # Add readout order generation options
        hbox_gen = QHBoxLayout()
        hbox_gen.addWidget(QLabel("Generate Readout Order:"))
        self.readout_gen_combo = QComboBox()
        self.readout_gen_combo.addItems(["Linear (row-major)"])
        hbox_gen.addWidget(self.readout_gen_combo)
        self.img_size_spin = QSpinBox()
        self.img_size_spin.setMinimum(1)
        self.img_size_spin.setMaximum(4096)
        self.img_size_spin.setValue(128)
        hbox_gen.addWidget(QLabel("Image Size:"))
        hbox_gen.addWidget(self.img_size_spin)
        btn_gen_readout = QPushButton("Generate")
        btn_gen_readout.clicked.connect(self.generate_readout_order)
        hbox_gen.addWidget(btn_gen_readout)
        layout.addLayout(hbox_gen)

        # Sub-aperture map loader
        self.subap_label = QLabel("Sub-aperture Map: Not loaded")
        btn_load_subap = QPushButton("Load Sub-aperture Map (.npy or .csv)")
        btn_load_subap.clicked.connect(self.load_subap)
        layout.addWidget(self.subap_label)
        layout.addWidget(btn_load_subap)

        # Sub-aperture map generator controls
        hbox_gen_subap = QHBoxLayout()
        hbox_gen_subap.addWidget(QLabel("Generate Sub-aperture Map:"))
        self.nsubs_spin = QSpinBox()
        self.nsubs_spin.setMinimum(1)
        self.nsubs_spin.setMaximum(512)
        self.nsubs_spin.setValue(10)
        hbox_gen_subap.addWidget(QLabel("nSubs:"))
        hbox_gen_subap.addWidget(self.nsubs_spin)
        self.subsize_spin = QSpinBox()
        self.subsize_spin.setMinimum(1)
        self.subsize_spin.setMaximum(256)
        self.subsize_spin.setValue(16)
        hbox_gen_subap.addWidget(QLabel("Sub size:"))
        hbox_gen_subap.addWidget(self.subsize_spin)
        self.xoff_spin = QSpinBox()
        self.xoff_spin.setMinimum(-1024)
        self.xoff_spin.setMaximum(1024)
        self.xoff_spin.setValue(0)
        hbox_gen_subap.addWidget(QLabel("X offset:"))
        hbox_gen_subap.addWidget(self.xoff_spin)
        self.yoff_spin = QSpinBox()
        self.yoff_spin.setMinimum(-1024)
        self.yoff_spin.setMaximum(1024)
        self.yoff_spin.setValue(0)
        hbox_gen_subap.addWidget(QLabel("Y offset:"))
        hbox_gen_subap.addWidget(self.yoff_spin)
        btn_gen_subap = QPushButton("Generate")
        btn_gen_subap.clicked.connect(self.generate_subap_map)
        hbox_gen_subap.addWidget(btn_gen_subap)
        layout.addLayout(hbox_gen_subap)

        # Sub-aperture size
        hbox_size = QHBoxLayout()
        hbox_size.addWidget(QLabel("Sub-aperture size (pixels):"))
        self.size_spin = QSpinBox()
        self.size_spin.setMinimum(1)
        self.size_spin.setMaximum(256)
        self.size_spin.setValue(16)
        hbox_size.addWidget(self.size_spin)
        layout.addLayout(hbox_size)

        # Number of readout groups
        hbox_groups = QHBoxLayout()
        hbox_groups.addWidget(QLabel("Number of readout groups:"))
        self.groups_spin = QSpinBox()
        self.groups_spin.setMinimum(1)
        self.groups_spin.setMaximum(10000)
        self.groups_spin.setValue(10)
        hbox_groups.addWidget(self.groups_spin)
        layout.addLayout(hbox_groups)

        # Generate button
        btn_generate = QPushButton("Generate Centroid Agenda")
        btn_generate.clicked.connect(self.generate_agenda)
        layout.addWidget(btn_generate)

        # Save button
        self.btn_save = QPushButton("Save Agenda")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_agenda)
        layout.addWidget(self.btn_save)

        # Output label
        self.output_label = QLabel("")
        layout.addWidget(self.output_label)

        # Matplotlib figure for images
        self.fig, (self.ax_img, self.ax_1d) = plt.subplots(2, 1, figsize=(6, 8), gridspec_kw={'height_ratios': [3, 1]})
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        layout.addWidget(self.status_bar)

        self.setLayout(layout)
        self.agenda = None

    def set_status(self, msg, level=logging.INFO):
        self.status_bar.showMessage(msg)
        self.logger.log(level, msg)

    def load_readout(self, readout_map=None):
        self.set_status("Loading readout order...")
        if readout_map is None:
            path, _ = QFileDialog.getOpenFileName(self, "Load Readout Order", "", "Numpy/CSV Files (*.npy *.csv)")
            if path:
                try:
                    if path.endswith('.npy'):
                        self.readout_map = np.load(path)
                    else:
                        self.readout_map = np.loadtxt(path, delimiter=',')
                    self.readout_label.setText(f"Readout Order: {path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load readout order: {e}")
        else:
            self.readout_map = readout_map

        self.update_plots(self.agenda)
        self.set_status("Readout order loaded.")

    def generate_readout_order(self):
        self.set_status("Generating linear readout order...")
        size = self.img_size_spin.value()
        arr = np.arange(size * size).reshape((size, size))
        self.readout_map = arr
        self.readout_label.setText(f"Readout Order: Linear {size}x{size}")
        # Check sub-aperture map fits
        if self.subap_map is not None:
            img_shape = self.readout_map.shape
            nSubs = self.nsubs_spin.value()
            subSize = self.subsize_spin.value()
            xoff = self.xoff_spin.value()
            yoff = self.yoff_spin.value()
            needed_x = xoff + nSubs * subSize
            needed_y = yoff + nSubs * subSize
            if needed_x > img_shape[1] or needed_y > img_shape[0]:
                QMessageBox.warning(self, "Sub-aperture Map Out of Bounds",
                    f"Sub-aperture map (offset + nSubs*subSize) exceeds image size.\n"
                    f"Image size: {img_shape}, Needed: ({needed_y}, {needed_x})\n"
                    f"Please adjust nSubs, sub size, or offsets.")
        QMessageBox.information(self, "Readout Order Generated", f"Linear readout order {size}x{size} generated.")

        # now call load_readout to update plots
        self.load_readout(readout_map=self.readout_map)
        self.set_status("Linear readout order generated.")

    def load_subap(self):
        self.set_status("Loading sub-aperture map...")
        path, _ = QFileDialog.getOpenFileName(self, "Load Sub-aperture Map", "", "Numpy/CSV Files (*.npy *.csv)")
        if path:
            try:
                if path.endswith('.npy'):
                    self.subap_map = np.load(path)
                else:
                    self.subap_map = np.loadtxt(path, delimiter=',')
                self.subap_label.setText(f"Sub-aperture Map: {path}")
                self.update_plots(self.agenda)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load sub-aperture map: {e}")
        self.set_status("Sub-aperture map loaded.")

    def generate_subap_map(self):
        self.set_status("Generating sub-aperture map...")
        nSubs = self.nsubs_spin.value()
        sub_size = self.subsize_spin.value()
        x_offset = self.xoff_spin.value()
        y_offset = self.yoff_spin.value()
        # Use genSHSubApMap to generate full map (numbered)
        full_map = genSHSubApMap(nSubs, nSubs, 0.1 * nSubs, nSubs // 2, mask=False)
        self.subap_map_full = full_map
        centers = []
        for row in range(full_map.shape[0]):
            for col in range(full_map.shape[1]):
                if full_map[row, col] > 0:
                    x = col * sub_size + sub_size // 2 + x_offset
                    y = row * sub_size + sub_size // 2 + y_offset
                    centers.append([y, x])
        if centers:
            self.subap_map = np.array(centers)
            self.subap_label.setText(f"Sub-aperture Map: Generated ({len(centers)} sub-aps)")
            self.size_spin.setValue(sub_size)
            self.update_plots(self.agenda)
            self.set_status(f"Sub-aperture map generated with {len(centers)} sub-aps.")
        else:
            QMessageBox.warning(self, "No sub-apertures", "No valid sub-apertures found with these parameters.")
            self.set_status("No valid sub-apertures found.", logging.WARNING)

    def generate_agenda(self):
        self.set_status("Generating centroid agenda...")
        if self.readout_map is None or self.subap_map is None:
            QMessageBox.warning(self, "Missing Input", "Please load or generate both readout order and sub-aperture map before generating the centroid agenda.")
            return
        nPixPerSubAp = self.size_spin.value()
        nGroups = self.groups_spin.value()
        nPixels = self.readout_map.shape[0]
        total_pixels = self.readout_map.size
        pixelAgenda = np.full(nGroups, total_pixels // nGroups, dtype=int)
        pixelAgenda[:total_pixels % nGroups] += 1  # Distribute remainder
        print(f"Pixel agenda: {pixelAgenda}")
        try:
            available = getAvailableSubAps(
                self.readout_map.flatten(), nPixels, nPixPerSubAp, pixelAgenda, getattr(self, 'subap_map_full', None)
            )
            self.agenda = available
            print(f"Available sub-apertures: {available}")
            self.btn_save.setEnabled(True)
            self.output_label.setText(f"Agenda generated. See plots below.")
            self.update_plots(available)
            self.set_status("Centroid agenda generated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate agenda: {e}")
            self.set_status(f"Failed to generate agenda: {e}", logging.ERROR)

    def update_plots(self, available=None):
        self.fig.clf()
        has_readout = self.readout_map is not None
        has_subap = self.subap_map is not None
        nPixPerSubAp = self.size_spin.value()
        if has_readout and has_subap:
            ax_img = self.fig.add_subplot(2, 1, 1)
            ax_1d = self.fig.add_subplot(2, 1, 2)
            im = ax_img.imshow(self.readout_map, cmap='viridis')
            self.fig.colorbar(im, ax=ax_img, orientation='vertical', label='Readout Index')
            for center in self.subap_map:
                y, x = center
                rect = plt.Rectangle((x - nPixPerSubAp // 2, y - nPixPerSubAp // 2), nPixPerSubAp, nPixPerSubAp,
                                     linewidth=1, edgecolor='r', facecolor='none')
                ax_img.add_patch(rect)
            ax_img.set_title('Readout Order with Sub-aperture Boxes')
            ax_img.set_xlabel('X')
            ax_img.set_ylabel('Y')
            # 1D plot: plot agenda directly
            if available is not None:
                ax_1d.plot(np.arange(len(available)), available, marker='o')
                ax_1d.set_title('Available Sub-apertures per Readout Group')
                ax_1d.set_xlabel('Readout Group')
                ax_1d.set_ylabel('Available Sub-apertures')
                ax_1d.grid(True)
            else:
                ax_1d.axis('off')
        elif has_readout:
            ax_img = self.fig.add_subplot(1, 1, 1)
            im = ax_img.imshow(self.readout_map, cmap='viridis')
            self.fig.colorbar(im, ax=ax_img, orientation='vertical', label='Readout Index')
            ax_img.set_title('Readout Order')
            ax_img.set_xlabel('X')
            ax_img.set_ylabel('Y')
        elif has_subap:
            ax_img = self.fig.add_subplot(1, 1, 1)
            for center in self.subap_map:
                y, x = center
                rect = plt.Rectangle((x - nPixPerSubAp // 2, y - nPixPerSubAp // 2), nPixPerSubAp, nPixPerSubAp,
                                     linewidth=1, edgecolor='r', facecolor='none')
                ax_img.add_patch(rect)
            ax_img.set_title('Sub-aperture Boxes (no readout order)')
            ax_img.set_xlabel('X')
            ax_img.set_ylabel('Y')
            ax_img.set_xlim(0, max(self.subap_map[:,1]) + nPixPerSubAp)
            ax_img.set_ylim(0, max(self.subap_map[:,0]) + nPixPerSubAp)
        else:
            self.fig.text(0.5, 0.5, 'No data loaded', ha='center', va='center', fontsize=16)
        self.fig.tight_layout()
        self.canvas.draw()

    def save_agenda(self):
        self.set_status("Saving agenda...")
        if self.agenda is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Agenda", "", "Numpy File (*.npy);;CSV File (*.csv)")
        if path:
            try:
                if path.endswith('.npy'):
                    np.save(path, self.agenda)
                else:
                    np.savetxt(path, self.agenda, delimiter=',')
                QMessageBox.information(self, "Saved", f"Agenda saved to {path}")
                self.set_status(f"Agenda saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save agenda: {e}")
                self.set_status(f"Failed to save agenda: {e}", logging.ERROR)

class CentroidAgendaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Centroid Agenda Tool")
        self.widget = CentroidAgendaTool()
        layout = QVBoxLayout(self)
        layout.addWidget(self.widget)
        self.setLayout(layout)
        self.resize(700, 900)

def show_centroid_agenda_tool(parent=None):
    dlg = CentroidAgendaDialog(parent)
    dlg.exec_()

def main():
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    win = CentroidAgendaTool()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
