from dataclasses import dataclass
from PyQt6.QtGui import QPixmap


@dataclass
class PreviewData:
    preview: QPixmap = None
    storyboard: QPixmap = None
    storyboard_frames_count: int = 0
    duration_in_px: int = 0


@dataclass
class ClipMetaData:
    filename: str
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    preview_small: QPixmap = None
    preview_large: QPixmap = None
    preview_frames_count: int = 0
    duration_in_px: int = 0



