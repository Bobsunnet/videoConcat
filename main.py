import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QStatusBar

from src.video_player import VideoPlayer
from src.video_editor import VideoEditor
from src.UI.color import ColorBackground, ColorOptions

from src.updater import UpdateManager


class PreviewEditorMediator:
    def __init__(self, editor:VideoEditor, player:VideoPlayer):
        self.editor = editor
        self.player = player
        self.connect_loading()
        self.connect_dropping()

    def connect_loading(self):
        self.editor.preview_window.item_selected.connect(lambda clip_data: self.player.connect_video_to_player(clip_data.filename))

    def connect_dropping(self):
        self.player.file_dropped.connect(self.editor.preview_window.add_video_preview)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Concatenator")
        self.update_manager = UpdateManager()
        self.video_player = VideoPlayer(parent=self)
        self.editor = VideoEditor(self.video_player, parent=self)
        self.mediator = PreviewEditorMediator(self.editor, self.video_player)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.setGeometry(400, 100, 1000, 800)
        self.setMinimumSize(1000, 800)

        self.init_layout()
        self.update_manager.check_for_updates()

    def init_layout(self):
        main_layout_widget = ColorBackground(ColorOptions.darker)
        main_layout = QVBoxLayout()

        video_player_background = ColorBackground(ColorOptions.dim)
        video_layout = QHBoxLayout()
        video_layout.addWidget(self.video_player)
        video_player_background.setLayout(video_layout)

        editor_background = ColorBackground(ColorOptions.darkish_lighter)
        editor_background.setMaximumHeight(180)

        editor_layout = QHBoxLayout()
        editor_layout.addWidget(self.editor)
        editor_background.setLayout(editor_layout)

        main_layout.addWidget(video_player_background)
        main_layout.addWidget(editor_background)
        main_layout_widget.setLayout(main_layout)
        self.setCentralWidget(main_layout_widget)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.video_player.audioOutput.setVolume(0.8)
    window.show()
    sys.exit(app.exec())