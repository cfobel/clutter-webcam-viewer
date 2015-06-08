from gi.repository import Gtk, Clutter, GLib
from pygtk3_helpers.delegates import SlaveView


class WarpControl(SlaveView):
    def __init__(self, warp_actor):
        super(WarpControl, self).__init__()
        self.warp_actor = warp_actor

    def create_ui(self):
        box = Gtk.Box()
        rotate_left = Gtk.Button('Rotate left')
        rotate_right = Gtk.Button('Rotate right')
        flip_horizontal = Gtk.Button('Flip horizontal')
        flip_vertical = Gtk.Button('Flip vertical')
        load = Gtk.Button('Load...')
        save = Gtk.Button('Save...')

        rotate_left.connect('clicked', lambda *args: self.rotate_left())
        rotate_right.connect('clicked', lambda *args: self.rotate_right())
        flip_horizontal.connect('clicked', lambda *args:
                                self.flip_horizontal())
        flip_vertical.connect('clicked', lambda *args: self.flip_vertical())

        for b in (rotate_left, rotate_right, flip_horizontal, flip_vertical,
                  load, save):
            box.pack_start(b, False, False, 0)

        box.show_all()
        self.widget.pack_start(box, False, False, 0)

    def rotate_left(self):
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.warp_actor.rotate,
                                 -1)

    def rotate_right(self):
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.warp_actor.rotate,
                                 1)

    def flip_horizontal(self):
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                 self.warp_actor.flip_horizontal)

    def flip_vertical(self):
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                 self.warp_actor.flip_vertical)
