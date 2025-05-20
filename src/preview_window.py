import time

from PyQt6.QtCore import QPointF, QThreadPool, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import (QGraphicsScene, QPushButton, QWidget, QHBoxLayout,
                             QVBoxLayout, QGraphicsItemGroup, QGraphicsTextItem)

from src import debug_manager
from src.UI.color import ColorOptions
from src.schemas import ClipMetaData, PreviewData
from src.tracks_view import TracksView, TimelineTickItem
from src.video_preview_item import VideoPreviewItem
from src.workers import VideoDataAnalyzer
from src.workers.file_analyzer import StoryboardCreator


class Scene(QGraphicsScene):
    ITEMS_ROFFSET = 2

    def get_items(self) -> list:
        """
        Returns the list of VideoPreviewItem items sorted by their x position.

        Used to keep the order of video previews in the correct order when the user moves them.
        """
        return sorted([item for item in self.items() if isinstance(item, VideoPreviewItem)],
                      key=lambda item: item.x())

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


class PreviewWindow(QWidget):
    item_selected = pyqtSignal(ClipMetaData)
    item_removed = pyqtSignal(ClipMetaData)
    resizing_completed = pyqtSignal()
    TRACK_VIEW_HEIGHT = 40
    MAX_PX_PER_SEC = 100
    ZOOM_VARIANTS = [0.5, 1, 2, 5, 10, 15, 20, 30, 50, 80, 100]

    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.scene = Scene()
        self.total_previews = 0
        self.pending_previews = 0
        self.original_previews_order = []

        self.pixels_per_second = self.ZOOM_VARIANTS[4]  # frames per sec = 10[px/sec] / 70 [px] =0.1428 frames per sec
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
        self.resizing_completed.connect(self.sort_after_resizing)

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
        print(self.scene.get_items())

    def debug_action(self, *args):
        print('SIGNAL EMITTED')

    @pyqtSlot()
    def on_remove_selected(self):
        items: list[VideoPreviewItem] = self.scene.selectedItems()
        if items:
            selected_item = items[0]
            self.scene.removeItem(selected_item)
            # self.scene.remove_field_gaps()
            self.item_removed.emit(selected_item.clip_metadata)

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
        if debug_manager.debug_is_on:
            for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi',
                                           'D:/PythonProjects/videoConcat/video/video_v1.mp4', ]):
                self.add_video_track(file_path)

    def _find_last_pos_x(self):
        items_list = self.scene.get_items()
        pos_x = self.scene.ITEMS_ROFFSET
        if items_list:
            last_item_width = items_list[-1].sceneBoundingRect().width()
            pos_x = items_list[-1].x() + last_item_width

        return pos_x

    def create_preview_item(self, preview_data: PreviewData):
        scaled_pixmap = preview_data.storyboard.scaled(preview_data.duration_in_px, self.TRACK_VIEW_HEIGHT)
        position = QPointF(self._find_last_pos_x(), 0)
        return VideoPreviewItem(scaled_pixmap, self.scene, position, preview_data.clip_metadata)

    def add_preview_item(self, preview_data: PreviewData):
        preview = self.create_preview_item(preview_data)
        self.scene.addItem(preview)
        self.update_scene_rect()

    @pyqtSlot(PreviewData)
    def on_storyboard_ready(self, preview_data: PreviewData):
        self.add_preview_item(preview_data)
        self.pending_previews -= 1
        if self.pending_previews == 0:
            self.resizing_completed.emit()

    @pyqtSlot(str)
    def on_storyboard_error(self, error: str):
        print(error)
        self.pending_previews -= 1

    def run_storyboard_creation_worker(self, clip_metadata: ClipMetaData):
        duration_in_px = int(clip_metadata.duration_s * self.pixels_per_second)
        last_frame_width = int(duration_in_px % clip_metadata.scaled_width)  # 675 % 88 = 59
        last_frame_percentage = last_frame_width / clip_metadata.scaled_width  # 0.6704
        worker = StoryboardCreator(clip_metadata, duration_in_px, last_frame_percentage)
        worker.signals.finished.connect(self.on_storyboard_ready)
        worker.signals.error.connect(self.on_storyboard_error)
        self.threadpool.start(worker)

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
        print(self.pixels_per_second)
        self.draw_time_line()
        self.change_preview_size()

    def zoom_out(self):
        zoom_idx = self.ZOOM_VARIANTS.index(self.pixels_per_second)
        if zoom_idx == 0:
            return

        self.pixels_per_second = self.ZOOM_VARIANTS[zoom_idx - 1]
        self.draw_time_line()
        self.change_preview_size()

    @pyqtSlot()
    def sort_after_resizing(self):
        pos_x = self.scene.ITEMS_ROFFSET
        previews_sorted = sorted(self.scene.get_items(),
                                 key=lambda item: self.original_previews_order.index(item.clip_metadata))
        for el in previews_sorted:
            el.setPos(pos_x, 0)
            pos_x += el.boundingRect().width()

        self.update_scene_rect()

    def change_preview_size(self):
        clips_metadata_list = []
        self.original_previews_order = [preview.clip_metadata for preview in self.scene.get_items()]

        for preview in self.scene.get_items():
            clips_metadata_list.append(preview.clip_metadata)
            self.scene.removeItem(preview)

        self.total_previews = len(clips_metadata_list)
        self.pending_previews = self.total_previews

        for clip_metadata in clips_metadata_list:
            self.run_storyboard_creation_worker(clip_metadata)




if __name__ == '__main__':
    pass
