from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QPointF, QObject, pyqtSignal, QThread, QRunnable, QThreadPool
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout

from moviepy import VideoFileClip

from src import debug_manager


@dataclass
class ClipData:
    filename: str
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    preview_small: QPixmap = None


class VideoFileAnalyzerSignals(QObject):
    finished = pyqtSignal(ClipData)
    error = pyqtSignal(str)


class VideoFileAnalyzer(QRunnable):
    def __init__(self, file_path: str):
        super().__init__()
        self.clip_data = ClipData(file_path)
        self.signals = VideoFileAnalyzerSignals()

    @staticmethod
    def frame_to_pixmap(frame: np.ndarray):
        h, w, ch = frame.shape
        image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(image)

    def generate_preview(self, video_file_clip:VideoFileClip):
        frame = video_file_clip.get_frame(1)
        self.clip_data.preview_small = self.frame_to_pixmap(frame)

    def scan_metadata(self, video_file_clip: VideoFileClip):
        self.clip_data.duration_s = video_file_clip.duration
        self.clip_data.width, self.clip_data.height = video_file_clip.size

    def run(self):
        try:
            clip = VideoFileClip(self.clip_data.filename)
            self.generate_preview(clip)
            self.scan_metadata(clip)
            clip.close()
        except Exception as e:
            self.signals.error.emit("ERROR "+ str(e))
        else:
            self.signals.finished.emit(self.clip_data)


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def __init__(self):
        super().__init__()

    def get_items(self) ->list:
        return sorted(self.items(), key=lambda item: item.x())


class VideoPreviewItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF, clip: ClipData):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.scene = scene
        self.prev_pos = init_pos
        self.clip = ClipData(clip.filename)
        self.setPos(init_pos)

    def _change_order(self, proposed_pos: QPointF):
        """"""
        if proposed_pos == self.prev_pos:
            return

        last_grid_position = self.scene.ITEMS_ROFFSET
        for item in self.scene.get_items():
            if item.x() > last_grid_position:
                item.update_position(QPointF(last_grid_position, 0))

            if item.x() < proposed_pos.x():
                last_grid_position += item.sceneBoundingRect().width()
                continue
            item.update_position(QPointF(last_grid_position, 0))
            last_grid_position += item.sceneBoundingRect().width()

    def update_position(self, pos: QPointF):
        self.setPos(pos)
        self.prev_pos = pos

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            x = value.x()
            if value.x() < 0:
                x = 0
            self.setPos(x, 0)

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        self._change_order(self.pos())
        super().mouseReleaseEvent(event)

    def __repr__(self):
        return f'{self.clip.filename}; pos: {self.x()}'


class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.scene = Scene()
        self.scene.focusItemChanged.connect(self.debug_action)
        self.init_scene_mock()

        self.track_view = QGraphicsView()
        self.track_view.setSceneRect(0, 0, 800, 50)
        self.track_view.setStyleSheet('background-color: black;')

        self.track_view.setScene(self.scene)
        self.btn_debug = QPushButton('debug scene')
        self.btn_debug.clicked.connect(self.debug_pressed)
        debug_manager.register_widget(self.btn_debug)

        layout = QHBoxLayout()
        layout.addWidget(self.btn_debug)
        layout.addWidget(self.track_view)
        self.setLayout(layout)

    def debug_pressed(self, value=None):
        print(self.scene.get_items())

    def debug_action(self, *args):
        print(args)

    def init_scene_mock(self):
        start_img_width = 100
        step = 50
        pos = self.scene.ITEMS_ROFFSET
        for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi', 'D:/PythonProjects/videoConcat/video/vid2.mp4']):
            self.add_video_preview(file_path)
            # clip = VideoFileClip(file_path)
            # frame = clip.get_frame(1)
            # clip.close()
            # width = start_img_width + i * step
            # pixmap_item = VideoPreviewItem(self.frame_to_pixmap(frame).scaled(width, 50),
            #                                self.scene,
            #                                QPointF(pos, 0),
            #                                ClipData(file_path))
            # self.scene.addItem(pixmap_item)
            # pos += width

    @staticmethod
    def frame_to_pixmap(frame: np.ndarray):
        h, w, ch = frame.shape
        image = QImage(frame.tobytes(), w, h, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(image)

    def _find_pos_x(self):
        items_list = self.scene.get_items()
        pos_x = self.scene.ITEMS_ROFFSET
        if items_list:
            pos_x = items_list[-1].x() + items_list[-1].sceneBoundingRect().width()

        return pos_x

    def on_analysis_ready(self, clip_data: ClipData):
        pixmap_item = VideoPreviewItem(
            clip_data.preview_small.scaled(100, 50),
            self.scene,
            QPointF(self._find_pos_x(), 0),
            clip_data,
        )
        self.scene.addItem(pixmap_item)

    def on_analysis_error(self, error: str):
        print(error)

    def add_video_preview(self, file_path: str):
        worker = VideoFileAnalyzer(file_path)
        worker.signals.finished.connect(self.on_analysis_ready)
        worker.signals.error.connect(self.on_analysis_error)
        self.threadpool.start(worker)


if __name__ == '__main__':
    pass