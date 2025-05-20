from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from moviepy import VideoFileClip

from src.ffmpeg_extractor import extract_frames_to_folder
from src.schemas import ClipMetaData


class VideoDataAnalyzerSignals(QObject):
    finished = pyqtSignal(ClipMetaData)
    error = pyqtSignal(str)


class VideoDataAnalyzer(QRunnable):
    def __init__(self, file_path: str, preview_frame_height: int):
        super().__init__()
        self.signals = VideoDataAnalyzerSignals()
        self.video_path = file_path
        self.preview_frame_height = preview_frame_height
        self.frame_resize_coef = 0
        self.duration_in_px = 0
        self.scaled_frame_width = 0

    def analyze_clip(self) -> ClipMetaData:
        clip = VideoFileClip(self.video_path)
        duration_s = clip.duration
        width, height = clip.size
        clip.close()

        frame_resize_coef = self.preview_frame_height / height
        scaled_frame_width = int(width * frame_resize_coef)
        scaled_frame_width -= scaled_frame_width % 4
        if scaled_frame_width == 0:
            scaled_frame_width = 4

        all_frames_folder = extract_frames_to_folder(self.video_path, scaled_frame_width, self.preview_frame_height)

        return ClipMetaData(self.video_path,
                            duration_s,
                            width,
                            height,
                            scaled_frame_width,
                            self.preview_frame_height,
                            all_frames_folder)

    def run(self):
        try:
            clip_metadata = self.analyze_clip()

        except Exception as e:
            self.signals.error.emit("ERROR " + str(e))
        else:
            self.signals.finished.emit(clip_metadata)


