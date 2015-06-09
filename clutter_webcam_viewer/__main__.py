from threading import Thread

from gi.repository import Clutter, GLib, Gst
from .svg import SvgGroup
from . import RecordView


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    import sys
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Demonstrate GTK3 Clutter')
    parser.add_argument('-s', '--svg-path', default=None)
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Run UI in background thread (useful for '
                        'running, e.g., from IPython).')

    args = parser.parse_args()
    return args


def main(args):
    Gst.init()
    record_view = RecordView()

    if args.interactive:
        gui_thread = Thread(target=record_view.show_and_run)
        gui_thread.daemon = True
        gui_thread.start()
    else:
        record_view.show()

    while record_view.video_view is None:
        time.sleep(.1)
        print 'waiting for GUI'

    view = record_view.video_view

    def add_svg(view, svg_path):
        actor = SvgGroup.from_path(svg_path)
        view.stage.add_actor(actor)
        actor.add_constraint(Clutter.BindConstraint
                             .new(view.stage, Clutter.BindCoordinate.SIZE, 0))

    if args.svg_path is not None:
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, add_svg, view,
                                 args.svg_path)

    if args.interactive:
        raw_input()
    else:
        record_view.show_and_run()

    return record_view


if __name__ == '__main__':
    '''
    Demonstrate drag'n'drop webcam feed using Clutter stage.
    '''
    import time

    args = parse_args()
    result = main(args)
