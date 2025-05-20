from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem

from src.schemas import ClipMetaData
if TYPE_CHECKING:
    from src.preview_components import Scene


class VideoPreviewItem(QGraphicsPixmapItem):
    DEFAULT_Z_VALUE = 0
    SELECTED_Z_VALUE = 1

    def __init__(self, pixmap: QPixmap, scene: "Scene", init_pos: QPointF, clip_metadata: ClipMetaData):
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
