import pandas as pd
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gdk, GstVideo, GLib
from gi.repository import ClutterGst, Clutter
import cogl_helpers as ch
from opencv_helpers import (get_map_array, find_homography_array,
                            cvwarp_mat_to_4x4)


rand_rgb = lambda: np.concatenate([np.random.randint(255, size=3), [0]])


def aspect_fit(actor, allocation, flags, bbox):
    actor_shape = pd.Series(allocation.get_size(), index=['width', 'height'])
    actor_scale = .9 * scale_to_fit_a_in_b(bbox[['width', 'height']],
                                           actor_shape)
    actor.set_scale(actor_scale, actor_scale)
    offset = -actor_scale * bbox[['x', 'y']]
    offset.name = 'offset'
    scaled_shape = actor_scale * bbox[['width', 'height']]
    offset += .5 * (actor_shape - scaled_shape).values
    actor.set_translation(offset.x, offset.y, 0)


class PipelineActor(Clutter.Group):
    def __init__(self, device=None):
        super(PipelineActor, self).__init__()
        self.device = device
        self.texture = Clutter.Texture.new()
        self.texture.connect('size-change', self.on_size_change)
        #self.texture_shape = pd.Series([-1, -1], index=['width', 'height'])
        self.add_actor(self.texture)
        #self.add_constraint(Clutter.BindConstraint
                            #.new(self.texture, Clutter.BindCoordinate.SIZE, 0))

    def on_size_change(self, texture, width, height):
        self.set_size(width, height)
