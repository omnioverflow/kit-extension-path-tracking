import omni.ext
import omni.usd
from pxr import Usd, UsdGeom, UsdLux
import re

from .debug_renderer import *
from .path_tracking import *
from .stepper import *
from .trajectory_scenario import TrajectoryScenario
from .ui import *
from .utils import Utils

# ==============================================================================
# 
# ExtensionModel
# 
# ==============================================================================

class ExtensionModel:
    def __init__(self, extension_id):
        self._ext_id = extension_id
        self.METERS_PER_UNIT = 0.01
        UsdGeom.SetStageMetersPerUnit(omni.usd.get_context().get_stage(), self.METERS_PER_UNIT)
        self._vehicle_paths = []
        self._trajectory_paths = []
        self._scenarios = []
        self._scenario_managers = []
        self._enable_debug=False

    def teardown(self):
        for manager in self._scenario_managers:
            manager.stop_scenario()
        self._scenario_managers = []
        self._scenarios = []

    def attach_vehicle_to_curve(self, selected_paths):
        # Currently we expect two prims to be selected:
        # - WizardVehicle
        # - BasisCurve (corresponding curve/trajectory the vehicle must track)
        if len(selected_paths) == 2:
            stage = omni.usd.get_context().get_stage()
            prim0 = stage.GetPrimAtPath(selected_paths[0])
            prim1 = stage.GetPrimAtPath(selected_paths[1])
            if prim0.IsA(UsdGeom.BasisCurves):
                # Fix order of selected prims: WizardVehicle should be first
                prim0, prim1 = prim1, prim0
                selected_paths[0], selected_paths[1] = selected_paths[1], selected_paths[0]
            if prim0.IsA(UsdGeom.Xformable):
                self._vehicle_paths.append(selected_paths[0] + "/Vehicle")
                self._trajectory_paths.append(selected_paths[1])

    def clear_attachments(self):
        self._vehicle_paths.clear()
        self._trajectory_paths.clear()

    def load_simulation(self):
        vehicle_count = len(self._vehicle_paths)
        trajectory_count = len(self._trajectory_paths)
        scenario_count = len(self._scenarios)
        assert(vehicle_count == trajectory_count)

        if scenario_count < vehicle_count:
            for i in range(scenario_count, vehicle_count):
                scenario = TrajectoryScenario(
                    self._vehicle_paths[i],
                    self._trajectory_paths[i],
                    self.METERS_PER_UNIT
                )
                scenario.enable_debug(self._enable_debug)
                self._scenarios.append(scenario)
                scenario_manager = ScenarioManager(scenario)
                self._scenario_managers.append(scenario_manager)
        for scenario in self._scenarios:
            scenario.reset()

        self.recompute_trajectories()

    def recompute_trajectories(self):
        assert(len(self._scenarios) == len(self._scenario_managers))
        for i in range(len(self._scenario_managers)):
            scenario = self._scenarios[i]
            manager = self._scenario_managers[i]
            scenario.recompute_trajectory()
            manager.set_scenario(scenario)

    def set_enable_debug(self, flag):
        self._enable_debug = flag
        for scenario in self._scenarios:
            scenario.enable_debug(flag)

    def set_hide_paths(self, flag):
        stage = omni.usd.get_context().get_stage()
        visibility_token = "invisible" if flag else "inherited"
        for path in self._trajectory_paths:
            stage.GetPrimAtPath(path).GetAttribute("visibility").Set(visibility_token)
    
    def set_draw_track(self, flag):
        for scenario in self._scenarios:
            scenario.draw_track = flag

    def load_ground_plane(self):
        stage = omni.usd.get_context().get_stage()
        path = omni.usd.get_stage_next_free_path(stage, "/GroundPlane", False)
        Utils.add_ground_plane(stage, path, "Y")

    def load_sample_vehicle(self):
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        forklift_prim_path = "/"
        forklift_prim_path = omni.usd.get_stage_next_free_path(
            usd_context.get_stage(),
            forklift_prim_path, 
            True
        )
        forklift_usd_path = f"{ext_path}/data/car.usd"
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=forklift_prim_path,
            asset_path=forklift_usd_path,
            usd_context=usd_context,
        )

    def load_sample_track(self):
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        basis_curve_prim_path = "/BasisCurves"
        basis_curve_prim_path = omni.usd.get_stage_next_free_path(
            usd_context.get_stage(),
            basis_curve_prim_path, 
            True
        )
        basis_curve_usd_path = f"{ext_path}/data/curve.usd"
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=basis_curve_prim_path,
            asset_path=basis_curve_usd_path,
            usd_context=usd_context,
        )

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

    # def _on_click_track_selected(self):
    #     selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
    #     self._model.attach_vehicle_to_curve(selected_paths)
        # selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        # if len(selected_paths) == 1:
        #     if len(self._trajectory_paths) > 0:
        #         self._trajectory_paths[0] = selected_paths[0]
        #     else:
        #         self._trajectory_paths.append(selected_paths[0])
        #     if len(self._scenarios) and len(self._scenario_managers):
        #         manager = self._scenario_managers[0]
        #         scenario = self._scenarios[0]
        #         scenario.recompute_trajectory()
        #         manager.set_scenario(scenario)

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
        prim_paths = [
            "/World_01/WizardVehicle1",
            "/World/BasisCurves/BasisCurves"
        ]
        self._model.attach_vehicle_to_curve(prim_paths)

    def _changed_enable_debug(self, model):
        self._model.set_enable_debug(model.as_bool)

    def _changed_hide_paths(self, model):
        self._model.set_hide_paths(model.as_bool)

    def _changed_draw_track(self, model):
        self._model.set_draw_track(model.as_bool)