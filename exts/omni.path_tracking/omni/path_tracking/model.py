import omni
from pxr import UsdGeom
from .stepper import *
from .trajectory_scenario import TrajectoryScenario
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
        # Currently the extension expects Y-axis to be up-axis.
        # Conventionally Y-up is often used in graphics, including Kit-apps.
        # TODO: refactor impl to avoid breaking things when changing up-axis settings.
        self._up_axis = "Y"
        self._vehicle_paths = []
        self._trajectory_paths = []
        self._scenarios = []
        self._scenario_managers = []
        # Enables debug overlay with additional info regarding current vehicle state.
        self._enable_debug=False

    def teardown(self):
        for manager in self._scenario_managers:
            manager.stop_scenario()
        self._scenario_managers = None
        self._scenarios = None

    def attach_vehicle_to_curve(self, selected_paths):
        """
        Links a vehicle prim (must be WizardVehicle Xform) to the path (BasisCurve)
        to be tracked by the vechile.
        
        # Currently we expect two prims to be selected:
        # - WizardVehicle
        # - BasisCurve (corresponding curve/trajectory the vehicle must track)

        """
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
        """
        Removes previously added path tracking attachments.
        """
        self._vehicle_paths.clear()
        self._trajectory_paths.clear()

    def load_simulation(self):
        """
        Load scenarios with vehicle-to-curve attachments. 
        Note that multiple vehicles could run at the same time. 
        """
        vehicle_count = len(self._vehicle_paths)
        trajectory_count = len(self._trajectory_paths)
        scenario_count = len(self._scenarios)
        assert(vehicle_count == trajectory_count)

        if scenario_count < vehicle_count:
            for i in range(scenario_count, vehicle_count):
                scenario = TrajectoryScenario(
                    self._vehicle_paths[i],
                    self._trajectory_paths[i],
                    self.METERS_PER_UNIT,
                    i
                )
                scenario.enable_debug(self._enable_debug)
                self._scenarios.append(scenario)
                scenario_manager = ScenarioManager(scenario)
                self._scenario_managers.append(scenario_manager)
        for scenario in self._scenarios:
            scenario.reset()

        self.recompute_trajectories()

    def recompute_trajectories(self):
        """
        Update tracked trajectories. Often needed when BasisCurve defining a
        trajectory in the scene was updated by a user.
        """
        assert(len(self._scenarios) == len(self._scenario_managers))
        for i in range(len(self._scenario_managers)):
            scenario = self._scenarios[i]
            manager = self._scenario_managers[i]
            scenario.recompute_trajectory()
            manager.set_scenario(scenario)

    def set_enable_debug(self, flag):
        """
        Enables/disables debug overlay.
        """
        self._enable_debug = flag
        for scenario in self._scenarios:
            scenario.enable_debug(flag)

    def load_ground_plane(self):
        """
        Helper to quickly load a preset ground plane prim.
        """
        stage = omni.usd.get_context().get_stage()
        path = omni.usd.get_stage_next_free_path(stage, "/GroundPlane", False)
        Utils.add_ground_plane(stage, path, self._up_axis)

    def load_sample_vehicle(self):
        """
        Load a preset vechile from a USD data provider shipped with the extension.
        """
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
        """
        Load a sample BasisCurve serialiazed in USD.
        """
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

    def attachment_presets(self):
        """
        Prim paths for the preset scene with prim paths for vehicle-to-curve
        attachment.
        """
        return [
            "/World_01/WizardVehicle1",
            "/World/BasisCurves/BasisCurves"
        ]