#!/usr/bin/env python3
import itertools
import math

from gi.repository import GLib, Clutter
import cairo
import pandas as pd
from svg_model.data_frame import (get_svg_frame, close_paths, get_path_infos,
                                  get_bounding_box)


try:
    profile
except NameError:
    profile = lambda f: f


def scale_to_fit_a_in_b(a_shape, b_shape):
    # Normalize the shapes to allow comparison.
    a_shape_normal = a_shape / a_shape.max()
    b_shape_normal = b_shape / b_shape.max()

    if a_shape_normal.width > b_shape_normal.width:
        a_shape_normal *= b_shape_normal.width / a_shape_normal.width

    if a_shape_normal.height > b_shape_normal.height:
        a_shape_normal *= b_shape_normal.height / a_shape_normal.height

    return a_shape_normal.max() * b_shape.max() / a_shape.max()


class SvgActor(Clutter.Actor):
  @profile
  def __init__(self, svg_path):
    super(SvgActor, self).__init__()
    self.df_device = close_paths(get_svg_frame(svg_path))

    self.bbox = get_bounding_box(self.df_device)
    self.df_paths = get_path_infos(self.df_device)
    self.idle_resize_id = 0

    self.colors = {
      'white' : Clutter.Color.new(255, 255, 255, 255),
      'blue' : Clutter.Color.new(16, 16, 32, 255),
      'black' : Clutter.Color.new(0, 0, 0, 128),
      'hand' : Clutter.Color.new(16, 32, 16, 196)
    }

    # our 2D canvas, courtesy of Cairo
    canvas = Clutter.Canvas.new()
    canvas.set_size(*self.bbox[['width', 'height']])

    self.set_content(canvas)
    self.set_content_scaling_filters(Clutter.ScalingFilter.TRILINEAR,
                                     Clutter.ScalingFilter.LINEAR)

    # resize the canvas whenever the actor changes size
    self.connect("allocation-changed", self.on_actor_resize)

    # connect our drawing code
    canvas.connect("draw", self.on_draw)

    # invalidate the canvas, so that we can draw before the main loop starts
    self.idle_invalidate(canvas)

  @profile
  def on_draw(self, canvas, cr, width, height):
    canvas_shape = pd.Series([width, height], index=['width', 'height'])
    actor_scale = .9 * scale_to_fit_a_in_b(self.bbox[['width', 'height']],
                                           canvas_shape)

    cr.save()
    # clear the contents of the canvas, to avoid painting
    # over the previous frame
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.paint()
    cr.restore()
    cr.set_operator(cairo.OPERATOR_OVER)

    # Center drawing in canvas
    cr.translate(*(.5 * canvas_shape))
    # scale the modelview to the size of the surface
    cr.scale(actor_scale, actor_scale)

    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(0.1)

    for ((path_id, df_i),
         (path_id_j, info_i)) in itertools.izip(self.df_device
                                                .groupby('path_id'),
                                                self.df_paths.iterrows()):
        cr.move_to(*df_i.iloc[0][['x', 'y']])
        for vertex_i, (x, y) in df_i[['x', 'y']].iterrows():
            cr.line_to(x, y)
        Clutter.cairo_set_source_color(cr, self.colors['black'])
        cr.stroke_preserve()
        Clutter.cairo_set_source_color(cr, self.colors['white'])
        cr.fill()

    # we're done drawing
    return True

  def idle_invalidate(self, canvas=None):
    if canvas is None:
        canvas = self.get_content()
    canvas.invalidate()
    return GLib.SOURCE_CONTINUE

  @profile
  def idle_resize(self):
    width, height = self.get_size()

    # Match the canvas size to the actor's
    canvas = self.get_content()
    canvas.set_size(math.ceil(width), math.ceil(height))

    # unset the guard
    self.idle_resize_id = 0

    # remove the timeout
    return GLib.SOURCE_REMOVE

  def on_actor_resize(self, actor, allocation, flags):
    # Throttle multiple actor allocations to one canvas resize we use a guard
    # variable to avoid queueing multiple resize operations.
    if self.idle_resize_id == 0:
      self.idle_resize_id = Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                                     self.idle_resize)


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    import sys
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv[1:]

    parser = ArgumentParser(description='Demonstrate SVG drawn to '
                            'Clutter.Canvas')
    parser.add_argument('svg_path')

    args = parser.parse_args(args)
    return args


if __name__ == '__main__':
    def on_destroy(stage):
        Clutter.main_quit()

    args = parse_args()

    Clutter.init([])
    actor = SvgActor(args.svg_path)

    # create a resizable stage
    stage = Clutter.Stage.new()
    stage.set_title("SVG to cairo")
    stage.set_user_resizable(True)
    stage.set_background_color(actor.colors['blue'])
    stage.set_size(480, 270)
    stage.show()
    stage.add_child(actor)
    # quit on destroy
    stage.connect("destroy", on_destroy)

    ## bind the size of the actor to that of the stage
    actor.add_constraint(Clutter.BindConstraint
                         .new(stage, Clutter.BindCoordinate.SIZE, 0))
    actor.set_opacity(.5 * 255)
    Clutter.main()
