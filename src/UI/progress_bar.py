from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QProgressBar


class ProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.max_value = None

    @pyqtSlot(int)
    def progress_changed(self, value:int):
        if self.max_value is not None:
            self.setValue(value)
        else:
            self.max_value = value
            self.setRange(0, value)

    def init_scale(self ):
        self.setRange(0, 100)
        self.setValue(0)
        self.max_value = None