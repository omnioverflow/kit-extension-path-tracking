"""Extension model class for path tracking extension."""
# pylint: disable=import-error, invalid-name
import carb
import omni
import omni.kit.commands
from omni.physxvehicle.scripts.commands import PhysXVehicleWizardCreateCommand
from omni.physxvehicle.scripts.helpers.UnitScale import UnitScale
from omni.physxvehicle.scripts.wizards import physxVehicleWizard as VehicleWizard
from pxr import PhysxSchema, UsdGeom, UsdPhysics

from .path_tracker import PurePursuitScenario
from .stepper import ScenarioManager
from .utils import Utils


class ExtensionModel:
    """Extension model class"""

    ROOT_PATH = "/World"
    VEHICLE_PRIM_NAME = "Vehicle"

    def __init__(self, extension_id, default_lookahead_distance, max_lookahed_distance, min_lookahed_distance):
        self._ext_id = extension_id
        self._METADATA_KEY = f"{extension_id.split('-')[0]}.metadata"
        self._lookahead_distance = default_lookahead_distance
        self.MIN_LOOKAHEAD_distance = min_lookahed_distance
        self.MAX_LOOKAHEAD_distance = max_lookahed_distance

        # self.meters_per_unit = 0.01
        # UsdGeom.SetStageMetersPerUnit(omni.usd.get_context().get_stage(), self.meters_per_unit)
        self.meters_per_unit = UsdGeom.GetStageMetersPerUnit(omni.usd.get_context().get_stage())

        stage = omni.usd.get_context().get_stage()
        self._up_axis = UsdGeom.GetStageUpAxis(stage).upper()

        self.vehicle_to_curve_attachments = {}
        self._scenario_managers = []
        self._dirty = False
        # Enables debug overlay with additional info regarding current vehicle state.
        self._enable_debug = False
        # Closed trajectory loop
        self._closed_trajectory_loop = False
        self._rear_steering = False

    def teardown(self):
        """Cleans up the extension model."""
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
            key = None
            if prim0.HasAPI(PhysxSchema.PhysxVehicleAPI):
                key = wizard_vehicle_path
            else:
                try:
                    # fallback to the first child with PhysxVehicleAPI
                    for child in prim0.GetChildren():
                        if child.HasAPI(PhysxSchema.PhysxVehicleAPI):
                            key = child.GetPath()
                            break
                except Exception as e:  # pylint: disable=broad-except
                    carb.log_warning(f"Failed to attach vehicle to curve: {e}")
                    key = None

            if key is None:
                carb.log_warning(f"Failed to attach vehicle to curve: {wizard_vehicle_path} is not a vehicle prim.")
                return
            self.vehicle_to_curve_attachments[key] = curve_path

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
                wizard_vehicle_path=selected_prim_paths[0],
                curve_path=selected_prim_paths[1]
            )

    def attach_preset_metadata(self, metadata):
        """
        Does vehicle-to-curve attachment from the metadata dictionary directly.
        """
        self.attach_vehicle_to_curve(
            wizard_vehicle_path=metadata["WizardVehicle"],
            curve_path=metadata["BasisCurve"]
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
        self.vehicle_to_curve_attachments.clear()

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

            for vehicle_path, curve in self.vehicle_to_curve_attachments.items():
                scenario = PurePursuitScenario(
                    lookahead_distance,
                    vehicle_path,
                    curve,
                    self.meters_per_unit,
                    self._closed_trajectory_loop,
                    self._rear_steering,
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
        for manager in self._scenario_managers:
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
        """
        Returns the unit scale for the current stage.
        """
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

        assert success
        assert not messageList
        assert scenePath and scenePath is not None

        return root_vehicle_path

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
        attachment_preset = metadata.get(self._METADATA_KEY)
        if not attachment_preset or attachment_preset is None:
            # Fallback to defaults
            attachment_preset = {
                "WizardVehicle": vehicle_path,
                "BasisCurve": "/World/BasisCurves/BasisCurves"
            }
        return attachment_preset

    def get_lookahead_distance(self):
        """Returns the lookahead distance parameter for pure pursuit"""
        return self._lookahead_distance

    def update_lookahead_distance(self, distance):
        """Updates the lookahead distance parameter for pure pursuit"""

        clamped_distance = max(
            self.MIN_LOOKAHEAD_distance,
            min(self.MAX_LOOKAHEAD_distance, distance)
        )

        for scenario_manager in self._scenario_managers:
            scenario_manager.scenario.set_lookahead_distance(clamped_distance)

        return clamped_distance
