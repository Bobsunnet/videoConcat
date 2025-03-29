from PyQt6.QtCore import QUrl, Qt, QDir, QTime
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSlider, QFileDialog, QSpacerItem, \
    QSizePolicy, QLabel


class VideoPlayer(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = ''

        self.setContentsMargins(20, 20, 20, 40)
        self.setGeometry(10, 10, 400, 300)
        self.setStyleSheet('background-color: #99a;')

        self.btn_debug = QPushButton("DEBUG", parent=self)
        self.btn_debug.setStyleSheet('background-color: #bbb;')
        self.btn_debug.clicked.connect(self.debug_pressed)

        self.create_player()
        self.init_layout()

    def create_player(self):
        self.video_window = QVideoWidget(parent=self)
        self.video_window.setGeometry(10, 10, 400, 225)

        self.player = QMediaPlayer(parent=self)
        # self.player.setSource(QUrl.fromLocalFile("video/vid1.mp4"))
        self.player.setVideoOutput(self.video_window)
        self.audioOutput = QAudioOutput()
        self.player.setAudioOutput(self.audioOutput)

        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.player_position_changed)
        self.player.mediaStatusChanged.connect(self.play_status_changed)

        self.video_slider = QSlider(parent=self)
        self.video_slider.setOrientation(Qt.Orientation.Horizontal)
        self.video_slider.sliderPressed.connect(self.slider_pressed)
        self.video_slider.sliderMoved.connect(self.slider_pressed)

        self.lbl_timer = QLabel('00:00:00')
        self.lbl_timer.setMaximumHeight(22)

        self.btn_open_file = QPushButton("Open File", parent=self)
        self.btn_open_file.clicked.connect(self.open_file)

        self.btn_play = QPushButton("Play", parent=self)
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.play_pressed)

        self.btn_stop = QPushButton("Stop", parent=self)
        self.btn_stop.clicked.connect(self.stop_pressed)

        self._connect_video_to_player("video/vid1.mp4")


    def init_layout(self):
        main_layout = QVBoxLayout()
        first_layout = QVBoxLayout()
        slider_layout = QHBoxLayout()
        second_layout = QHBoxLayout()

        first_layout.addWidget(self.video_window)
        slider_layout.addWidget(self.video_slider)
        slider_layout.addWidget(self.lbl_timer)
        first_layout.addLayout(slider_layout)

        main_layout.addLayout(first_layout)
        main_layout.addLayout(second_layout)
        second_layout.addWidget(self.btn_open_file)
        second_layout.addWidget(self.btn_stop)
        second_layout.addWidget(self.btn_play)
        second_layout.addSpacing(200)
        second_layout.addWidget(self.btn_debug)

        self.setLayout(main_layout)

    def debug_pressed(self, value=None):
        """"""

    def play_pressed(self):
        status = self.player.isPlaying()
        self.change_btn_play_name(status)

        if self.player.isPlaying():
            self.player.pause()
        else:
            self.player.play()

    def change_btn_play_name(self, play: bool):
        if play:
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
            self._connect_video_to_player(filename)

    def _connect_video_to_player(self, file_path:str):
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.filename = file_path
        self.change_btn_play_name(True)