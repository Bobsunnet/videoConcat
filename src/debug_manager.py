from .options.options import DEBUG


class DebugWidgetsManager:
    def __init__(self):
        self.debug_widgets = []
        self.debug_is_on = DEBUG

    def register_widget(self, widget):
        self.debug_widgets.append(widget)
        if not self.debug_is_on:
            widget.setVisible(False)

    def register_signal(self, signal, slot):
        if self.debug_is_on:
            signal.connect(slot)


debug_manager = DebugWidgetsManager()