import os

from PyQt6.QtCore import QDir, QObject, pyqtSignal, pyqtSlot, QRunnable, QThreadPool
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFileDialog, QComboBox, QVBoxLayout
from PyQt6.QtMultimedia import QMediaPlayer

from moviepy import VideoFileClip, VideoClip
from moviepy.video.compositing import CompositeVideoClip

from src.UI.color import ColorBackground, ColorOptions
from src.UI.progress_bar import ProgressBar
from src.widget_logger import WidgetProgressLogger
from src.TracksView import PreviewWindow

from src import debug_manager


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


class ConcatenatorSignals(QObject):
    """Signals container for ConcatenatorWorker"""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)


class ConcatenatorWorker(QRunnable):

    def __init__(self, clips: list[VideoFileClip], file_path: str, method: str = 'chain'):
        super().__init__()
        self.video_concat: VideoClip | None = None
        self.signals = ConcatenatorSignals()
        self.clips = clips
        self.file_path = file_path
        self.method = method

    def run(self):
        try:
            self.video_concat = (CompositeVideoClip
                             .concatenate_videoclips(self.clips, method=self.method)
                             .write_videofile(self.file_path, logger=WidgetProgressLogger(self.signals.progress))
                             )
        except Exception as e:
            self.signals.error.emit("ERROR "+ str(e))

        else:
            self.signals.finished.emit()


class VideoEditor(QWidget):
    def __init__(self, video_player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview_window = PreviewWindow()
        self.threadpool = QThreadPool()
        self.parent = kwargs.get('parent', None)
        self.player = video_player
        self.btn_open_file = QPushButton("Open File", parent=self)
        self.btn_open_file.clicked.connect(self.add_file_to_view)

        self.btn_process_file = QPushButton("Process File", parent=self)
        self.btn_process_file.setMinimumSize(100, 30)
        self.btn_process_file.clicked.connect(self.process_file)
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.cbox_method = QComboBox()
        self.cbox_method.addItem('Chain')
        self.cbox_method.addItem('Compose')

        self.btn_debug = QPushButton("DEBUG_editor")
        self.btn_debug.clicked.connect(self._debug_pressed)
        debug_manager.register_widget(self.btn_debug)

        self._init_layout()

    def _init_layout(self):
        main_layout = QVBoxLayout()
        preview_background = ColorBackground(ColorOptions.darker)
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(self.preview_window)
        preview_background.setLayout(preview_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.btn_open_file)
        buttons_layout.addWidget(self.btn_process_file)
        buttons_layout.addWidget(self.cbox_method)
        buttons_layout.addWidget(self.btn_debug)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.progress_bar)
        main_layout.addWidget(preview_background)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def process_file(self):
        # if not self._player_status_check():
        #     print('No media ready for concatenation')
        #     return

        folder_path = QFileDialog().getExistingDirectory(self, 'Destination Folder', QDir.currentPath())
        if folder_path == '':
            return

        clip_items = [item.clip for item in self.preview_window.scene.get_items()]

        if len(clip_items) == 0:
            print("No videos in preview window.")
            return

        self.progress_bar.setVisible(True)
        res_file_path = self._create_concat_file_path(
            folder_path,
            [clip.filename for clip in clip_items],
            )

        worker = ConcatenatorWorker(clip_items,
            file_path=res_file_path,
            method=self.cbox_method.currentText().lower()
        )
        worker.signals.progress.connect(self.progress_bar.progress_changed)
        worker.signals.finished.connect(self._processing_finished)
        worker.signals.error.connect(self.worker_error)
        self.btn_process_file.setEnabled(False)

        self.threadpool.start(worker)

    @pyqtSlot()
    def _processing_finished(self):
        """ Slot called when the processing is finished """
        self.progress_bar.init_scale()
        self.progress_bar.setVisible(False)
        self.btn_process_file.setEnabled(True)

    @pyqtSlot()
    def _debug_pressed(self):
        """
        Debug button pressed."""

    def _player_status_check(self) ->bool:
        """
        Checks if both players have valid media status.

        Checks if the media status of both players is not in the list of
        invalid statuses.

        Returns:
            bool: True if both status are valid, False otherwise.
        """
        invalid_status = [QMediaPlayer.MediaStatus.LoadingMedia,
                          QMediaPlayer.MediaStatus.InvalidMedia,
                          QMediaPlayer.MediaStatus.NoMedia,
                          QMediaPlayer.MediaStatus.StalledMedia]
        bad_status = self.player.player.mediaStatus() in invalid_status
        if bad_status:
            return False

        return True

    def _create_concat_file_path(self, folder_path:str, files_list:list[str])->str:
        """
        Creates a file path for concatenated video

        Concatenates the names of the two files, removes the extension
        and adds '.mp4' to the end of the new name.

        Args:
            folder_path (str): The path to the folder where the new file
                should be saved.

        Returns:
            str: The full path to the new file.
        """
        concat_final_name = ''
        for file_name in files_list:
            concat_final_name += os.path.split(file_name)[-1].rpartition('.')[0]
            concat_final_name += '__'

        concat_final_name += '.mp4'
        save_path = os.path.join(folder_path, concat_final_name)
        return save_path

    def add_file_to_view(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open Video File',
                                                  QDir.currentPath(),
                                                  "Media (*.webm *.mp4 *.ts *.avi *.mpeg *.mpg *.mkv *.VOB *.m4v *.3gp "
                                                  "*.mp3 *.m4a *.wav *.ogg *.flac *.m3u *.m3u8)")

        if filename != '':
            self.preview_window.add_video_preview(filename)

    @pyqtSlot(str)
    def worker_error(self, error:str):
        print('ERROR: %s' % error)


if __name__ == '__main__':
    pass
    # vc = ClipConcatenator()
    # clip = vc.run_concatenation(VideoFileClip("../video/video_v1.mp4"), VideoFileClip("../video/video_v2.mp4"))
    # clip.write_videofile("output.mp4")
