from PyQt6.QtCore import QThreadPool

from src.schemas import ClipMetaData
from src.workers import VideoDataAnalyzer
from src.workers import StoryboardCreator


class PreviewWorkersManager:
    def __init__(self):
        self.thread_pool = QThreadPool()

    def run_storyboard_creation_worker(self, clip_metadata: ClipMetaData, pixels_per_second: int, on_ready, on_error):
        duration_in_px = int(clip_metadata.duration_s * pixels_per_second)
        last_frame_width = int(duration_in_px % clip_metadata.scaled_width)  # 675 % 88 = 59
        last_frame_percentage = last_frame_width / clip_metadata.scaled_width  # 0.6704
        worker = StoryboardCreator(clip_metadata, duration_in_px, last_frame_percentage)
        worker.signals.finished.connect(on_ready)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)

    def run_video_analysis_worker(self, file_path: str, tracks_view_height, on_ready, on_error):
        worker = VideoDataAnalyzer(file_path, preview_frame_height=tracks_view_height)
        worker.signals.finished.connect(on_ready)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)
