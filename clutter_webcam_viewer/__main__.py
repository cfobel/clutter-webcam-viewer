import time
from threading import Thread

from gi.repository import GObject, Gst, Gdk, GstVideo
from gi.repository import GtkClutter, ClutterGst, Clutter

from . import View


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""
    import sys
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Demonstrate Clutter GStreamer')
    parser.add_argument('-d', '--device', default=None)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    '''
    Demonstrate drag'n'drop webcam feed using Clutter stage.
    '''
    args = parse_args()
    GObject.threads_init()
    Gst.init(None)

    view = View(args.device)
    gui_thread = Thread(target=view.show_and_run)
    gui_thread.daemon = True
    gui_thread.start()

    while view.pipeline is None:
        time.sleep(.1)

    view.pipeline.set_state(Gst.State.PLAYING)

    view.texture.connect('button-press-event', view.on_button_press)
    view.texture.connect('button-release-event', view.on_button_release)
    view.texture.connect('button-release-event', view.change_bg)
    view.texture.connect('motion-event', view.on_mouse_move)
    view.stage.connect('enter-event', view.on_enter)
    view.stage.connect('leave-event', view.on_exit)

    raw_input()
