import omni
from pxr import UsdGeom
import omni.kit.commands
from omni.physxvehicle.scripts.wizards import physxVehicleWizard as VehicleWizard
from omni.physxvehicle.scripts.helpers.UnitScale import UnitScale
from omni.physxvehicle.scripts.commands import *

from .stepper import *
from .path_tracker import PurePursuitScenario
from .utils import Utils

# ==============================================================================
# 
# ExtensionModel
# 
# ==============================================================================
class ExtensionModel:

    ROOT_PATH = "/World"

    def __init__(self, extension_id, default_lookahead_distance, max_lookahed_distance, min_lookahed_distance):
        self._ext_id = extension_id
        self._METADATA_KEY = f"{extension_id.split('-')[0]}.metadata"
        self._lookahead_distance = default_lookahead_distance
        self._min_lookahead_distance = min_lookahed_distance
        self._max_lookahead_distance = max_lookahed_distance
        self.METERS_PER_UNIT = 0.01
        UsdGeom.SetStageMetersPerUnit(omni.usd.get_context().get_stage(), self.METERS_PER_UNIT)
        # Currently the extension expects Y-axis to be up-axis.
        # Conventionally Y-up is often used in graphics, including Kit-apps.
        # TODO: refactor impl to avoid breaking things when changing up-axis settings.
        self._up_axis = "Y"
        self._vehicle_to_curve_attachments = {}
        self._scenario_managers = []
        self._dirty = False
        # Enables debug overlay with additional info regarding current vehicle state.
        self._enable_debug=False
        # Closed trajectory loop
        self._closed_trajectory_loop = False
        self._rear_steering = False

    def teardown(self):
        self.stop_scenarios()
        self._scenario_managers = None

    def attach_vehicle_to_curve(self, wizard_vehicle_path, curve_path):
        """
        Links a vehicle prim (must be WizardVehicle Xform) to the path (BasisCurve)
        to be tracked by the vechile.
        
        Currently we expect two prims to be selected:
        - WizardVehicle
        - BasisCurve (corresponding curve/trajectory the vehicle must track)

        """
        stage = omni.usd.get_context().get_stage()
        prim0 = stage.GetPrimAtPath(wizard_vehicle_path)
        prim1 = stage.GetPrimAtPath(curve_path)
        if prim0.IsA(UsdGeom.BasisCurves):
            # Fix order of selected prims: WizardVehicle should be first
            prim0, prim1 = prim1, prim0
            wizard_vehicle_path, curve_path = curve_path, wizard_vehicle_path
        if prim0.IsA(UsdGeom.Xformable):
            key = wizard_vehicle_path + "/Vehicle"
            self._vehicle_to_curve_attachments[key] = curve_path
        self._dirty = True

    def attach_selected_prims(self, selected_prim_paths):
        """
        Attaches selected prims paths from a stage to be considered as a 
        vehicle and path to be tracked correspondingly.
        The selected prim paths should include a WizardVehicle Xform that 
        represents vehicle, and a BasisCurves that represents tracked path.
        """
        if len(selected_prim_paths) == 2:
            self.attach_vehicle_to_curve(
                wizard_vehicle_path = selected_prim_paths[0], 
                curve_path = selected_prim_paths[1]
            )

    def attach_preset_metadata(self, metadata):
        """
        Does vehicle-to-curve attachment from the metadata dictionary directly.
        """
        self.attach_vehicle_to_curve(
            wizard_vehicle_path = metadata["WizardVehicle"],
            curve_path = metadata["BasisCurve"]
        )
    
    def _cleanup_scenario_managers(self):
        """Cleans up scenario managers. Often useful when tracked data becomes obsolete."""
        self.stop_scenarios()
        for manager in self._scenario_managers:
            manager.cleanup()
        self._scenario_managers.clear()
        self._dirty = True

    def clear_attachments(self):
        """
        Removes previously added path tracking attachments.
        """
        self._cleanup_scenario_managers()
        self._vehicle_to_curve_attachments.clear()

    def stop_scenarios(self):
        """
        Stops path tracking scenarios.
        """
        for manager in self._scenario_managers:
            manager.stop_scenario()

    def load_simulation(self, lookahead_distance):
        """
        Load scenarios with vehicle-to-curve attachments. 
        Note that multiple vehicles could run at the same time. 
        """
        if self._dirty:
            self._cleanup_scenario_managers()

            for vehicle_path in self._vehicle_to_curve_attachments:
                scenario = PurePursuitScenario(
                    lookahead_distance,
                    vehicle_path,
                    self._vehicle_to_curve_attachments[vehicle_path],
                    self.METERS_PER_UNIT,
                    self._closed_trajectory_loop,
                    self._rear_steering
                )
                scenario.enable_debug(self._enable_debug)
                scenario_manager = ScenarioManager(scenario)
                self._scenario_managers.append(scenario_manager)
            self._dirty = False

        self.recompute_trajectories()

    def recompute_trajectories(self):
        """
        Update tracked trajectories. Often needed when BasisCurve defining a
        trajectory in the scene was updated by a user.
        """
        for i in range(len(self._scenario_managers)):
            manager = self._scenario_managers[i]
            manager.scenario.recompute_trajectory()

    def set_enable_debug(self, flag):
        """
        Enables/disables debug overlay.
        """
        self._enable_debug = flag
        for manager in self._scenario_managers:
            manager.scenario.enable_debug(flag)

    def set_close_trajectory_loop(self, flag):
        """
        Enables closed loop path tracking.
        """
        self._closed_trajectory_loop = flag
        for manager in self._scenario_managers:
            manager.scenario.set_close_trajectory_loop(flag)

    def set_enable_rear_steering(self, flag):
        """
        Enables rear steering for the vehicle.
        """
        self._rear_steering = flag
        # Mark simulation config as dirty in order to re-create vehicle object.
        self._dirty = True

    def load_ground_plane(self):
        """
        Helper to quickly load a preset ground plane prim.
        """
        stage = omni.usd.get_context().get_stage()
        path = omni.usd.get_stage_next_free_path(stage, "/GroundPlane", False)
        Utils.add_ground_plane(stage, path, self._up_axis)

    def get_unit_scale(self, stage):
        metersPerUnit = UsdGeom.GetStageMetersPerUnit(stage)
        lengthScale = 1.0 / metersPerUnit
        kilogramsPerUnit = UsdPhysics.GetStageKilogramsPerUnit(stage)
        massScale = 1.0 / kilogramsPerUnit
        return UnitScale(lengthScale, massScale)

    def load_sample_vehicle(self):
        """
        Load a preset vechile from a USD data provider shipped with the extension.
        """
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        vehicleData = VehicleWizard.VehicleData(self.get_unit_scale(stage),
        VehicleWizard.VehicleData.AXIS_Y, VehicleWizard.VehicleData.AXIS_Z)

        root_vehicle_path = self.ROOT_PATH + VehicleWizard.VEHICLE_ROOT_BASE_PATH
        root_vehicle_path = omni.usd.get_stage_next_free_path(stage, root_vehicle_path, True)
        root_shared_path = self.ROOT_PATH + VehicleWizard.SHARED_DATA_ROOT_BASE_PATH
        root_vehicle_path = omni.usd.get_stage_next_free_path(stage, root_shared_path, True)
        
        vehicleData.rootVehiclePath = root_vehicle_path
        vehicleData.rootSharedPath = root_shared_path

        (success, (messageList, scenePath)) = PhysXVehicleWizardCreateCommand.execute(vehicleData)
        
        assert(success)
        assert(not messageList)
        assert(scenePath and scenePath is not None)

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
        basis_curve_usd_path = f"{ext_path}/data/usd/curve.usd"
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=basis_curve_prim_path,
            asset_path=basis_curve_usd_path,
            usd_context=usd_context,
        )

    def load_forklift_rig(self):
        """Load a forklift model from USD with already exisitng physx vehicle rig."""
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        forklift_prim_path = "/ForkliftRig"
        forklift_prim_path = omni.usd.get_stage_next_free_path(
            usd_context.get_stage(),
            forklift_prim_path, 
            True
        )
        vehicle_usd_path = f"{ext_path}/data/usd/forklift/forklift_rig.usd"
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=forklift_prim_path,
            asset_path=vehicle_usd_path,
            usd_context=usd_context,
        )
        return forklift_prim_path

    def load_preset_scene(self):
        """
        Loads a preset scene with vehicle template and predefined curve for
        path tracking.
        """
        default_prim_path = self.ROOT_PATH
        stage = omni.usd.get_context().get_stage()
        if not stage.GetPrimAtPath(default_prim_path):
            omni.kit.commands.execute(
                "CreatePrim", prim_path=default_prim_path,
                prim_type="Xform", select_new_prim=True, attributes={}
            )
            stage.SetDefaultPrim(stage.GetPrimAtPath(default_prim_path))

        self.load_ground_plane()
        vehicle_prim_path = self.load_sample_vehicle()
        self.load_sample_track()
        metadata_vehicle_to_curve = self.get_attachment_presets(vehicle_prim_path)
        self.attach_preset_metadata(metadata_vehicle_to_curve)

    def get_attachment_presets(self, vehicle_path):
        """
        Prim paths for the preset scene with prim paths for vehicle-to-curve
        attachment.
        """
        stage = omni.usd.get_context().get_stage()
        vehicle_prim = stage.GetPrimAtPath(vehicle_path)
        metadata = vehicle_prim.GetCustomData()
        # Vehicle-to-Curve attachment of the preset is stored in the metadata.
        attachment_preset = metadata[self._METADATA_KEY]
        assert(attachment_preset is not None)
        return attachment_preset

    def get_lookahead_distance(self):
        return self._lookahead_distance

    def update_lookahead_distance(self, distance):
        """Updates the lookahead distance parameter for pure pursuit"""

        clamped_distance = max(
            self._min_lookahead_distance,
            min(self._max_lookahead_distance, distance)
        )

        for scenario_manager in self._scenario_managers:
            scenario_manager.scenario.set_lookahead_distance(clamped_distance)

        return clamped_distance