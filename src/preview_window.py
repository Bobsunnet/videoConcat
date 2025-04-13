from PyQt6.QtCore import QPointF, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout

from src import debug_manager
from src.schemas import ClipData
from src.workers import VideoDataAnalyzer


class TracksView(QGraphicsView):
    def __init__(self, parent:'PreviewWindow'=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dragMoveEvent(self, event):
        """ need to be reimplemented along with dragEnterEvent and dropEvent """
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            self.parent().add_video_preview(file_path)


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def __init__(self):
        super().__init__()

    def get_items(self) ->list:
        """
        Returns the list of VideoPreviewItem items sorted by their x position.

        Used to keep the order of video previews in the correct order when the user moves them.
        """
        return sorted(self.items(), key=lambda item: item.x())


class VideoPreviewItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF, clip: ClipData):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.scene = scene
        self.prev_pos = init_pos
        self.clip_data = ClipData(clip.filename)
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
        return f'{self.clip_data.filename}; pos: {self.x()}'


class PreviewWindow(QWidget):
    item_selected = pyqtSignal(ClipData)
    START_WIDTH = 800

    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.scene = Scene()
        self.scene.selectionChanged.connect(self.on_selectionChanged)
        self.init_scene_mock()

        self.track_view = TracksView(self)
        self.track_view.setSceneRect(0, 0, self.START_WIDTH, 50)
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
        items = self.scene.selectedItems()
        if items:
            print(items[0].clip_data)
            print()

        for el in self.scene.get_items():
            print(el.clip_data)

    def debug_action(self, *args):
        print('SIGNAL EMITTED')

    @pyqtSlot()
    def on_selectionChanged(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            clip_data = selected_items[0].clip_data
            self.item_selected.emit(clip_data)

    def init_scene_mock(self):
        for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi', 'D:/PythonProjects/videoConcat/video/vid2.mp4']):
            self.add_video_preview(file_path)

    def _find_pos_x(self):
        items_list = self.scene.get_items()
        pos_x = self.scene.ITEMS_ROFFSET
        if items_list:
            pos_x = items_list[-1].x() + items_list[-1].sceneBoundingRect().width()

        return pos_x

    def on_analysis_ready(self, clip_data: ClipData):
        preview_item = VideoPreviewItem(
            clip_data.preview_small.scaled(100, 50),
            self.scene,
            QPointF(self._find_pos_x(), 0),
            clip_data,
        )
        self.scene.addItem(preview_item)

    def on_analysis_error(self, error: str):
        print(error)

    def add_video_preview(self, file_path: str):
        worker = VideoDataAnalyzer(file_path)
        worker.signals.finished.connect(self.on_analysis_ready)
        worker.signals.error.connect(self.on_analysis_error)
        self.threadpool.start(worker)


if __name__ == '__main__':
    pass