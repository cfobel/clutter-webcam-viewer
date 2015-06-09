import pandas as pd
import numpy as np
from gi.repository import Clutter, GLib
from opencv_helpers import find_homography_array, cvwarp_mat_to_4x4
import cogl_helpers as ch


def bounding_box_from_allocation(allocation):
    attrs = 'x', 'y', 'width', 'height'
    return pd.Series([getattr(allocation, k) for k in attrs],
                     index=list(attrs), name='bounding_box')


def corners_from_bounding_box(bbox):
    corners = pd.DataFrame([[0, 0], [bbox.width, 0], [bbox.width, bbox.height],
                            [0, bbox.height]], columns=list('xy'))
    return corners + bbox[['x', 'y']].values


class WarpActor(Clutter.Group):
    def __init__(self, actor):
        super(WarpActor, self).__init__()
        self.add_actor(actor)
        self.actor = actor
        self.actor.set_reactive(True)
        self.connect("allocation-changed", self.on_allocation_changed, actor)
        self.connect('enter-event', self.on_enter)
        self.connect('leave-event', self.on_exit)
        self.actor.connect('button-press-event', self.on_button_press)
        self.actor.connect('button-release-event', self.on_button_release)
        self.actor.connect('motion-event', self.on_mouse_move)
        self._enter_coords = None
        self._exit_coords = None
        self.parent_corners = None
        self.child_corners = None

    def on_allocation_changed(self, warp_actor, allocation, flags, actor):
        bbox = bounding_box_from_allocation(self.actor
                                            .get_allocation_geometry())
        if (bbox[['width', 'height']] > 0).all():
            Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                     self.fit_child_to_parent)

    def warp_actor_corner_points(self):
        bbox = bounding_box_from_allocation(self.get_allocation_geometry())
        return corners_from_bounding_box(bbox)

    def actor_corner_points(self):
        bbox = bounding_box_from_allocation(self.actor
                                            .get_allocation_geometry())
        return corners_from_bounding_box(bbox)

    def fit_child_to_parent(self):
        parent_corners = self.warp_actor_corner_points()
        child_corners = self.actor_corner_points()
        homography_arr = find_homography_array(child_corners.values,
                                               parent_corners.values)
        warp_arr = cvwarp_mat_to_4x4(homography_arr)
        self.actor.set_transform(ch.from_array(warp_arr))
        self.parent_corners = self.warp_actor_corner_points()
        self.child_corners = self.actor_corner_points()

    def on_enter(self, actor, event):
        self._in_bounds = True
        self._enter_coords = pd.Series([event.x, event.y], index=['x', 'y'])

    def on_exit(self, actor, event):
        self._in_bounds = False
        self._exit_coords = pd.Series([event.x, event.y], index=['x', 'y'])

    def on_button_press(self, actor, event):
        self._press_coords = pd.Series([event.x, event.y], index=['x', 'y'])
        self._button_down = True
        self._press_translate = pd.Series(self.actor.get_translation()[:2],
                                          index=['x', 'y'])
        self._press_index = self.nearest_point_index(self._press_coords)
        ok, x, y = self.actor.transform_stage_point(*self._press_coords)
        if not ok:
            raise ValueError('Error translating point.')
        self.child_corners.iloc[self._press_index] = x, y
        self.parent_corners.iloc[self._press_index] = event.x, event.y

    def on_button_release(self, actor, event):
        if getattr(self, '_button_down', False):
            self._release_coords = pd.Series([event.x, event.y],
                                             index=['x', 'y'])
            self._button_down = False

    def nearest_point_index(self, p):
        return (self.parent_corners - p).abs().sum(axis=1).argmin()

    def on_mouse_move(self, actor, event):
        if getattr(self, '_button_down', False):
            if self._exit_coords is not None and not int(event.modifier_state &
                                                         Clutter.ModifierType
                                                         .BUTTON1_MASK):
                # Button was pressed, but is no longer pressed (e.g., released
                # while outside of stage).
                self.on_button_release(self.actor, self._exit_coords)
            self.parent_corners.iloc[self._press_index] = event.x, event.y
            self.update_transform()

    def update_transform(self):
        homography_arr = find_homography_array(self.child_corners.values,
                                               self.parent_corners.values)
        transform_arr = cvwarp_mat_to_4x4(homography_arr)
        self.actor.set_transform(ch.from_array(transform_arr))

    def rotate(self, shift):
        '''
        Rotate 90 degrees clockwise `shift` times.  If `shift` is negative,
        rotate counter-clockwise.
        '''
        self.child_corners.values[:] = np.roll(self.child_corners
                                                 .values, shift, axis=0)
        self.update_transform()

    def flip_horizontal(self):
        corners = self.child_corners.values.copy()
        self.child_corners.values[:2] = np.roll(corners[:2], 1, axis=0)
        self.child_corners.values[2:] = np.roll(corners[2:], 1, axis=0)
        self.update_transform()

    def flip_vertical(self):
        corners = self.child_corners.values.copy()
        self.child_corners.values[[0, -1]] = corners[[-1, 0]]
        self.child_corners.values[1:3] = np.roll(corners[1:3], 1, axis=0)
        self.update_transform()

    def get_actor_vertices(self):
        return pd.DataFrame([[v.x, v.y] for v in
                             self.actor.get_abs_allocation_vertices()],
                            columns=['x', 'y'])

    def save(self, warp_path):
        # Parent allocation
        parent_bbox = \
            bounding_box_from_allocation(self.get_allocation_geometry())
        # Child allocation
        child_bbox = \
            bounding_box_from_allocation(self.actor.get_allocation_geometry())
        common_settings = dict(format='table', data_columns=True,
                               complib='zlib', complevel=6)
        parent_bbox.to_hdf(str(warp_path), '/shape/parent', **common_settings)
        child_bbox.to_hdf(str(warp_path), '/shape/child', **common_settings)
        self.parent_corners.to_hdf(str(warp_path), '/corners/parent',
                                   **common_settings)
        self.child_corners.to_hdf(str(warp_path), '/corners/child',
                                  **common_settings)

    def load(self, warp_path):
        warp_path = str(warp_path)
        try:
            parent_corners = pd.read_hdf(warp_path, '/corners/parent')
            child_corners = pd.read_hdf(warp_path, '/corners/child')
            self.parent_corners[:] = parent_corners
            self.child_corners[:] = child_corners
        except Exception:
            pass
        else:
            Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                     self.update_transform)

    def reset(self):
        self._button_down = False
        self.fit_child_to_parent()
