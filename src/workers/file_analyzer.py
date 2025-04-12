import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip

from src.schemas import ClipData


class VideoFileAnalyzerSignals(QObject):
    finished = pyqtSignal(ClipData)
    error = pyqtSignal(str)


class VideoDataAnalyzer(QRunnable):
    def __init__(self, file_path: str):
        super().__init__()
        self.clip_data = ClipData(file_path)
        self.signals = VideoFileAnalyzerSignals()

    @staticmethod
    def frame_to_pixmap(frame: np.ndarray):
        h, w, ch = frame.shape
        image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(image)

    def generate_preview(self, video_file_clip:VideoFileClip):
        frame = video_file_clip.get_frame(1)
        self.clip_data.preview_small = self.frame_to_pixmap(frame)

    def scan_metadata(self, video_file_clip: VideoFileClip):
        self.clip_data.duration_s = video_file_clip.duration
        self.clip_data.width, self.clip_data.height = video_file_clip.size

    def run(self):
        try:
            clip = VideoFileClip(self.clip_data.filename)
            self.generate_preview(clip)
            self.scan_metadata(clip)
            clip.close()
        except Exception as e:
            self.signals.error.emit("ERROR "+ str(e))
        else:
            self.signals.finished.emit(self.clip_data)