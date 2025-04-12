from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from moviepy import  VideoClip, VideoFileClip
from moviepy.video.compositing import CompositeVideoClip
from src import WidgetProgressLogger


class ClipContentProvider:
    def __init__(self, clips_list: list):
        self.clips_data_list = clips_list

    def get_video_clips(self) ->list[VideoFileClip]:
        return [VideoFileClip(clip.filename) for clip in self.clips_data_list]


class ConcatenatorSignals(QObject):
    """Signals container for ConcatenatorWorker"""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)


class ConcatenatorWorker(QRunnable):
    def __init__(self, clips_data_list: list, file_path: str, concat_method: str = 'chain'):
        super().__init__()
        self.video_concat: VideoClip | None = None
        self.signals = ConcatenatorSignals()
        self.clips = clips_data_list
        self.file_path = file_path
        self.concat_method = concat_method

    def run(self):
        try:
            self.video_concat = (CompositeVideoClip
                             .concatenate_videoclips(ClipContentProvider(self.clips).get_video_clips(), method=self.concat_method)
                             .write_videofile(self.file_path, logger=WidgetProgressLogger(self.signals.progress))
                             )
        except Exception as e:
            self.signals.error.emit("ERROR "+ str(e))

        else:
            self.signals.finished.emit()

