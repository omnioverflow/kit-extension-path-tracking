"""VehicleFactory: Static factory for creating PhysX vehicles in Omniverse."""
import omni
import omni.usd
import omni.timeline

from pxr import Usd, UsdGeom, UsdPhysics
from typing import Callable, Optional, Tuple


from omni.physxvehicle.scripts.wizards import physxVehicleWizard as physxVehicleWizard


class VehicleFactory:
    """
    Static factory for creating PhysX vehicles via the Wizard command on an existing stage.

    Core entrypoint:
        VehicleFactory.create_vehicle(stage, parent_path=None, vehicle_name=None, customize=None)

    Convenience presets:
        VehicleFactory.create_standard(stage, **kwargs)
        VehicleFactory.create_basic(stage, **kwargs)

    The optional `customize(vdm, vd, stage)` callback lets clients tweak VehicleDataManager/VehicleData
    (e.g. size, drive type, tire friction, etc.) before the command executes.
    """

    @staticmethod
    def create_vehicle(
        stage: Usd.Stage,
        *,
        parent_path: Optional[str] = None,
        vehicle_name: Optional[str] = None,
        customize: Optional[Callable[[object, object, Usd.Stage], None]] = None,
    ) -> Tuple[bool, list, object, str, str]:
        VehicleFactory._ensure_timeline_stopped()

        root_parent = parent_path or VehicleFactory._resolve_parent_root(stage)
        unit_scale, vertical_axis, longitudinal_axis = VehicleFactory._derive_units_and_axes(stage)

        vdm = physxVehicleWizard.VehicleDataManager(unit_scale, vertical_axis, longitudinal_axis)
        vd = vdm.vehicleData  # vehicleData holds the unit scale in some versions

        base_vehicle = VehicleFactory._compose_base_vehicle_path(root_parent, vehicle_name)
        vehicle_root_path = omni.usd.get_stage_next_free_path(
            stage, base_vehicle, prepend_default_prim=False, source_prim=None
        )
        shared_root_path = root_parent + physxVehicleWizard.SHARED_DATA_ROOT_BASE_PATH

        vd.rootVehiclePath = vehicle_root_path
        vd.rootSharedPath = shared_root_path

        if customize:
            customize(vdm, vd, stage)

        success, (messages, tracker) = physxVehicleWizard.commands.PhysXVehicleWizardCreateCommand.execute(vd)
        return success, messages, tracker, vehicle_root_path, shared_root_path


    @staticmethod
    def create_standard(
        stage: Usd.Stage,
        **kwargs
    ) -> Tuple[bool, list, object, str, str]:
        """
        Convenience: create a 'standard' drive-type vehicle (if the wizard exposes the constant).
        Falls back gracefully if the symbol is absent in your version.
        """
        def preset(vdm, vd, _stage):
            # These APIs vary by Kit/extension version; guard with hasattr.
            if hasattr(vdm, "set_drive_type") and hasattr(physxVehicleWizard, "DRIVE_TYPE_STANDARD"):
                vdm.set_drive_type(physxVehicleWizard.DRIVE_TYPE_STANDARD)
                if hasattr(vdm, "update"):
                    vdm.update()
        return VehicleFactory.create_vehicle(stage, customize=preset, **kwargs)

    @staticmethod
    def create_basic(
        stage: Usd.Stage,
        **kwargs
    ) -> Tuple[bool, list, object, str, str]:
        """
        Convenience: create a 'basic' drive-type vehicle if available.
        """
        def preset(vdm, vd, _stage):
            if hasattr(vdm, "set_drive_type") and hasattr(physxVehicleWizard, "DRIVE_TYPE_BASIC"):
                vdm.set_drive_type(physxVehicleWizard.DRIVE_TYPE_BASIC)
                if hasattr(vdm, "update"):
                    vdm.update()
        return VehicleFactory.create_vehicle(stage, customize=preset, **kwargs)

    @staticmethod
    def _ensure_timeline_stopped():
        tl = omni.timeline.get_timeline_interface()
        if not tl.is_stopped():
            tl.stop()

    @staticmethod
    def _resolve_parent_root(stage: Usd.Stage) -> str:
        """Choose where to place the vehicle & shared data."""
        default_prim = stage.GetDefaultPrim()
        if default_prim and default_prim.IsValid():
            return str(default_prim.GetPath())
        world = stage.GetPrimAtPath("/World")
        if world and world.IsValid():
            return str(world.GetPath())
        # Last resort: first root child under pseudo-root
        root_children = list(stage.GetPseudoRoot().GetChildren())
        if not root_children:
            # If truly empty stage, define /World but DO NOT change up-axis or units.
            world = UsdGeom.Xform.Define(stage, "/World")
            stage.SetDefaultPrim(world.GetPrim())
            return "/World"
        return str(root_children[0].GetPath())

    @staticmethod
    def _derive_units_and_axes(stage: Usd.Stage):
        """Read (do not modify) current stage units/axes and map to wizard expectations."""
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
        kilograms_per_unit = UsdPhysics.GetStageKilogramsPerUnit(stage)
        unit_scale = physxVehicleWizard.UnitScale(lengthScale=1.0 / meters_per_unit,
                                  massScale=1.0 / kilograms_per_unit)

        up = UsdGeom.GetStageUpAxis(stage)
        if up == UsdGeom.Tokens.z:
            vertical_axis = physxVehicleWizard.VehicleData.AXIS_Z
            longitudinal_axis = physxVehicleWizard.VehicleData.AXIS_X
        else:
            vertical_axis = physxVehicleWizard.VehicleData.AXIS_Y
            longitudinal_axis = physxVehicleWizard.VehicleData.AXIS_Z
        return unit_scale, vertical_axis, longitudinal_axis

    @staticmethod
    def _compose_base_vehicle_path(parent_root: str, vehicle_name: Optional[str]) -> str:
        """
        Compose a base path for the vehicle root.
        """
        if vehicle_name:
            name_path = vehicle_name if vehicle_name.startswith("/") else f"/{vehicle_name}"
            return f"{parent_root}{name_path}"

        return f"{parent_root}{physxVehicleWizard.VEHICLE_ROOT_BASE_PATH}"


if __name__ == "__main__":
    stage = omni.usd.get_context().get_stage()
    assert stage, "No stage is open. Open a stage before running."

    ok, msgs, tracker, vroot, sroot = VehicleFactory.create_vehicle(stage)
