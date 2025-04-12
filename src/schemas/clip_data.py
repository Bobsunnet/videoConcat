from PyQt6.QtGui import QPixmap

from dataclasses import dataclass


@dataclass
class ClipData:
    filename: str
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    preview_small: QPixmap = None