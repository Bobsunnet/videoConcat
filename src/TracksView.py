import sys

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QVBoxLayout, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout

from src import debug_manager


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def __init__(self):
        super().__init__()

    def get_items(self):
        return sorted(self.items(), key=lambda item: item.x())


class VideoPreviewItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF = None, file: str = None):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.scene = scene
        self.prev_pos = init_pos
        self.file_name = file
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
        return f'{self.file_name}; pos: {self.x()}'


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
        # layout.addStretch()
        self.setLayout(layout)

    def debug_pressed(self, value=None):
        self.add_video_preview('./snippets/img/seagull.jpg')
        print(self.scene.get_items())

    def init_scene_mock(self):
        start_img_width = 100
        step = 50
        pos = self.scene.ITEMS_ROFFSET
        for i, img_path in enumerate(['./snippets/img/flowers.jpg',
                                      './snippets/img/sunset.jpg',
                                      './snippets/img/pyramid.jpg',]):
            width = start_img_width + i * step
            pixmap_item = VideoPreviewItem(QPixmap(img_path).scaled(width, 50), self.scene, QPointF(pos, 0), img_path)
            self.scene.addItem(pixmap_item)
            pos += width

    def add_video_preview(self, file_path: str):
        pos = self.scene.get_items()[-1].x() + self.scene.get_items()[-1].sceneBoundingRect().width()
        pixmap_item = VideoPreviewItem(
            QPixmap(file_path).scaled(100, 50),
            self.scene,
            QPointF(pos, 0),
            file_path,
        )
        self.scene.addItem(pixmap_item)


if __name__ == '__main__':
    pass
