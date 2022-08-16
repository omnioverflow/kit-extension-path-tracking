import omni.usd
import math
import numpy as np
import random
from pxr import Gf, Sdf, UsdShade
from .debug_renderer import DebugRenderer
from .path_tracking import PurePursuitPathTracker
from .stepper import Scenario
from .vehicle import Axle, Vehicle

# ==============================================================================
# Desitanation
# ==============================================================================
class Destination():
    def __init__(self):
        res, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Sphere")
        if res:
            stage = omni.usd.get_context().get_stage()
            self._prim = stage.GetPrimAtPath(path)
            
            x = random.uniform(5000.0, 10000.0)
            z = random.uniform(5000.0, 10000.0)

            attr_translate = self._prim.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Float3, False)
            attr_translate.Set(Gf.Vec3f(x, 0.0, z))
            self._prim.CreateAttribute("xformOp:rotateZYX", Sdf.ValueTypeNames.Float3, False).Set(
                Gf.Vec3f(0.0, 0.0, 0.0)
            )
            self._prim.CreateAttribute("xformOp:scale", Sdf.ValueTypeNames.Float3, False).Set(
                Gf.Vec3f(1.0, 1.0, 1.0)
            )
            self._prim.CreateAttribute("xformOpOrder", Sdf.ValueTypeNames.String, False).Set(
                ["xformOp:translate", "xformOp:rotateZYX", "xformOp:scale"]
            )

            mtl_created_list = []
            omni.kit.commands.execute(
                "CreateAndBindMdlMaterialFromLibrary",
                mdl_name="OmniPBR.mdl",
                mtl_name="RedOmniPBR",
                mtl_created_list=mtl_created_list,
            )

            self._red_mtl_prim = stage.GetPrimAtPath(mtl_created_list[0])
            omni.usd.create_material_input(self._red_mtl_prim, 
                "diffuse_color_constant", 
                Gf.Vec3f(1, 0, 0), 
                Sdf.ValueTypeNames.Color3f)
        
            red_mat_shade = UsdShade.Material(self._red_mtl_prim)
            UsdShade.MaterialBindingAPI(self._prim).Bind(red_mat_shade, UsdShade.Tokens.strongerThanDescendants)
    
    def teardown(self):
        stage = omni.usd.get_context().get_stage()
        stage.RemovePrim(self._prim.GetPath())
        stage.RemovePrim(self._red_mtl_prim.GetPath())

    def position(self):
        return self._prim.GetAttribute("xformOp:translate").Get()

# ==============================================================================
# SimpleScenario
# ==============================================================================
class SimpleScenario(Scenario):
    def __init__(self, viewport_ui, meters_per_unit, vehicle_path, destination=True):
        self._METERS_PER_UNIT = meters_per_unit
        self._viewport_ui = viewport_ui
        secondsToRun = 10000.0
        timeStepsPerSecond = 25
        super().__init__(secondsToRun, 1.0 / timeStepsPerSecond)

        self._stage = omni.usd.get_context().get_stage()
        self._vehicle = Vehicle(self._stage.GetPrimAtPath(vehicle_path))
        self._dest = Destination() if destination else None
        self._debug_render = DebugRenderer()
        self._motion_controller = PurePursuitPathTracker(math.pi / 4)
    
    def on_start(self):
        self._vehicle.accelerate(1.0)

    def on_end(self):
        pass
    
    def _vehicle_is_close_to(self, point):
        if not point:
            raise Exception("Point is None")
        curr_vehicle_pos = self._vehicle.curr_position()
        if not curr_vehicle_pos:
            raise Exception("curr_vehicle_pos is None")
        distance = np.linalg.norm(curr_vehicle_pos - point)
        return tuple([distance, distance < 400.0])

    def _process(self, forward, up, dest_position, distance=None, is_close_to_dest=False):
        if (distance is None):
            distance, is_close_to_dest = self._vehicle_is_close_to(dest_position)
        curr_vehicle_pos = self._vehicle.curr_position()

        self._debug_render.update_vehicle(self._vehicle)
        self._debug_render.update_path_to_dest(curr_vehicle_pos, dest_position)

        # Project onto xz
        curr_vehicle_pos[1] = 0.0
        forward[1] = 0.0
        dest_position[1] = 0.0

        velocity = self._vehicle.get_velocity()
        speed = self._vehicle_speed(velocity)
        axle_front = Gf.Vec3f(self._vehicle.axle_position(Axle.FRONT))
        # axle_front[1] = 0.0
        axle_rear = Gf.Vec3f(self._vehicle.axle_position(Axle.REAR))
        # axle_rear[1] = 0.0

        # self._debug_render.update_path_tracking(axle_front, axle_rear, forward, dest_position)

        steer_angle = self._motion_controller.on_step(
            axle_front,
            axle_rear,
            forward,
            dest_position,
            curr_vehicle_pos
        )

        # Accelerate/break control heuristic
        if steer_angle < 0:
            self._vehicle.steer_left(abs(steer_angle))
        else:
            self._vehicle.steer_right(steer_angle)
        if abs(steer_angle) > 0.3 and speed > 5.0:
            self._vehicle.brake(1.0)
            self._vehicle.accelerate(0.0)
        else:
            self._vehicle.brake(0.0)
            self._vehicle.accelerate(0.7)

    def _full_stop(self):
        self._vehicle.accelerate(0.0)
        self._vehicle.brake(1.0)

    def on_step(self, deltaTime, totalTime):
        R = self._vehicle.rotation_matrix()
        forward = self._vehicle.forward()
        up = self._vehicle.up()

        dest_position = self._dest.position()
        self._process(forward, up, dest_position)

    def _vehicle_speed(self, value):
        speed = value[0]*value[0] + value[1]*value[1] + value[2]*value[2]
        speed = math.sqrt(speed) * self._METERS_PER_UNIT
        return speed

    def set_meters_per_unit(self, value):
        self._METERS_PER_UNIT = value

    def teardown(self):
        super().abort()
        self._dest.teardown()
        self._dest = None
        self._stage = None
        self._vehicle = None
        self._debug_render = None
        self._motion_controller = None

    def enable_debug(self, flag):
        self._debug_render.enable(flag)