from pygtk3_helpers.delegates import SlaveView
import pandas as pd
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gdk, GstVideo
from gi.repository import GtkClutter, ClutterGst, Clutter


rand_rgb = lambda: np.concatenate([np.random.randint(255, size=3), [0]])


class View(SlaveView):
    def __init__(self, device=None):
        self.pipeline = None
        self.device = device
        self.texture_shape = pd.Series([-1, -1], index=['width', 'height'])
        super(View, self).__init__()

    def create_ui(self):
        Clutter.init()
        Clutter.threads_init()

        self.clutter = GtkClutter.Embed()
        self.clutter.set_size_request(420, 280)

        self.stage = self.clutter.get_stage()
        self.texture = Clutter.Texture.new()
        self.texture.connect('size-change', self.on_size_change)

        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()

        if self.device is None:
            self.src = Gst.ElementFactory.make('autovideosrc', None)
        else:
            self.src = Gst.ElementFactory.make('v4l2src', 'source')
            self.src.set_property('device', self.device)
        self.sink = ClutterGst.VideoSink.new(self.texture)
        self.sink.set_property('sync', True)

        # Add elements to the pipeline
        self.pipeline.add(self.src)
        self.pipeline.add(self.sink)

        self.src.link_filtered(self.sink,
                               Gst.Caps.from_string('video/x-raw '
                                                    'format=(string)I420'))

        self.stage.set_color(Clutter.Color.new(1, 0, 0, 0))
        self.stage.add_actor(self.texture)
        self.stage.show_all()

        self.widget.add(self.clutter)

        self.clutter.connect('configure-event', self.on_configure_event)

    def on_size_change(self, texture, width, height):
        allocation = self.clutter.get_allocation()
        self.texture_shape = pd.Series([width, height],
                                       index=['width', 'height'])
        self.resize(allocation.width, allocation.height)

    def on_configure_event(self, widget, event):
        if all(map(lambda x: x >= 0, (event.x, event.y, event.width,
                                      event.height))):
            self.resize(event.width, event.height)

    def resize(self, width, height):
        canvas_shape = pd.Series([width, height], index=['width', 'height'])
        if (self.texture_shape > 0).all():
            scale = canvas_shape / self.texture_shape
            texture_scale = self.texture.get_scale()
            if not (scale == texture_scale).all():
                self.texture.set_scale(*(scale * 0.8))

    def change_bg(self, *args):
        self.stage.set_color(Clutter.Color.new(*rand_rgb()))

    def on_enter(self, actor, event):
        self._in_bounds = True
        self._enter_coords = pd.Series([event.x, event.y], index=['x', 'y'])

    def on_exit(self, actor, event):
        self._in_bounds = False
        self._exit_coords = pd.Series([event.x, event.y], index=['x', 'y'])

    def on_button_press(self, actor, event):
        self._press_coords = pd.Series([event.x, event.y], index=['x', 'y'])
        self._button_down = True
        self._press_translate = pd.Series(self.texture.get_translation()[:2],
                                          index=['x', 'y'])

    def on_button_release(self, actor, event):
        if getattr(self, '_button_down', False):
            self._release_coords = pd.Series([event.x, event.y],
                                             index=['x', 'y'])
            self._button_down = False
            translate = (self._release_coords - self._press_coords +
                         self._press_translate)
            self.texture.set_translation(translate.x, translate.y, 0)

    def on_mouse_move(self, actor, event):
        if getattr(self, '_button_down', False):
            if not int(event.modifier_state & Clutter.ModifierType.BUTTON1_MASK):
                # Button was pressed, but is no longer pressed (e.g., released
                # while outside of stage).
                self.on_button_release(self.texture, self._exit_coords)
            self._move_coords = pd.Series([event.x, event.y], index=['x', 'y'])
            translate = (self._move_coords - self._press_coords +
                         self._press_translate)
            self.texture.set_translation(translate.x, translate.y, 0)
