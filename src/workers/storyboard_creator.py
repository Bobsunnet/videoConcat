import math
import os

import numpy as np
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QPixmap, QImage

from src.schemas import PreviewData, ClipMetaData


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
        # print(f'\n[FRAMES COUNT ] = {frames_count}, step: {step}')
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


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    h, w, ch = frame.shape
    frame = np.ascontiguousarray(frame)
    image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)
