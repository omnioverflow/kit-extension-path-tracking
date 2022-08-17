import omni.ext
import omni.usd

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
        self._ui.teardown()
        self._ui = None
        self._model.teardown()
        self._model = None
        if hasattr(self, '_viewport_ui') and self._viewport_ui is not None:
            self._viewport_ui.teardown()
            self._viewport_ui = None

    # ==========================================================================
    # Callbacks
    # ==========================================================================

    def _on_click_start_scenario(self):
        self._model.load_simulation()    
        omni.timeline.get_timeline_interface().play()

    def _on_click_load_sample_vehicle(self):
        self._model.load_sample_vehicle()        

    def _on_click_load_ground_plane(self):
        self._model.load_ground_plane()

    def _on_click_load_basis_curve(self):
        self._model.load_sample_track()

    def _on_click_attach_selected(self):
        selected = omni.usd.get_context().get_selection().get_selected_prim_paths()
        self._model.attach_vehicle_to_curve(selected)
    
    def _on_click_clear_attachments(self):
        self._model.clear_attachments()

    def _on_click_recompute_trajectories(self):
        self._model.recompute_trajectories()

    def _on_click_load_preset_scene(self):
        self._model.load_ground_plane()
        self._model.load_sample_vehicle()
        self._model.load_sample_track()
        self._model.attach_vehicle_to_curve(self._model.attachment_presets())

    def _changed_enable_debug(self, model):
        self._model.set_enable_debug(model.as_bool)