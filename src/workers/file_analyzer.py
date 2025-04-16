import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip

from src.schemas import ClipMetaData
from src.schemas import PreviewData


class StoryboardCreator:
    def extract_storyboard_frames(self,
                                  video_clip: VideoFileClip,
                                  time_marks: list[float],
                                  last_frame_percentage: float) -> list[np.ndarray]:
        """ """
        frames: list[np.ndarray] = []
        for i, time_mark in enumerate(time_marks):
            frame = video_clip.get_frame(time_mark)
            if i == len(time_marks) - 1:
                h, w, _ = frame.shape
                new_w = int(w*last_frame_percentage)
                new_w -= new_w % 4
                frame = frame[:, :new_w, :]
            frames.append(frame)
        return frames

    def generate_preview_data(self,
                              video_file_clip: VideoFileClip,
                              time_marks:list[float],
                              last_frame_percentage:float) ->PreviewData:
        frames_list = self.extract_storyboard_frames(video_file_clip, time_marks, last_frame_percentage)
        preview_data = PreviewData()
        preview_data.preview = _frame_to_pixmap(frames_list[0])
        preview_data.storyboard = _frame_to_pixmap(np.hstack(frames_list))
        preview_data.storyboard_frames_count = len(frames_list)
        return preview_data


class VideoDataAnalyzerSignals(QObject):
    finished = pyqtSignal(ClipMetaData)
    error = pyqtSignal(str)


class VideoDataAnalyzer(QRunnable):
    def __init__(self, file_path: str, px_per_sec: int, preview_frame_height: int):
        super().__init__()
        self.signals = VideoDataAnalyzerSignals()

        self.clip_metadata = ClipMetaData(file_path)
        self.px_per_sec = px_per_sec
        self.scaled_frame_height = preview_frame_height
        self.frame_resize_coef = 0
        self.duration_in_px = 0
        self.scaled_frame_width = 0

    def scan_metadata(self, video_file_clip: VideoFileClip):
        self.clip_metadata.duration_s = video_file_clip.duration
        self.clip_metadata.width, self.clip_metadata.height = video_file_clip.size
        self.duration_in_px = int(self.clip_metadata.duration_s * self.px_per_sec)
        self.frame_resize_coef = self.scaled_frame_height / self.clip_metadata.height
        self.scaled_frame_width = int(self.clip_metadata.width * self.frame_resize_coef)

    def generate_preview(self, video_file_clip:VideoFileClip):
        preview_creator = StoryboardCreator()
        last_frame_width = int(self.duration_in_px % self.scaled_frame_width)  #675 % 88 = 59
        last_frame_percentage = last_frame_width / self.scaled_frame_width  # 0.6704

        step = self.scaled_frame_width / self.px_per_sec
        time_marks = []
        time_mark = 0
        while time_mark < self.clip_metadata.duration_s:
            time_marks.append(time_mark)
            time_mark += step

        return preview_creator.generate_preview_data(video_file_clip, time_marks, last_frame_percentage)


    def run(self):
        try:
            clip = VideoFileClip(self.clip_metadata.filename)
            self.scan_metadata(clip)
            # clip = clip.resized(width=self.scaled_frame_width, height=self.scaled_frame_height)
            preview_data = self.generate_preview(clip)

            # ______________TEMP_______________________________
            self.clip_metadata.preview_small = preview_data.preview
            self.clip_metadata.preview_large = preview_data.storyboard
            self.clip_metadata.preview_frames_count = preview_data.storyboard_frames_count
            self.clip_metadata.duration_in_px = self.duration_in_px
            # ______________TEMP_______________________________

            clip.close()
        except Exception as e:
            self.signals.error.emit("ERROR " + str(e))
        else:
            self.signals.finished.emit(self.clip_metadata)


def _frame_to_pixmap(frame: np.ndarray):
    h, w, ch = frame.shape
    print(h, w)
    frame = np.ascontiguousarray(frame)
    image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)