from PyQt6.QtCore import QUrl, Qt, QDir, QTime, pyqtSlot
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSlider, QFileDialog, QLabel

from src import debug_manager


class DropOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            parent = self.parent()
            if isinstance(parent, VideoPlayer):
                parent.connect_video_to_player(file_path)
                parent.change_btn_play_name(True)


class VideoPlayer(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = ''

        self.setContentsMargins(20, 20, 20, 40)
        self.setGeometry(10, 10, 400, 300)
        self.setStyleSheet('background-color: #99a;')

        self.video_window = QVideoWidget(parent=self)
        self.video_window.setGeometry(10, 10, 400, 225)
        self.drop_overlay = DropOverlay(self)
        self.drop_overlay.setGeometry(self.video_window.geometry())

        self.player = QMediaPlayer(parent=self)
        self.player.setVideoOutput(self.video_window)
        self.audioOutput = QAudioOutput()
        self.audioOutput.setVolume(0.8)
        self.player.setAudioOutput(self.audioOutput)

        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.player_position_changed)
        self.player.mediaStatusChanged.connect(self.play_status_changed)

        self.video_slider = QSlider(parent=self)
        self.video_slider.setOrientation(Qt.Orientation.Horizontal)
        self.video_slider.sliderPressed.connect(self.slider_pressed)
        self.video_slider.sliderMoved.connect(self.slider_pressed)

        self.audio_slider = QSlider()
        self.audio_slider.setOrientation(Qt.Orientation.Horizontal)
        self.audio_slider.setValue(80)
        self.audio_slider.valueChanged.connect(lambda x: self.audioOutput.setVolume(x / 100))

        self.lbl_timer = QLabel('00:00:00')
        self.lbl_timer.setMaximumHeight(22)

        self.btn_open_file = QPushButton("Open File", parent=self)
        self.btn_open_file.clicked.connect(self.open_file)

        self.btn_play = QPushButton("Play", parent=self)
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.play_pressed)

        self.btn_stop = QPushButton("Stop", parent=self)
        self.btn_stop.clicked.connect(self.stop_pressed)

        self.btn_debug = QPushButton("DEBUG", parent=self)
        self.btn_debug.clicked.connect(self._debug_pressed)
        debug_manager.register_widget(self.btn_debug)
        debug_manager.register_signal(self.player.mediaStatusChanged, self._debug_action)

        self.init_layout()

    def resizeEvent(self, event):
        self.drop_overlay.setGeometry(self.video_window.geometry())
        super().resizeEvent(event)

    def init_layout(self, debug_btn=None):
        main_layout = QVBoxLayout()
        screen_layout = QVBoxLayout()
        slider_layout = QHBoxLayout()

        screen_layout.addWidget(self.video_window)
        slider_layout.addWidget(self.video_slider)
        slider_layout.addWidget(self.lbl_timer)
        screen_layout.addLayout(slider_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.btn_open_file)
        buttons_layout.addWidget(self.btn_stop)
        buttons_layout.addWidget(self.btn_play)
        buttons_layout.addWidget(self.audio_slider)
        buttons_layout.addWidget(self.btn_debug)

        main_layout.addLayout(screen_layout)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def _debug_pressed(self, value=None):
        """"""

    def _debug_action(self, value=None):
        """"""
        print(self.player.mediaStatus())

    def play_pressed(self):
        playing = self.player.isPlaying()
        self.change_btn_play_name(playing)

        if self.player.isPlaying():
            self.player.pause()
        else:
            self.player.play()

    def change_btn_play_name(self, status: bool):
        if status:
            self.btn_play.setText("Play")
        else:
            self.btn_play.setText("Pause")

    def stop_pressed(self):
        self.player.stop()
        self.change_btn_play_name(True)

    def player_position_changed(self):
        position_ms = self.player.position()
        self.video_slider.setValue(position_ms)
        qtime = QTime(0, 0, 0, 0)
        qtime = qtime.addMSecs(position_ms)
        self.lbl_timer.setText(qtime.toString())

    def slider_pressed(self):
        self.player.setPosition(self.video_slider.value())

    def duration_changed(self, value: int):
        self.video_slider.setRange(0, value)

    @pyqtSlot()
    def play_status_changed(self):
        status = self.player.mediaStatus()
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.btn_play.setEnabled(True)
        elif status == QMediaPlayer.MediaStatus.NoMedia or status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.btn_play.setEnabled(False)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.change_btn_play_name(True)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open Video File',
                                                  QDir.currentPath(),
                                                  "Media (*.webm *.mp4 *.ts *.avi *.mpeg *.mpg *.mkv *.VOB *.m4v *.3gp "
                                                  "*.mp3 *.m4a *.wav *.ogg *.flac *.m3u *.m3u8)")

        print('open status: ', filename)

        if filename != '':
            self.connect_video_to_player(filename)

    def connect_video_to_player(self, file_path:str):
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.filename = file_path
        self.change_btn_play_name(True)