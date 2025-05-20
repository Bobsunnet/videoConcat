from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsTextItem

from src.preview_components.tracks_view import TimelineTickItem


class TimelineRenderer:
    def __init__(self, scene):
        self.scene = scene
        self.grpTicks = QGraphicsItemGroup()
        self.grpLabels = QGraphicsItemGroup()
        self.scene.addItem(self.grpTicks)
        self.scene.addItem(self.grpLabels)

    def draw(self, px_per_sec, timeline_width):
        self.grpLabels.setPos(0, 0)
        self.grpTicks.setPos(0, 0)
        self.draw_ticks(timeline_width)
        self.draw_labels(px_per_sec, timeline_width)
        self.grpLabels.setPos(0, -38)
        self.grpTicks.setPos(0, -38)

    def draw_ticks(self, timeline_width):
        for el in self.grpTicks.childItems():
            self.scene.removeItem(el)

        ticks_step_in_px = 10
        for px in range(0, timeline_width, ticks_step_in_px):
            tick_height = 10
            if px % (5 * tick_height) == 0:
                tick_height = 20

            tick = TimelineTickItem(px + self.scene.ITEMS_ROFFSET, 0, px + self.scene.ITEMS_ROFFSET, tick_height)
            self.grpTicks.addToGroup(tick)

    def draw_labels(self, px_per_sec, timeline_width):
        for el in self.grpLabels.childItems():
            self.scene.removeItem(el)

        label_tick_height = 20
        step_px = 50
        for px in range(step_px, timeline_width, step_px):
            label = QGraphicsTextItem(str(round(px / px_per_sec, 1)))
            label.setPos(px + self.scene.ITEMS_ROFFSET - 10, label_tick_height)
            self.grpLabels.addToGroup(label)
