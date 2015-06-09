from gi.repository import GObject, GtkClutter, Clutter, GLib, Gtk
from pygtk3_helpers.delegates import SlaveView
from webcam_recorder.caps import get_device_configs
from webcam_recorder.video_view import RecordControl
from .pipeline import PipelineActor
from .warp import WarpActor
from .warp_control import WarpControl
from .pipeline_manager import PipelineManager


class ClutterView(SlaveView):
    def create_ui(self):
        Clutter.init()
        Clutter.threads_init()

        self.clutter = GtkClutter.Embed()
        self.clutter.set_size_request(420, 280)

        self.stage = self.clutter.get_stage()
        self.stage.set_background_color(Clutter.Color
                                        .from_string('#8c8c8c')[1])
        self.stage.show_all()

        self.widget.add(self.clutter)


class RecordView(SlaveView):
    def __init__(self, device_configs=None):
        super(RecordView, self).__init__()
        if device_configs is None:
            self.device_configs = get_device_configs()
            self.device_configs = self.device_configs[(self.device_configs
                                                       .format == 'I420')
                                                      & (self.device_configs
                                                         .framerate > 10)]
        else:
            self.device_configs = device_configs
        self.pipeline_manager = PipelineManager()
        self.config_requested = None
        self.record_path = None
        self.pipeline_actor = None
        self.video_view = None

    def add_pipeline_actor(self):
        actor = PipelineActor()
        self.warp_actor = WarpActor(actor)
        actor.connect('allocation-changed', lambda *args:
                      self.warp_actor.fit_child_to_parent())
        self.video_view.stage.add_actor(self.warp_actor)
        self.warp_actor.add_constraint(Clutter.BindConstraint
                                       .new(self.video_view.stage,
                                            Clutter.BindCoordinate.SIZE, 0))
        self.pipeline_actor = actor

    def create_ui(self):
        self.record_control = RecordControl()
        self.video_view = ClutterView()
        self.video_view.show()
        self.add_pipeline_actor()
        self.warp_control = WarpControl(self.warp_actor)
        for slave in (self.record_control, self.warp_control, self.video_view):
            slave.show()
            self.add_slave(slave)
        self.record_control.on_changed = self.on_options_changed

        for slave in (self.record_control, self.warp_control):
            # Do not expand record or warp rows.
            self.widget.set_child_packing(slave.widget, False, False, 0,
                                          Gtk.PackType.START)

        Clutter.threads_add_timeout(GLib.PRIORITY_DEFAULT, 1000,
                                    self.refresh_config)

    def on_options_changed(self, config, record_path):
        self.config_requested = config
        self.record_path = record_path

    def refresh_config(self):
        '''
        __NB__ This *must* be called from a *different* thread than the GUI/Gtk thread.
        '''
        from gi.repository import Clutter, Gst, GstVideo, ClutterGst
        from path_helpers import path
        from .warp import bounding_box_from_allocation

        if self.config_requested is not None:
            sink = ClutterGst.VideoSink.new(self.pipeline_actor.texture)
            sink.set_property('sync', True)
            sink.set_property('qos', True)

            if self.record_path is not None:
                record_path = path(self.record_path)
                warp_path = record_path.parent.joinpath(record_path.namebase +
                                                        '.h5')
                # Parent allocation
                parent_bbox = \
                    bounding_box_from_allocation(self.warp_actor
                                                 .get_allocation_geometry())
                # Child allocation
                child_bbox = \
                    bounding_box_from_allocation(self.warp_actor.actor
                                                 .get_allocation_geometry())
                common_settings = dict(format='table', data_columns=True,
                                       complib='zlib', complevel=6)
                parent_bbox.to_hdf(str(warp_path), '/shape/parent',
                                   **common_settings)
                child_bbox.to_hdf(str(warp_path), '/shape/child',
                                  **common_settings)
                self.warp_actor.parent_corners.to_hdf(str(warp_path),
                                                      '/corners/parent',
                                                      **common_settings)
                self.warp_actor.child_corners.to_hdf(str(warp_path),
                                                     '/corners/child',
                                                     **common_settings)
            self.pipeline_manager.set_config(self.config_requested,
                                             record_path=self.record_path,
                                             sink=sink)
            self.config_requested = None
        return True
