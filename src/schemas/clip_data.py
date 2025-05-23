from dataclasses import dataclass
from PyQt6.QtGui import QPixmap


@dataclass
class PreviewData:
    clip_metadata: 'ClipMetaData'
    preview: QPixmap = None
    storyboard: QPixmap = None
    storyboard_frames_count: int = 0
    duration_in_px: int = 0

    preview_frames_count: int = 0  # --



@dataclass
class ClipMetaData:
    filename: str
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    scaled_width:int = None
    scaled_height:int = None
    all_frames_folder: str = None

    # preview_small: QPixmap = None # --
    # preview_large: QPixmap = None # --
    # preview_frames_count: int = 0 # --
    # duration_in_px: int = 0 # --



