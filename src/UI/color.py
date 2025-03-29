from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget


class ColorBackground(QWidget):
    def __init__(self, color:str):
        super().__init__()
        self.color = color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)


class ColorOptions:
    dark = '#2e3436'
    darker = '#262626'
    darkish = '#3B3F4E'
    darkish_brighter = '#4E5157'
    darkish_lighter = '#5C6066'
    darkish_lightest = '#747C8B'
    dim = '#454545'
    dimmer = '#3A3A3A'
    dimmest = '#262626'
    light = '#F0F0F0'
    lighter = '#F7F7F7'
    lightest = '#FFFFFF'
    medium = '#B1B1B1'
    medium_brighter = '#C4C4C4'
    medium_darker = '#A3A3A3'
    semi_light = '#E5E5E5'