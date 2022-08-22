import omni.ext
import omni.kit
import omni.usd

import asyncio

from .debug_renderer import *
from .model import ExtensionModel
from .path_tracking import *
from .ui import *

# ==============================================================================
# 
# PathTrackingExtension
# 
# ==============================================================================
class PathTrackingExtension(omni.ext.IExt):

    def on_startup(self, ext_id):
        self._ui = ExtensionUI(self)
        self._ui.build_ui()
        self._model = ExtensionModel(ext_id)

    def on_shutdown(self):
        timeline = omni.timeline.get_timeline_interface()
        if timeline.is_playing():
            timeline.stop()
        self._ui.teardown()
        self._ui = None
        self._model.teardown()
        self._model = None

    # ==========================================================================
    # Callbacks
    # ==========================================================================

    def _on_click_start_scenario(self):
        async def start_scenario(model):
            timeline = omni.timeline.get_timeline_interface()
            if timeline.is_playing():
                timeline.stop()
                await omni.kit.app.get_app().next_update_async()
            model.load_simulation()
            omni.timeline.get_timeline_interface().play()

        run_loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(start_scenario(self._model), loop=run_loop)

    def _on_click_load_sample_vehicle(self):
        self._model.load_sample_vehicle()        

    def _on_click_load_ground_plane(self):
        self._model.load_ground_plane()

    def _on_click_load_basis_curve(self):
        self._model.load_sample_track()

    def _on_click_attach_selected(self):
        selected_prim_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        self._model.attach_selected_prims(selected_prim_paths)
    
    def _on_click_clear_attachments(self):
        self._model.clear_attachments()

    def _on_click_recompute_trajectories(self):
        self._model.recompute_trajectories()

    def _on_click_load_preset_scene(self):
        self._model.load_preset_scene()

    def _changed_enable_debug(self, model):
        self._model.set_enable_debug(model.as_bool)