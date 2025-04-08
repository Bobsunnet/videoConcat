import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout

from moviepy import VideoFileClip

from src import debug_manager


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def __init__(self):
        super().__init__()

    def get_items(self):
        return sorted(self.items(), key=lambda item: item.x())


class VideoPreviewItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF, clip: VideoFileClip):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.scene = scene
        self.prev_pos = init_pos
        self.clip = clip
        self.file_name = clip.filename
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
        return f'{self.clip.filename if self.clip else self.file_name}; pos: {self.x()}'


class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.scene = Scene()
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

    def init_scene_mock(self):
        start_img_width = 100
        step = 50
        pos = self.scene.ITEMS_ROFFSET
        for i, img_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi', 'D:/PythonProjects/videoConcat/video/vid2.mp4']):
            clip = VideoFileClip(img_path)
            frame = clip.get_frame(1)
            width = start_img_width + i * step
            pixmap_item = VideoPreviewItem(self.frame_to_pixmap(frame).scaled(width, 50),
                                           self.scene,
                                           QPointF(pos, 0),
                                           clip)
            self.scene.addItem(pixmap_item)
            pos += width

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

    def add_video_preview(self, file_path: str):
        clip = VideoFileClip(file_path)
        frame = clip.get_frame(1)
        pixmap = self.frame_to_pixmap(frame)

        pixmap_item = VideoPreviewItem(
            pixmap.scaled(100, 50),
            self.scene,
            QPointF(self._find_pos_x(), 0),
            clip,
        )
        self.scene.addItem(pixmap_item)


if __name__ == '__main__':
    pass