from pygtk3_helpers.delegates import SlaveView
import pandas as pd
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gdk, GstVideo
from gi.repository import GtkClutter, ClutterGst, Clutter
import cogl_helpers as ch
from opencv_helpers import (get_map_array, find_homography_array,
                            cvwarp_mat_to_4x4)


rand_rgb = lambda: np.concatenate([np.random.randint(255, size=3), [0]])


class View(SlaveView):
    def __init__(self, device=None):
        self.pipeline = None
        self.device = device
        self.texture_shape = pd.Series([-1, -1], index=['width', 'height'])
        super(View, self).__init__()

    def stage_corner_points(self):
        allocation = self.clutter.get_allocation()
        x, y, w, h = [getattr(allocation, k) for k in ['x', 'y', 'width',
                                                       'height']]
        return pd.DataFrame([[0, 0], [w, 0], [w, h], [0, h]],
                            columns=list('xy'))

    def texture_corner_points(self):
        w, h = self.texture.get_size()
        return pd.DataFrame([[0, 0], [w, 0], [w, h], [0, h]],
                            columns=list('xy'))

    def fit_texture_to_stage(self):
        stage_corners = self.stage_corner_points()
        texture_corners = self.texture_corner_points()
        homography_arr = find_homography_array(texture_corners.values,
                                               stage_corners.values)
        warp_arr = cvwarp_mat_to_4x4(homography_arr)
        self.texture.set_transform(ch.from_array(warp_arr))
        self.texture_corners = self.texture_corner_points()
        self.view_corners = self.stage_corner_points()

    def create_ui(self):
        Clutter.init()
        Clutter.threads_init()

        self.clutter = GtkClutter.Embed()
        self.clutter.set_size_request(420, 280)

        self.stage = self.clutter.get_stage()
        self.texture = Clutter.Texture.new()
        self.texture.connect('allocation-changed', self.on_size_change)

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
        self.sink.set_property('qos', True)

        # Add elements to the pipeline
        self.pipeline.add(self.src)
        self.pipeline.add(self.sink)

        self.src.link_filtered(self.sink,
                               Gst.Caps.from_string('video/x-raw, '
                                                    'format=(string)I420'))

        self.stage.set_color(Clutter.Color.new(1, 0, 0, 0))
        self.stage.add_actor(self.texture)
        self.stage.show_all()

        self.widget.add(self.clutter)

        self.clutter.connect('configure-event', self.on_configure_event)

    def on_size_change(self, texture, width, height):
        self.texture_shape = pd.Series([width, height],
                                       index=['width', 'height'])
        self.view_corners = self.stage_corner_points()
        self.texture_corners = pd.DataFrame([[0, 0], [width, 0],
                                             [width, height], [0, height]],
                                            columns=list('xy'))
        GObject.idle_add(self.fit_texture_to_stage)

    def on_configure_event(self, widget, event):
        if all(map(lambda x: x >= 0, (event.x, event.y, event.width,
                                      event.height))):
            self.fit_texture_to_stage()

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
        self._press_index = self.nearest_point_index(self._press_coords)
        ok, x, y = self.texture.transform_stage_point(*self._press_coords)
        if not ok:
            raise ValueError('Error translating point.')
        self.texture_corners.iloc[self._press_index] = x, y
        self.view_corners.iloc[self._press_index] = event.x, event.y

    def on_button_release(self, actor, event):
        if getattr(self, '_button_down', False):
            self._release_coords = pd.Series([event.x, event.y],
                                             index=['x', 'y'])
            self._button_down = False

    def nearest_point_index(self, p):
        return (self.view_corners - p).abs().sum(axis=1).argmin()

    def on_mouse_move(self, actor, event):
        if getattr(self, '_button_down', False):
            if not int(event.modifier_state & Clutter.ModifierType.BUTTON1_MASK):
                # Button was pressed, but is no longer pressed (e.g., released
                # while outside of stage).
                self.on_button_release(self.texture, self._exit_coords)
            self.view_corners.iloc[self._press_index] = event.x, event.y
            self.update_transform()

    def update_transform(self):
        homography_arr = find_homography_array(self.texture_corners.values,
                                               self.view_corners.values)
        transform_arr = cvwarp_mat_to_4x4(homography_arr)
        self.texture.set_transform(ch.from_array(transform_arr))

    def rotate(self, shift):
        '''
        Rotate 90 degrees clockwise `shift` times.  If `shift` is negative,
        rotate counter-clockwise.
        '''
        self.texture_corners.values[:] = np.roll(self.texture_corners
                                                 .values, shift, axis=0)
        self.update_transform()

    def flip_horizontal(self):
        corners = self.texture_corners.values.copy()
        self.texture_corners.values[:2] = np.roll(corners[:2], 1, axis=0)
        self.texture_corners.values[2:] = np.roll(corners[2:], 1, axis=0)
        self.update_transform()

    def flip_vertical(self):
        corners = self.texture_corners.values.copy()
        self.texture_corners.values[[0, -1]] = corners[[-1, 0]]
        self.texture_corners.values[1:3] = np.roll(corners[1:3], 1, axis=0)
        self.update_transform()

    def get_texture_vertices(self):
        return pd.DataFrame([[v.x, v.y] for v in
                             self.texture.get_abs_allocation_vertices()],
                            columns=['x', 'y'])
