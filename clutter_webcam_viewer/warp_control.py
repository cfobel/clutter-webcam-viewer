from gi.repository import Gtk, Clutter, GLib, GObject
from pygtk3_helpers.delegates import SlaveView
import pygtk3_helpers.ui.dialog as pu


class WarpControl(SlaveView):
    '''
    A slave view containing UI elements (buttons, etc.) for rotating, flipping,
    saving, and loading warp perspective projection settings.
    '''
    def __init__(self, warp_actor):
        super(WarpControl, self).__init__()
        self.warp_actor = warp_actor

    def create_ui(self):
        '''
        Create UI elements and connect signals.
        '''
        box = Gtk.Box()
        rotate_left = Gtk.Button('Rotate left')
        rotate_right = Gtk.Button('Rotate right')
        flip_horizontal = Gtk.Button('Flip horizontal')
        flip_vertical = Gtk.Button('Flip vertical')
        reset = Gtk.Button('Reset')
        load = Gtk.Button('Load...')
        save = Gtk.Button('Save...')

        rotate_left.connect('clicked', lambda *args: self.rotate_left())
        rotate_right.connect('clicked', lambda *args: self.rotate_right())
        flip_horizontal.connect('clicked', lambda *args:
                                self.flip_horizontal())
        flip_vertical.connect('clicked', lambda *args: self.flip_vertical())
        reset.connect('clicked', lambda *args: self.reset())
        load.connect('clicked', lambda *args: GObject.idle_add(self.load))
        save.connect('clicked', lambda *args: GObject.idle_add(self.save))

        for b in (rotate_left, rotate_right, flip_horizontal, flip_vertical,
                  reset, load, save):
            box.pack_start(b, False, False, 0)

        box.show_all()
        self.widget.pack_start(box, False, False, 0)

        if self.warp_actor.parent_corners is None:
            for b in (rotate_left, rotate_right, flip_horizontal,
                      flip_vertical, reset, load, save):
                b.set_sensitive(False)
            def check_init():
                if self.warp_actor.parent_corners is not None:
                    for b in (rotate_left, rotate_right, flip_horizontal,
                              flip_vertical, reset, load, save):
                        b.set_sensitive(True)
                    return False
                return True
            GObject.timeout_add(100, check_init)

    def save(self):
        '''
        Save warp projection settings to HDF file.
        '''
        response = pu.open(title='Save perspective warp', patterns=['*.h5'])
        if response is not None:
            self.warp_actor.save(response)

    def load(self):
        '''
        Load warp projection settings from HDF file.
        '''
        response = pu.open(title='Load perspective warp', patterns=['*.h5'])
        if response is not None:
            self.warp_actor.load(response)

    def rotate_left(self):
        '''
        Rotate projection 90 degrees to the left.
        '''
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.warp_actor.rotate,
                                 -1)

    def rotate_right(self):
        '''
        Rotate projection 90 degrees to the right.
        '''
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.warp_actor.rotate,
                                 1)

    def flip_horizontal(self):
        '''
        Flip the projection horizontally.
        '''
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                 self.warp_actor.flip_horizontal)

    def flip_vertical(self):
        '''
        Flip the projection vertically.
        '''
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT,
                                 self.warp_actor.flip_vertical)

    def reset(self):
        '''
        Reset the warp projection.
        '''
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.warp_actor.reset)
