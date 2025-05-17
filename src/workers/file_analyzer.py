import math
import os

import numpy as np
from PIL import Image

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip

from src.ffmpeg_extractor import extract_frames_to_folder
from src.ffmpeg_extractor.tools import create_snaps_folder
from src.schemas import ClipMetaData
from src.schemas import PreviewData
from src.utils import extract_file_name

from src.options import BASEDIR

SNAPS_FOLDER = os.path.join(BASEDIR, 'snaps')


class StoryboardCreatorSignals(QObject):
    finished = pyqtSignal(PreviewData)
    error = pyqtSignal(str)


class StoryboardCreator(QRunnable):
    def __init__(self, clip_metadata: ClipMetaData, duration_in_px:int, last_frame_percentage: float):
        super().__init__()
        self.signals = StoryboardCreatorSignals()
        self.clip_metadata = clip_metadata
        self.duration_in_px = duration_in_px
        self.last_frame_percentage = last_frame_percentage
        self.all_frames_list = [file
                                for file in os.listdir(self.clip_metadata.all_frames_folder)
                                if file.endswith(".png")]

    def _prepare_frames(self):
        frames_count = math.ceil(self.duration_in_px / self.clip_metadata.scaled_width)
        step = len(self.all_frames_list) // frames_count
        # print(f'[FRAMES COUNT ] = {frames_count}, step: {step}')
        for frame_name in self.all_frames_list[::step]:
            with Image.open(os.path.join(self.clip_metadata.all_frames_folder, frame_name)) as img:
                yield img

    def create_storyboard_frames(self) ->list[np.array]:
        frames = [np.array(frame) for frame in self._prepare_frames()]
        if self.last_frame_percentage:
            last_frame = self._truncate_frame(frames[-1], self.last_frame_percentage)
            frames[-1] = last_frame

        return frames

    @staticmethod
    def _truncate_frame(frame: np.ndarray, last_frame_percentage: float) -> np.ndarray:
        h, w, _ = frame.shape
        new_w = int(w * last_frame_percentage)
        new_w -= new_w % 4
        return frame[:, :new_w, :]

    def generate_preview_data(self) -> PreviewData:
        frames_list = self.create_storyboard_frames()
        preview_data = PreviewData(clip_metadata=self.clip_metadata)
        preview_data.duration_in_px = self.duration_in_px
        preview_data.preview = _frame_to_pixmap(frames_list[0])
        preview_data.storyboard = _frame_to_pixmap(np.hstack(frames_list))
        preview_data.storyboard_frames_count = len(frames_list)
        return preview_data

    def run(self):
        try:
            preview_data = self.generate_preview_data()

        except Exception as e:
            self.signals.error.emit("ERROR " + str(e))
        else:
            self.signals.finished.emit(preview_data)


class VideoDataAnalyzerSignals(QObject):
    finished = pyqtSignal(ClipMetaData)
    error = pyqtSignal(str)


class VideoDataAnalyzer(QRunnable):
    def __init__(self, file_path: str, preview_frame_height: int):
        super().__init__()
        self.signals = VideoDataAnalyzerSignals()
        self.video_path = file_path

        # self.clip_metadata = ClipMetaData(file_path)  # --
        self.preview_frame_height = preview_frame_height
        self.frame_resize_coef = 0
        self.duration_in_px = 0
        self.scaled_frame_width = 0

    # def scan_metadata(self, video_file_clip: VideoFileClip):
    #     self.clip_metadata.duration_s = video_file_clip.duration
    #     self.clip_metadata.width, self.clip_metadata.height = video_file_clip.size
    #     self.duration_in_px = int(self.clip_metadata.duration_s * self.px_per_sec)
    #     self.frame_resize_coef = self.preview_frame_height / self.clip_metadata.height
    #
    #     self.scaled_frame_width = int(self.clip_metadata.width * self.frame_resize_coef)
    #     self.scaled_frame_width -= self.scaled_frame_width % 4
    #
    #     if self.scaled_frame_width == 0:
    #         self.scaled_frame_width = 4

    # def generate_preview(self, filename: str):
    #     last_frame_width = int(self.duration_in_px % self.scaled_frame_width)  # 675 % 88 = 59
    #     last_frame_percentage = last_frame_width / self.scaled_frame_width  # 0.6704
    #     preview_creator = StoryboardCreator(filename, self.scaled_frame_width, self.preview_frame_height)
    #
    #     return preview_creator.generate_preview_data(last_frame_percentage, self.duration_in_px)

    def save_enough_frames(self, filename: str, frame_width: int, frame_height: int) ->str:
        folder_name = extract_file_name(filename)
        folder_path = os.path.join(SNAPS_FOLDER, folder_name)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
            extract_frames_to_folder(filename, frame_width, frame_height)

        return folder_path

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

        all_frames_folder = self.save_enough_frames(self.video_path, scaled_frame_width, self.preview_frame_height)

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
            print(clip_metadata)
            # preview_data = self.generate_preview(self.clip_metadata.filename)
            #
            # # ______________TEMP_______________________________
            # self.clip_metadata.preview_small = preview_data.preview
            # self.clip_metadata.preview_large = preview_data.storyboard
            # self.clip_metadata.preview_frames_count = preview_data.storyboard_frames_count
            # self.clip_metadata.duration_in_px = self.duration_in_px
            # ______________TEMP_______________________________

        except Exception as e:
            self.signals.error.emit("ERROR " + str(e))
        else:
            self.signals.finished.emit(clip_metadata)


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    h, w, ch = frame.shape
    frame = np.ascontiguousarray(frame)
    image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)
