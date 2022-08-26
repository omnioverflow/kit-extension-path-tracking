import omni.ext
import omni.kit
import omni.usd
import carb
from pxr import Tf, Usd

import asyncio

from .model import ExtensionModel
from .ui import *

# ==============================================================================
# 
# PathTrackingExtension
# 
# ==============================================================================
class PathTrackingExtension(omni.ext.IExt):

    def __init__(self):
        self._DEFAULT_LOOKAHEAD = 400.0
        # Any user-defined changes to the lookahead parameter will be clamped:
        self._MIN_LOOKAHEAD = 250.0
        self._MAX_LOOKAHEAD = 1000.0

    def on_startup(self, ext_id):
        if omni.usd.get_context().get_stage() is None:
            # Workaround for running within test environment.
            omni.usd.get_context().new_stage()

        # Usd listener could be used in the future if we could be interested 
        # in recomputing changes in the vehicle planned trajectory "on the fly".
        # self._usd_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_change, None)

        self._stage_event_sub = omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(
            self._on_stage_event, name="Stage Open/Closing Listening"
        )

        self._model = ExtensionModel(
            ext_id, 
            default_lookahead_distance=self._DEFAULT_LOOKAHEAD,
            max_lookahed_distance=self._MAX_LOOKAHEAD,
            min_lookahed_distance=self._MIN_LOOKAHEAD
        )
        self._ui = ExtensionUI(self)
        self._ui.build_ui(self._model.get_lookahead_distance(), attachments=[])

    def on_shutdown(self):
        timeline = omni.timeline.get_timeline_interface()
        if timeline.is_playing():
            timeline.stop()

        self._clear_attachments()

        self._usd_listener = None
        self._stage_event_sub = None

        self._ui.teardown()
        self._ui = None
        self._model.teardown()
        self._model = None

    def _update_ui(self):
        self._ui.update_attachment_info(self._model._vehicle_to_curve_attachments.keys())

    # ==========================================================================
    # Callbacks
    # ==========================================================================

    def _on_click_start_scenario(self):
        async def start_scenario(model):
            timeline = omni.timeline.get_timeline_interface()
            if timeline.is_playing():
                timeline.stop()
                await omni.kit.app.get_app().next_update_async()
            lookahead_distance = self._ui.get_lookahead_distance()
            model.load_simulation(lookahead_distance)
            omni.timeline.get_timeline_interface().play()

        run_loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(start_scenario(self._model), loop=run_loop)

    def _on_click_stop_scenario(self):
        async def stop_scenario():
            timeline = omni.timeline.get_timeline_interface()
            if timeline.is_playing():
                timeline.stop()
                await omni.kit.app.get_app().next_update_async()

        run_loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(stop_scenario(), loop=run_loop)

    def _on_click_load_sample_vehicle(self):
        self._model.load_sample_vehicle()        

    def _on_click_load_ground_plane(self):
        self._model.load_ground_plane()

    def _on_click_load_basis_curve(self):
        self._model.load_sample_track()

    def _on_click_load_forklift(self):
        self._model.load_forklift_rig()

    def _on_click_attach_selected(self):
        selected_prim_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        self._model.attach_selected_prims(selected_prim_paths)
        self._update_ui()
    
    def _clear_attachments(self):
        async def stop_scenario():
            timeline = omni.timeline.get_timeline_interface()
            if timeline.is_playing():
                timeline.stop()
                await omni.kit.app.get_app().next_update_async()

        run_loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(stop_scenario(), loop=run_loop)

        self._model.clear_attachments()
        self._update_ui()

    def _on_click_clear_attachments(self):
        self._clear_attachments()

    def _on_click_load_preset_scene(self):
        self._model.load_preset_scene()
        self._update_ui()

    def _on_stage_event(self, event: carb.events.IEvent):
        """Called on USD Context event"""
        if event.type == int(omni.usd.StageEventType.CLOSING):
            self._model.clear_attachments()
            self._update_ui()

    def _on_usd_change(self, objects_changed, stage):
        carb.log_info(f"_on_usd_change")
        for resync_path in objects_changed.GetResyncedPaths():
            carb.log_info(resync_path)

    def _changed_enable_debug(self, model):
        self._model.set_enable_debug(model.as_bool)

    def _on_lookahead_distance_changed(self, distance):
        # self._clear_attachments()
        clamped_lookahead_distance = self._model.update_lookahead_distance(distance)
        self._ui.set_lookahead_distance(clamped_lookahead_distance)