import io
import subprocess

import numpy as np
import imageio_ffmpeg

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from PyQt6.QtGui import QImage, QPixmap
from moviepy import VideoFileClip
from PIL import Image

from src.schemas import ClipMetaData
from src.schemas import PreviewData


class StoryboardCreator:

    def extract_frames_from_pipe(self, video_path: str, time_step: float, width: int, height: int):
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg_path,
            "-i", video_path,
            "-vf", f"fps=1/{time_step}",
            "-s", f"{width}x{height}",
            "-f", "image2pipe",
            "-vcodec", "png",
            "-"]

        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buffer = b''
        start_marker = b'\x89PNG\r\n\x1a\n'
        end_marker = b'IEND\xaeB`\x82'
        chunk_size = 65536

        while True:
            try:
                chunk = proc.stdout.read(chunk_size)
                if not chunk:
                    break

                buffer += chunk

                while True:
                    start_idx = buffer.find(start_marker)
                    if start_idx == -1:
                        break

                    end_idx = buffer.find(end_marker)
                    if end_idx == -1:
                        break

                    img_data_bytes = buffer[start_idx:end_idx + 8]
                    buffer = buffer[end_idx + 8:]
                    img = Image.open(io.BytesIO(img_data_bytes))
                    yield img

            except Exception as e:
                print(e)

        proc.terminate()

    def _ffmpeg_extract_frames(self, video_path: str, time_step: float, width: int, height: int,
                               last_frame_percentage: float):
        frames = [np.array(frame) for frame in self.extract_frames_from_pipe(video_path, time_step, width, height)]
        last_frame = self._truncate_frame(frames[-1], last_frame_percentage)
        frames[-1] = last_frame
        return frames

    def _truncate_frame(self, frame, last_frame_percentage) -> np.ndarray:
        h, w, _ = frame.shape
        new_w = int(w * last_frame_percentage)
        new_w -= new_w % 4
        return frame[:, :new_w, :]

    def generate_preview_data(self,
                              video_file_clip: VideoFileClip,
                              time_step: float,
                              last_frame_percentage: float) -> PreviewData:
        # frames_list = self.extract_storyboard_frames(video_file_clip, time_marks, last_frame_percentage)

        frames_list = self._ffmpeg_extract_frames(video_file_clip.filename,
                                                  time_step,
                                                  width=72,
                                                  height=40,
                                                  last_frame_percentage=last_frame_percentage
                                                  )
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

    def _create_time_marks(self):
        step = self.scaled_frame_width / self.px_per_sec
        time_marks = []
        time_mark = 0
        while time_mark < self.clip_metadata.duration_s:
            time_marks.append(round(time_mark, 2))  #
            time_mark += step

        return time_marks

    def generate_preview(self, video_file_clip: VideoFileClip):
        preview_creator = StoryboardCreator()
        last_frame_width = int(self.duration_in_px % self.scaled_frame_width)  # 675 % 88 = 59
        last_frame_percentage = last_frame_width / self.scaled_frame_width  # 0.6704
        time_step = self.scaled_frame_width / self.px_per_sec
        # ________________ TEMP ___________________________
        if time_step > self.clip_metadata.duration_s:
            time_step = self.clip_metadata.duration_s

        # TODO: доделать

        print(time_step)
        return preview_creator.generate_preview_data(video_file_clip, time_step, last_frame_percentage)

    def run(self):
        try:
            clip = VideoFileClip(self.clip_metadata.filename)
            self.scan_metadata(clip)
            clip = clip.resized(height=self.scaled_frame_height)
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
    frame = np.ascontiguousarray(frame)
    image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)
