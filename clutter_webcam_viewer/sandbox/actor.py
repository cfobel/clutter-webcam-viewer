import sys
import itertools

from gi.repository import Clutter, Cogl
import pandas as pd
from svg_model.data_frame import (get_svg_frame, close_paths, get_path_infos,
                                  get_bounding_box)


class PathActor(Clutter.Actor):
    def __init__(self, path_id, df_path):
        super(PathActor, self).__init__()

        self.set_reactive(True)
        self.path_id = path_id
        self.df_path = df_path[['x', 'y']].copy()

        # set default color to black
        self.color = '#000'
        self.shape = pd.Series([0, 0], index=['width', 'height'])

    def do_allocate(self, box, flags):
        self.shape = pd.Series(box.get_size(), index=['width', 'height'],
                               name='shape')
        self.x, self.y = self.df_path.T.values
        Clutter.Actor.do_allocate(self, box, flags)

    def do_paint(self):
        ok, color = Clutter.Color.from_string(self.color)

        tmp_alpha = self.get_paint_opacity() * color.alpha / 255

        Cogl.Path.new()
        Cogl.set_source_color4ub(color.red, color.green, color.blue, tmp_alpha)
        self.draw_path()
        Cogl.Path.stroke()

    def draw_path(self):
        Cogl.Path.move_to(self.x[0], self.y[0])
        for i in xrange(1, len(self.x)):
            x = self.x[i]
            y = self.y[i]
            Cogl.Path.line_to(x, y)

    def do_pick(self, pick_color):
        if not self.should_pick_paint():
            return

        Cogl.Path.new()

        Cogl.set_source_color4ub(pick_color.red, pick_color.green, pick_color.blue, pick_color.alpha)
        self.draw_path()
        Cogl.Path.fill()


def scale_to_fit_a_in_b(a_shape, b_shape):
    # Normalize the shapes to allow comparison.
    a_shape_normal = a_shape / a_shape.max()
    b_shape_normal = b_shape / b_shape.max()

    if a_shape_normal.width > b_shape_normal.width:
        a_shape_normal *= b_shape_normal.width / a_shape_normal.width

    if a_shape_normal.height > b_shape_normal.height:
        a_shape_normal *= b_shape_normal.height / a_shape_normal.height

    return a_shape_normal.max() * b_shape.max() / a_shape.max()


def clicked_cb(self, actor):
    print actor.path_id
    opacity = actor.get_opacity()
    actor.set_opacity(100 if opacity > 100 else 255)


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv[1:]

    parser = ArgumentParser(description='Demonstrate drawing SVG on Clutter '
                            'stage')
    parser.add_argument('shape', nargs='?', default=None)

    args = parser.parse_args(args)
    return args


if __name__ == "__main__":
    args = parse_args()
    print args

    Clutter.init()
    stage = Clutter.Stage()
    if args.shape is not None:
        width, height = map(int, args.shape.split('x'))
        stage.set_size(width, height)

    df_device = close_paths(get_svg_frame('90-pin channel mapping-opt.svg'))

    bbox = get_bounding_box(df_device)

    df_device[['x', 'y']] += .5
    bbox = get_bounding_box(df_device)

    df_paths = get_path_infos(df_device)

    stage.set_title("SVG paths as actors")
    stage.connect("destroy", lambda x: Clutter.main_quit())

    actors = []
    stage_shape = pd.Series(stage.get_allocation_box().get_size(),
                            index=['width', 'height'])
    actor_scale = .9 * scale_to_fit_a_in_b(bbox[['width', 'height']],
                                           stage_shape)

    group = Clutter.Group()
    for ((path_id, df_i),
         (path_id_j, info_i)) in itertools.izip(close_paths(df_device)
                                                .groupby('path_id'),
                                                df_paths.iterrows()):
        actor = PathActor(path_id, df_i)
        actor.set_size(bbox.width, bbox.height)
        actor.color = 'black'
        click_action = Clutter.ClickAction()
        click_action.connect("clicked", clicked_cb)
        actor.add_action(click_action)
        group.add_actor(actor)

    group.set_scale(actor_scale, actor_scale)
    offset = .5 * stage_shape
    group.set_translation(offset.width, offset.height, 0)
    group.set_opacity(100)
    stage.add_actor(group)
    stage.show_all()

    Clutter.main()
