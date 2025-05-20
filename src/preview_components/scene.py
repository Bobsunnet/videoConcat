from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsScene

from src.preview_components import VideoPreviewItem


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
