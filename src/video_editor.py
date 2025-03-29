from PyQt6.QtCore import QDir, QThread, QObject, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFileDialog, QSizePolicy

from moviepy import VideoFileClip, VideoClip
from moviepy.video.compositing import CompositeVideoClip

from src.UI.progress_bar import ProgressBar
from src.widget_logger import WidgetProgressLogger


class VideoCutter:
    def __init__(self):
        self.file_edited: VideoFileClip | None = None

    def cut_video(self, file_path: str, start_ms: int, end_ms: int) -> VideoFileClip:
        self.file_edited = VideoFileClip(file_path).subclipped(start_ms / 1000, end_ms / 1000)
        return self.file_edited

    def write_edited_file(self, file_name: str):
        if self.file_edited is not None:
            self.file_edited.write_videofile(f"{file_name}.mp4")
        else:
            print("No file edited")


class ClipConcatenator(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, clips: list[VideoFileClip], file_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_concat: VideoClip | None = None
        self.clips = clips
        self.file_path = file_path

    def run_concatenation(self):
        self.video_concat = (CompositeVideoClip
                             .concatenate_videoclips(self.clips, method="compose")
                             .write_videofile(self.file_path, logger=WidgetProgressLogger(self.progress))
                             )
        self.finished.emit()


class VideoEditor(QWidget):
    def __init__(self, left_player, right_player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player1 = left_player
        self.player2 = right_player
        self.btn_process_file = QPushButton("Process File", parent=self)
        self.btn_process_file.setMinimumSize(100, 30)
        self.btn_process_file.clicked.connect(self.process_file)
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)

        self.init_layout()

    def init_layout(self):
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.btn_process_file)
        main_layout.addStretch()
        main_layout.addWidget(self.progress_bar)
        self.setLayout(main_layout)

    def process_file(self):
        folder_path = QFileDialog().getExistingDirectory(self, 'Destination Folder', QDir.currentPath())
        if folder_path == '':
            return

        self.progress_bar.setVisible(True)
        file_path = folder_path + '/testOutput.mp4'  # :todo make this dynamic
        self.concat_thread = QThread()
        self.worker = ClipConcatenator(
            [VideoFileClip(self.player1.filename),
             VideoFileClip(self.player2.filename)],
            file_path=file_path
        )
        self.worker.moveToThread(self.concat_thread)
        self.concat_thread.started.connect(self.worker.run_concatenation)
        self.worker.finished.connect(self.concat_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.progress.connect(self.progress_bar.progress_changed)
        self.concat_thread.finished.connect(self.concat_thread.deleteLater)
        self.concat_thread.start()

        self.btn_process_file.setEnabled(False)
        self.concat_thread.finished.connect(self.processing_finished)

    @pyqtSlot()
    def processing_finished(self):
        self.progress_bar.init_scale()
        self.progress_bar.setVisible(False)
        self.btn_process_file.setEnabled(True)


if __name__ == '__main__':
    pass
    # vc = ClipConcatenator()
    # clip = vc.run_concatenation(VideoFileClip("../video/video_v1.mp4"), VideoFileClip("../video/video_v2.mp4"))
    # clip.write_videofile("output.mp4")
