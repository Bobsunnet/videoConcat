from PyQt6.QtCore import QPointF, QThreadPool, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout, QVBoxLayout

from src import debug_manager
from src.UI.color import ColorOptions
from src.options import DEBUG
from src.schemas import ClipMetaData
from src.workers import VideoDataAnalyzer


class TracksView(QGraphicsView):
    def __init__(self, parent:'PreviewWindow'=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)

        width = max(self.sceneRect().width(), self.width())
        self.setSceneRect(0, 0, width, self.height())


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

    def remove_field_gaps(self):
        """
        Shifts all items in the scene to the left, removing any gaps between them.

        Used when the user removes a preview item from the scene.
        """
        items = self.get_items()
        if items:
            pos_x = self.ITEMS_ROFFSET
            for item in items:
                item.update_position(QPointF(pos_x, 0))
                pos_x += item.sceneBoundingRect().width()


class VideoPreviewItem(QGraphicsPixmapItem):
    DEFAULT_Z_VALUE = 0
    SELECTED_Z_VALUE = 1

    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF, clip: ClipMetaData):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.scene = scene
        self.prev_pos = init_pos
        self.clip_data = ClipMetaData(clip.filename)
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

            y = self.pixmap().height() // 2
            self.setPos(x,y)

        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value: # value is 1 if item was selected and 0 if it was unselected
                self.setZValue(self.SELECTED_Z_VALUE)
            else:
                self.setZValue(self.DEFAULT_Z_VALUE)

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        self._change_order(self.pos())
        super().mouseReleaseEvent(event)

    def __repr__(self):
        return f'{self.clip_data.filename}; pos: {self.x()}'


class PreviewWindow(QWidget):
    item_selected = pyqtSignal(ClipMetaData)
    item_removed = pyqtSignal(ClipMetaData)
    TRACK_VIEW_HEIGHT = 41

    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.scene = Scene()
        self.pixels_per_second = 10
        self.start_width = 800
        self.scene.selectionChanged.connect(self.on_selectionChanged)
        self.init_scene_mock()

        self.track_view = TracksView(self)
        # self.track_view.setSceneRect(0, 0, self.start_width, self.TRACK_VIEW_HEIGHT)
        self.track_view.setStyleSheet(f'background-color: {ColorOptions.dimmer};')
        self.track_view.setScene(self.scene)

        self.btn_debug = QPushButton('DBG_scn')
        self.btn_debug.clicked.connect(self.debug_pressed)

        debug_manager.register_widget(self.btn_debug)

        layout = QHBoxLayout()
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.btn_debug)
        layout.addLayout(btn_layout)
        layout.addWidget(self.track_view)
        self.setLayout(layout)

    def debug_pressed(self, value=None):
        print(self.scene.get_items())

    def debug_action(self, *args):
        print('SIGNAL EMITTED')

    @pyqtSlot()
    def on_remove_selected(self):
        items:list[VideoPreviewItem] = self.scene.selectedItems()
        if items:
            selected_item = items[0]
            self.scene.removeItem(selected_item)
            self.scene.remove_field_gaps()
            self.item_removed.emit(selected_item.clip_data)
            print(selected_item.clip_data.filename)

    @pyqtSlot()
    def on_selectionChanged(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            self.item_selected.emit(selected_items[0].clip_data)

    def init_scene_mock(self):
        if not DEBUG:
            return

        for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid2.mp4', 'D:/PythonProjects/videoConcat/video/video_valera.mp4']):
            self.add_video_preview(file_path)

    def _find_last_pos_x(self):
        items_list = self.scene.get_items()
        pos_x = self.scene.ITEMS_ROFFSET
        if items_list:
            pos_x = items_list[-1].x() + items_list[-1].sceneBoundingRect().width()

        return pos_x

    def on_analysis_ready(self, clip_data: ClipMetaData):
        preview_item = VideoPreviewItem(
            clip_data.preview_large.scaled(clip_data.duration_in_px, self.TRACK_VIEW_HEIGHT),
            self.scene,
            QPointF(self._find_last_pos_x(), 0),
            clip_data,
        )
        self.scene.addItem(preview_item)

    def on_analysis_error(self, error: str):
        print(error)

    def add_video_preview(self, file_path: str):
        worker = VideoDataAnalyzer(file_path,
                                   px_per_sec=self.pixels_per_second,
                                   preview_frame_height=self.TRACK_VIEW_HEIGHT)
        worker.signals.finished.connect(self.on_analysis_ready)
        worker.signals.error.connect(self.on_analysis_error)
        self.threadpool.start(worker)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.on_remove_selected()
        else:
            super().keyPressEvent(event)


if __name__ == '__main__':
    pass