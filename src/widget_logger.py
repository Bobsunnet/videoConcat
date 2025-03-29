from PyQt6.QtCore import pyqtSignal
from proglog import ProgressBarLogger


class WidgetProgressLogger(ProgressBarLogger):
    def __init__(self, signal:pyqtSignal):
        super().__init__()
        self.signal = signal

    def bars_callback(self, bar, attr, value, old_value):
        if bar == 'frame_index':
            self.signal.emit(value)
