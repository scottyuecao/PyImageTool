from .widgets import InfoBar
from .PGImageTool import PGImageTool
from .DataMatrix import RegularDataArray
from pyqtgraph.Qt import QtCore, QtWidgets
from functools import partial
from .widgets import TransposeAxesWidget
import pyqtgraph as pg
import numpy as np
import warnings

class ImageTool(QtWidgets.QWidget):
    LayoutSimple = PGImageTool.LayoutSimple
    LayoutComplete = PGImageTool.LayoutComplete
    LayoutRaster = PGImageTool.LayoutRaster

    def __init__(self, data: RegularDataArray, layout: int = PGImageTool.LayoutSimple, parent=None):
        """
        Possible Layouts are PGImageTool.LayoutSimple, LayoutComplete, LayoutRaster
        """
        super().__init__(parent)
        # Warn user about nan
        if np.any(np.isnan(data.values)):
            warnings.warn('Input data contains NaNs. All NaN will be set to 0.')
            data.values[np.isnan(data.values)] = 0
        # Create data
        self.data: RegularDataArray = data
        self.it_layout: int = layout
        # Create info bar and ImageTool PyQt Widget
        self.info_bar = InfoBar(data, parent=self)
        self.pg_widget = QtWidgets.QWidget()  # widget to hold pyqtgraph graphicslayout
        self.pg_widget.setLayout(QtWidgets.QVBoxLayout())
        self.pg_win = PGImageTool(data, layout=layout)  # the pyqtgraph graphicslayout
        self.pg_widget.layout().addWidget(self.pg_win)
        # Build the layout
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.info_bar)
        self.layout().addWidget(self.pg_win)
        # Create status bar
        self.status_bar = QtWidgets.QStatusBar(self)
        self.status_bar.showMessage("Initialized")
        self.layout().addWidget(self.status_bar)
        # Connect signals and slots
        self.mouse_move_proxy = pg.SignalProxy(self.pg_win.mouse_hover, rateLimit=30, slot=self.update_status_bar)
        self.build_handlers()
        # TODO: update to QT 5.14 and use textActivated signal instead
        self.info_bar.cmap_combobox.currentTextChanged.connect(self.set_all_cmaps)
        self.info_bar.transpose_request.connect(self.transpose_data)

    def update_status_bar(self, msg: tuple):
        self.status_bar.showMessage(msg[0])

    def build_handlers(self):
        # Connect index spin box to model
        for i, sb in enumerate(self.info_bar.cursor_i):
            sb.valueChanged.connect(self.pg_win.cursor.set[i])
            self.pg_win.cursor.index[i].value_changed.connect(sb.setValue)

        # Connect coordinate spin box to model
        def on_cursor_dsb_changed(spinbox, handler):
            handler(spinbox.value())

        for i, dsb in enumerate(self.info_bar.cursor_c):
            coord = self.pg_win.index_to_coord[i]
            dsb.editingFinished.connect(partial(on_cursor_dsb_changed,
                                                dsb,
                                                self.pg_win.cursor.set[coord]))
            self.pg_win.cursor.pos[i].value_changed.connect(dsb.setValue)

        # Connect binwidth to model
        def on_sb_binwidth_changed(binwidth_model, newval):
            binwidth_model.val = newval

        def on_dsb_binwidth_changed(binwidth_model, coord_delta, dsb: QtWidgets.QDoubleSpinBox):
            idx = int(round(dsb.value() / coord_delta))
            binwidth_model.val = idx

        def on_binwidth_model_changed(sb: QtWidgets.QSpinBox, dsb: QtWidgets.QDoubleSpinBox, coord_delta, x):
            sb.blockSignals(True)
            sb.setValue(x)
            sb.blockSignals(False)
            dsb.blockSignals(True)
            dsb.setValue(coord_delta * x)
            dsb.blockSignals(False)

        for i, sb in enumerate(self.info_bar.bin_i):
            sb.valueChanged.connect(partial(on_sb_binwidth_changed, self.pg_win.bin_widths[i]))
            self.info_bar.bin_c[i].editingFinished.connect(partial(on_dsb_binwidth_changed, self.pg_win.bin_widths[i],
                                                                self.data.delta[i], self.info_bar.bin_c[i]))
            self.pg_win.bin_widths[i].value_changed.connect(partial(on_binwidth_model_changed,
                                                                    self.info_bar.bin_i[i],
                                                                    self.info_bar.bin_c[i],
                                                                    self.data.delta[i]))

    def reset(self):
        # Create info bar and ImageTool PyQt Widget
        self.info_bar.reset(self.data)
        self.pg_win.reset(self.data)

    def set_all_cmaps(self, cmap_name: str):
        self.pg_win.load_ct(cmap_name)

    def transpose_data(self, tr):
        self.data = self.data.transpose(tr)
        self.reset()

    def keyReleaseEvent(self, e):
        if e.key() == QtCore.Qt.Key_Shift:
            self.pg_win.shift_down = False
        else:
            e.ignore()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Shift:
            self.pg_win.shift_down = True
            self.pg_win.set_crosshair_to_mouse()
        else:
            e.ignore()