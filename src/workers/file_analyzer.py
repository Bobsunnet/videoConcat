import math
import os

import numpy as np
from PIL import Image

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip

from src.ffmpeg_extractor import extract_frames_to_folder
from src.schemas import ClipMetaData
from src.schemas import PreviewData
from src.utils import extract_file_name


class StoryboardCreator:
    def __init__(self, filename:str, width:int, height:int):
        self.width = width
        self.height = height
        self.folder_name = extract_file_name(filename)
        if not os.path.exists(f"snaps/{self.folder_name}"):
            os.mkdir(f"snaps/{self.folder_name}")
            extract_frames_to_folder(filename, width, height)

        self.all_frames_list = [file for file in os.listdir(f"snaps/{self.folder_name}") if file.endswith(".png")]

    def _prepare_frames(self, duration_in_px:int):
        frames_count = math.ceil(duration_in_px / self.width)
        step = len(self.all_frames_list)//frames_count
        # print(f'[FRAMES COUNT ] = {frames_count}, step: {step}')
        for frame_name in self.all_frames_list[::step]:
            with Image.open(f"snaps/{self.folder_name}/{frame_name}") as im:
                yield im

    def get_storyboard_frames(self, last_frame_percentage: float, duration_in_px:int):
        frames = [np.array(frame) for frame in self._prepare_frames(duration_in_px)]
        if last_frame_percentage:
            last_frame = self._truncate_frame(frames[-1], last_frame_percentage)
            frames[-1] = last_frame

        return frames

    @staticmethod
    def _truncate_frame(frame:np.ndarray, last_frame_percentage:float) -> np.ndarray:
        h, w, _ = frame.shape
        new_w = int(w * last_frame_percentage)
        new_w -= new_w % 4
        return frame[:, :new_w, :]

    def generate_preview_data(self,last_frame_percentage: float, duration_in_px:int) -> PreviewData:
        frames_list = self.get_storyboard_frames(last_frame_percentage, duration_in_px)
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
        self.preview_frame_height = preview_frame_height
        self.frame_resize_coef = 0
        self.duration_in_px = 0
        self.scaled_frame_width = 0

    def scan_metadata(self, video_file_clip: VideoFileClip):
        self.clip_metadata.duration_s = video_file_clip.duration
        self.clip_metadata.width, self.clip_metadata.height = video_file_clip.size
        self.duration_in_px = int(self.clip_metadata.duration_s * self.px_per_sec)
        self.frame_resize_coef = self.preview_frame_height / self.clip_metadata.height
        self.scaled_frame_width = int(self.clip_metadata.width * self.frame_resize_coef)
        self.scaled_frame_width -= self.scaled_frame_width % 4
        if self.scaled_frame_width == 0:
            self.scaled_frame_width = 4

    def generate_preview(self, filename: str):
        last_frame_width = int(self.duration_in_px % self.scaled_frame_width)  # 675 % 88 = 59
        last_frame_percentage = last_frame_width / self.scaled_frame_width  # 0.6704
        preview_creator = StoryboardCreator(filename, self.scaled_frame_width, self.preview_frame_height)

        return preview_creator.generate_preview_data(last_frame_percentage, self.duration_in_px)

    def analyze_clip(self)->ClipMetaData:
        pass

    def run(self):
        try:
            clip = VideoFileClip(self.clip_metadata.filename)
            self.scan_metadata(clip)
            clip.close()
            preview_data = self.generate_preview(self.clip_metadata.filename)

            # ______________TEMP_______________________________
            self.clip_metadata.preview_small = preview_data.preview
            self.clip_metadata.preview_large = preview_data.storyboard
            self.clip_metadata.preview_frames_count = preview_data.storyboard_frames_count
            self.clip_metadata.duration_in_px = self.duration_in_px
            # ______________TEMP_______________________________

        except Exception as e:
            self.signals.error.emit("ERROR " + str(e))
        else:
            self.signals.finished.emit(self.clip_metadata)


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    h, w, ch = frame.shape
    frame = np.ascontiguousarray(frame)
    image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)
