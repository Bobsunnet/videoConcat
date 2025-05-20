from PyQt6.QtCore import QPointF, QThreadPool, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import (QPushButton, QWidget, QHBoxLayout,
                             QVBoxLayout)

from src import debug_manager
from src.UI.color import ColorOptions
from src.preview_components import TimelineRenderer, Scene
from src.schemas import ClipMetaData, PreviewData
from src.preview_components import TracksView
from src.preview_components import VideoPreviewItem
from src.workers import PreviewWorkersManager


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
        self.timeline_renderer = TimelineRenderer(self.scene)
        self.workers_manager = PreviewWorkersManager()

        self.pixels_per_second = self.ZOOM_VARIANTS[4]  # frames per sec = 10[px/sec] / 70 [px] =0.1428 frames per sec
        self.scene.selectionChanged.connect(self.on_selection_changed)

        self.init_scene_mock()
        self.init_ui()

    def init_ui(self):
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

        self.timeline_renderer.draw(self.pixels_per_second, self._calc_timeline_width())

    def debug_pressed(self, value=None):
        print(self.scene.get_items())

    def debug_action(self, *args):
        print('SIGNAL EMITTED')

    @pyqtSlot()
    def on_remove_selected(self):
        items = self.scene.selectedItems()
        if items:
            selected_item = items[0]
            self.scene.removeItem(selected_item)
            # self.scene.remove_field_gaps()
            self.item_removed.emit(selected_item.clip_metadata)

        self.update_scene_rect()

    @pyqtSlot()
    def on_selection_changed(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            self.item_selected.emit(selected_items[0].clip_metadata)

    def init_scene_mock(self):
        if debug_manager.debug_is_on:
            for i, file_path in enumerate(['D:/PythonProjects/videoConcat/video/vid_sample.avi',
                                           'D:/PythonProjects/videoConcat/video/video_v1.mp4', ]):
                self.call_analysis_worker(file_path)

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

    @pyqtSlot(ClipMetaData)
    def on_analysis_ready(self, clip_metadata: ClipMetaData):
        self.workers_manager.run_storyboard_creation_worker(clip_metadata,
                                                            self.pixels_per_second,
                                                            self.on_storyboard_ready,
                                                            self.on_storyboard_error)

    @pyqtSlot(str)
    def on_analysis_error(self, error: str):
        print(error)

    def call_analysis_worker(self, file_path: str):
        self.workers_manager.run_video_analysis_worker(file_path,
                                                       self.TRACK_VIEW_HEIGHT,
                                                       self.on_analysis_ready,
                                                       self.on_analysis_error)

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

    def _calc_timeline_width(self) -> int:
        width = self.scene.sceneRect().width()
        return int(width if width > 100 * self.pixels_per_second else 100 * self.pixels_per_second)

    def zoom_in(self):
        zoom_idx = self.ZOOM_VARIANTS.index(self.pixels_per_second)
        if zoom_idx == len(self.ZOOM_VARIANTS) - 1:
            return

        self.pixels_per_second = self.ZOOM_VARIANTS[zoom_idx + 1]
        print(self.pixels_per_second)
        self.timeline_renderer.draw(self.pixels_per_second, self._calc_timeline_width())
        self.change_preview_size()

    def zoom_out(self):
        zoom_idx = self.ZOOM_VARIANTS.index(self.pixels_per_second)
        if zoom_idx == 0:
            return

        self.pixels_per_second = self.ZOOM_VARIANTS[zoom_idx - 1]
        self.timeline_renderer.draw(self.pixels_per_second, self._calc_timeline_width())
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
            self.workers_manager.run_storyboard_creation_worker(clip_metadata,
                                                                self.pixels_per_second,
                                                                self.on_storyboard_ready,
                                                                self.on_storyboard_error)


if __name__ == '__main__':
    pass
