from PyQt6.QtCore import QPointF, QThreadPool, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton, QWidget, QGraphicsItem, \
    QGraphicsPixmapItem, QHBoxLayout, QVBoxLayout, QGraphicsLineItem, QGraphicsItemGroup, QGraphicsTextItem

from src import debug_manager
from src.UI.color import ColorOptions
from src.options import DEBUG
from src.schemas import ClipMetaData, PreviewData
from src.workers import VideoDataAnalyzer
from src.workers.file_analyzer import StoryboardCreator


class TracksView(QGraphicsView):
    def __init__(self, parent: 'PreviewWindow' = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)

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


class TimelineTickItem(QGraphicsLineItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setPen(QColor(240, 0, 55))
        self.setZValue(1)


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.previews_items = []

    def addItem(self, item):
        if isinstance(item, VideoPreviewItem):
            self.previews_items.append(item)

        super().addItem(item)

    def removeItem(self, item):
        if isinstance(item, VideoPreviewItem):
            self.previews_items.remove(item)  # todo: get rid of this. Bug prone code

        super().removeItem(item)

    def get_items(self) -> list:
        """
        Returns the list of VideoPreviewItem items sorted by their x position.

        Used to keep the order of video previews in the correct order when the user moves them.
        """
        return sorted(self.previews_items, key=lambda item: item.x())

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

    def __init__(self, pixmap: QPixmap, scene: Scene, init_pos: QPointF, clip_metadata: ClipMetaData):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.scene = scene
        self.prev_pos = init_pos
        self.clip_metadata = clip_metadata
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
            self.setPos(x, y)

        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value:  # value is 1 if item was selected and 0 if it was unselected
                self.setZValue(self.SELECTED_Z_VALUE)
            else:
                self.setZValue(self.DEFAULT_Z_VALUE)

        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        self._change_order(self.pos())
        super().mouseReleaseEvent(event)

    def __repr__(self):
        return f'{self.clip_metadata.filename}; pos: {self.x()}'


class PreviewWindow(QWidget):
    item_selected = pyqtSignal(ClipMetaData)
    item_removed = pyqtSignal(ClipMetaData)
    TRACK_VIEW_HEIGHT = 40
    MAX_PX_PER_SEC = 100
    ZOOM_VARIANTS = [0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 50, 100]

    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.scene = Scene()
        self.clips_previews = []
        self.pixels_per_second = self.ZOOM_VARIANTS[5]  # frames per sec = 10[px/sec] / 70 [px] =0.1428 frames per sec
        self.scene.selectionChanged.connect(self.on_selectionChanged)
        self.grpTicks = QGraphicsItemGroup()
        self.grpLabels = QGraphicsItemGroup()
        self.scene.addItem(self.grpTicks)
        self.scene.addItem(self.grpLabels)

        self.init_scene_mock()
        self.draw_time_line()

        self.track_view = TracksView(self)
        self.track_view.setStyleSheet(f'background-color: {ColorOptions.dimmer};')
        self.track_view.setScene(self.scene)
        self.scene.setSceneRect(0, 0, self.track_view.width(), self.track_view.height())

        self.btn_debug = QPushButton('DBG_scn')
        self.btn_debug.clicked.connect(self.debug_pressed)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        debug_manager.register_widget(self.btn_debug)

        layout = QHBoxLayout()
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.btn_debug)
        btn_layout.addWidget(self.btn_zoom_in)
        btn_layout.addWidget(self.btn_zoom_out)
        layout.addLayout(btn_layout)
        layout.addWidget(self.track_view)
        self.setLayout(layout)

    def debug_pressed(self, value=None):
        print(self.grpLabels.childItems()[1].pos())
        print(self.grpTicks.childItems()[1].pos())

    def debug_action(self, *args):
        print('SIGNAL EMITTED')

    @pyqtSlot()
    def on_remove_selected(self):
        items: list[VideoPreviewItem] = self.scene.selectedItems()
        if items:
            selected_item = items[0]
            self.scene.removeItem(selected_item)
            self.scene.remove_field_gaps()
            self.item_removed.emit(selected_item.clip_metadata)
            # selected_item.deleteLater()
        self.update_scene_rect()

    @pyqtSlot()
    def on_selectionChanged(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            self.item_selected.emit(selected_items[0].clip_metadata)

    @pyqtSlot(str)
    def on_analysis_error(self, error: str):
        print(error)

    def init_scene_mock(self):
        if not DEBUG:
            return

        for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi',
                                       'D:/PythonProjects/videoConcat/video/video_v1.mp4', ]):
            self.add_video_track(file_path)

    def _find_last_pos_x(self):
        items_list = self.scene.get_items()
        pos_x = self.scene.ITEMS_ROFFSET
        if items_list:
            pos_x = items_list[-1].x() + items_list[-1].sceneBoundingRect().width()

        return pos_x

    def create_preview_item(self, preview_data: PreviewData):
        scaled_pixmap = preview_data.storyboard.scaled(preview_data.duration_in_px, self.TRACK_VIEW_HEIGHT)
        position = QPointF(self._find_last_pos_x(), 0)
        return VideoPreviewItem(scaled_pixmap, self.scene, position, preview_data.clip_metadata)

    def on_storyboard_ready(self, preview_data: PreviewData):
        self.add_preview_item(preview_data)

    @pyqtSlot(str)
    def on_storyboard_error(self, error: str):
        print(error)

    def run_storyboard_creation_worker(self, clip_metadata: ClipMetaData):
        duration_in_px = int(clip_metadata.duration_s * self.pixels_per_second)
        last_frame_width = int(duration_in_px % clip_metadata.scaled_width)  # 675 % 88 = 59
        last_frame_percentage = last_frame_width / clip_metadata.scaled_width  # 0.6704
        worker = StoryboardCreator(clip_metadata, duration_in_px, last_frame_percentage)
        worker.signals.finished.connect(self.on_storyboard_ready)
        worker.signals.error.connect(self.on_storyboard_error)
        self.threadpool.start(worker)

    def add_preview_item(self, preview_data: PreviewData):
        preview = self.create_preview_item(preview_data)
        self.scene.addItem(preview)
        self.update_scene_rect()

    def on_analysis_ready(self, clip_metadata: ClipMetaData):
        self.run_storyboard_creation_worker(clip_metadata)

    def add_video_track(self, file_path: str):
        worker = VideoDataAnalyzer(file_path,
                                   preview_frame_height=self.TRACK_VIEW_HEIGHT)
        worker.signals.finished.connect(self.on_analysis_ready)
        worker.signals.error.connect(self.on_analysis_error)
        self.threadpool.start(worker)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.on_remove_selected()
        else:
            super().keyPressEvent(event)

    def update_scene_rect(self):
        if self.scene.items():
            bounding_rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(bounding_rect)
        else:
            self.scene.setSceneRect(0, 0, self.track_view.width(), self.TRACK_VIEW_HEIGHT)

    # _________________ PORTED _____________________
    def _calc_timeline_width(self) -> int:
        width = self.scene.sceneRect().width()
        return int(width if width > 100 * self.pixels_per_second else 100 * self.pixels_per_second)

    def draw_time_line(self):
        self.grpLabels.setPos(0, 0)
        self.grpTicks.setPos(0, 0)
        self.draw_scale()
        self.draw_labels()
        self.grpLabels.setPos(0, -38)
        self.grpTicks.setPos(0, -38)

    def draw_scale(self):
        for el in self.grpTicks.childItems():
            self.scene.removeItem(el)

        for px in range(0, self._calc_timeline_width(), 10):
            tick_height = 10
            if px % (5 * 10) == 0:
                tick_height = 20

            tick = TimelineTickItem(px + self.scene.ITEMS_ROFFSET, 0, px + self.scene.ITEMS_ROFFSET, tick_height)
            self.grpTicks.addToGroup(tick)

    def draw_labels(self):
        for el in self.grpLabels.childItems():
            self.scene.removeItem(el)

        label_tick_height = 20
        step_px = 50
        for px in range(step_px, self._calc_timeline_width(), step_px):
            label = QGraphicsTextItem(str(round(px / self.pixels_per_second, 1)))
            label.setPos(px + self.scene.ITEMS_ROFFSET - 10, label_tick_height)
            self.grpLabels.addToGroup(label)

    def zoom_in(self):
        zoom_idx = self.ZOOM_VARIANTS.index(self.pixels_per_second)
        if zoom_idx == len(self.ZOOM_VARIANTS) - 1:
            return

        self.pixels_per_second = self.ZOOM_VARIANTS[zoom_idx + 1]
        self.draw_time_line()
        self.change_preview_size()

    def zoom_out(self):
        zoom_idx = self.ZOOM_VARIANTS.index(self.pixels_per_second)
        if zoom_idx == 0:
            return

        self.pixels_per_second = self.ZOOM_VARIANTS[zoom_idx - 1]
        self.draw_time_line()
        self.change_preview_size()

    def change_preview_size(self):
        clips_metadata_list = []
        for preview in self.scene.get_items():
            clips_metadata_list.append(preview.clip_metadata)
            self.scene.removeItem(preview)

        for clip_metadata in clips_metadata_list:
            self.run_storyboard_creation_worker(clip_metadata)


if __name__ == '__main__':
    pass
