from gi.repository import Clutter, GLib
from svg_model.data_frame import (close_paths, get_path_infos,
                                  get_bounding_box)
from .svg import PathActor, aspect_fit, SvgGroup
import zmq
import pandas as pd


class DmfDevice(object):
    def __init__(self, uri):
        self.uri = uri
        self.ctx = zmq.Context.instance()
        self.ports = self._command('ports')
        self.electrode_channels = self._command('electrode_channels')
        self.df_svg = self._command('device_svg_frame')
        self.sync_states()

        self.sub = zmq.Socket(self.ctx, zmq.SUB)
        self.sub.connect('tcp://localhost:%s' % self.ports.pub)
        self.sub.setsockopt(zmq.SUBSCRIBE, '')

    def toggle_channels(self, channels):
        self.channel_states[channels] = ~self.channel_states[channels]

    def sync_states(self):
        channel_states = self._command('sync')
        self.channel_states = pd.Series(channel_states, dtype=bool)
        self.channel_states.index.name = 'channel'

    def _command(self, cmd):
        req = zmq.Socket(self.ctx, zmq.REQ)
        req.connect(self.uri)
        req.send_pyobj({'command': cmd})

        while not req.poll(50):
            pass

        response = req.recv_pyobj()
        return response['result']

    def push_channel_states(self):
        ctx = zmq.Context.instance()
        push = zmq.Socket(ctx, zmq.PUSH)
        push.connect('tcp://localhost:%s' % self.ports.pull)
        push.send_pyobj(self.channel_states)

    def spin(self, timeout=zmq.NOBLOCK):
        updated = False
        while self.sub.poll(timeout):
            updated = True
            diff_states = self.sub.recv_pyobj()
            self.channel_states[diff_states.index] = diff_states
            if not timeout == zmq.NOBLOCK:
                break
        return updated


class DmfActor(Clutter.Group):
    def __init__(self, uri):
        super(DmfActor, self).__init__()
        self.device = DmfDevice(uri)

        self.df_device = close_paths(self.device.df_svg)
        self.bbox = get_bounding_box(self.df_device)
        self.df_paths = get_path_infos(self.df_device)

        for path_id, df_i in self.df_device.groupby('path_id'):
            actor = PathActor(path_id, df_i)
            actor.set_size(self.bbox.width, self.bbox.height)
            actor.color = '#000000'
            actor.connect("button-release-event", self.clicked_cb)
            self.add_actor(actor)
        self.connect("allocation-changed", aspect_fit, self.bbox)
        Clutter.threads_add_idle(GLib.PRIORITY_DEFAULT, self.update_ui)
        Clutter.threads_add_timeout(GLib.PRIORITY_DEFAULT, 100,
                                    self.refresh_channels)

    def refresh_channels(self, timeout=zmq.NOBLOCK):
        if self.device.spin(timeout):
            self.update_ui()
        return True

    def update_ui(self):
        for p in self.get_children():
            channels = self.device.electrode_channels.ix[p.path_id]
            actuated = self.device.channel_states[channels].any()
            p.color = '#FFFFFF' if actuated else '#000000'

    def clicked_cb(self, actor, event):
        channels = self.device.electrode_channels.ix[actor.path_id]
        self.device.toggle_channels(channels)
        self.update_ui()
        self.device.push_channel_states()
