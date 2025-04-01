from .options.options import DEBUG


class DebugWidgetsManager:
    def __init__(self):
        self.debug_widgets = []

    def register_widget(self, widget):
        self.debug_widgets.append(widget)
        if not DEBUG:
            widget.setVisible(False)

    def register_signal(self, signal, slot):
        if DEBUG:
            signal.connect(slot)


debug_manager = DebugWidgetsManager()