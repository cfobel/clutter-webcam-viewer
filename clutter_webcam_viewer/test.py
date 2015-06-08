import time
from threading import Thread

from gi.repository import GtkClutter, Clutter, GLib, Gst
from pygtk3_helpers.delegates import SlaveView
from .svg import SvgGroup
from .pipeline import PipelineActor
from .warp import WarpActor


class ClutterView(SlaveView):
    def create_ui(self):
        Clutter.init()
        Clutter.threads_init()

        self.clutter = GtkClutter.Embed()
        self.clutter.set_size_request(420, 280)

        self.stage = self.clutter.get_stage()
        self.stage.color = '#ffffff'
        self.stage.show_all()

        self.widget.add(self.clutter)


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    import sys
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Demonstrate GTK3 Clutter')
    parser.add_argument('-s', '--svg-path', default=None)
    parser.add_argument('-d', '--video-device', default=None)
    parser.add_argument('-u', '--dmf-device-uri')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    '''
    Demonstrate drag'n'drop webcam feed using Clutter stage.
    '''
    args = parse_args()

    Gst.init()
    view = ClutterView()
    gui_thread = Thread(target=view.show_and_run)
    gui_thread.daemon = True
    gui_thread.start()

    def add_svg(view, svg_path):
        actor = SvgGroup.from_path(svg_path)
        warp_actor = WarpActor(actor)
        view.stage.add_actor(warp_actor)
        warp_actor.add_constraint(Clutter.BindConstraint
                                  .new(view.stage, Clutter.BindCoordinate.SIZE,
                                       0))
        warp_actor.set_opacity(.5 * 255)

    def add_pipeline(view, video_device):
        actor = PipelineActor()
        actor.connect('allocation-changed', lambda *args:
                      warp_actor.fit_child_to_parent())
        actor.pipeline.set_state(Gst.State.PLAYING)
        warp_actor = WarpActor(actor)
        view.stage.add_actor(warp_actor)
        warp_actor.add_constraint(Clutter.BindConstraint
                                  .new(view.stage, Clutter.BindCoordinate.SIZE,
                                       0))

    def add_dmf_device(view, uri):
        from .dmf import DmfActor

        actor = DmfActor(uri)
        view.stage.add_actor(actor)
        actor.add_constraint(Clutter.BindConstraint
                             .new(view.stage, Clutter.BindCoordinate.SIZE, 0))
        actor.set_opacity(.5 * 255)

    if args.video_device is not None:
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, add_pipeline, view,
                                 args.video_device)
    if args.svg_path is not None:
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, add_svg, view,
                                 args.svg_path)
    elif args.dmf_device_uri is not None:
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, add_dmf_device, view,
                                 args.dmf_device_uri)

    raw_input()
