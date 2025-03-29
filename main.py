import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout

from src.video_player import VideoPlayer
from src.video_editor import VideoEditor
from src.UI.color import ColorBackground, ColorOptions


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Concatenator")
        self.left_player = VideoPlayer(parent=self)
        self.right_player = VideoPlayer(parent=self)
        self.editor = VideoEditor(self.left_player, self.right_player)

        self.setGeometry(400, 200, 800, 600)
        self.setMinimumSize(800, 600)

        self.init_layout()

    def init_layout(self):
        main_layout_widget = ColorBackground(ColorOptions.darker)
        main_layout = QVBoxLayout()

        video_player_background = ColorBackground(ColorOptions.dim)
        video_layout = QHBoxLayout()
        video_layout.addWidget(self.left_player)
        video_layout.addWidget(self.right_player)
        video_player_background.setLayout(video_layout)

        editor_background = ColorBackground(ColorOptions.darkish_lighter)
        editor_background.setMaximumHeight(70)

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
    window.left_player.audioOutput.setVolume(0.8)
    window.show()
    sys.exit(app.exec())