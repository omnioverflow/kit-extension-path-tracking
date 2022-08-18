import omni.usd
import math
import numpy as np
import random
from pxr import Gf, Sdf
from .debug_renderer import DebugRenderer
from .path_tracking import PurePursuitPathTracker
from .stepper import Scenario
from .vehicle import Axle, Vehicle

# ==============================================================================
#
# SimpleScenario
#
# ==============================================================================
class SimpleScenario(Scenario):
    def __init__(self, viewport_ui, meters_per_unit, vehicle_path, destination=True):
        self._METERS_PER_UNIT = meters_per_unit
        self._max_speed = 250.0
        self._viewport_ui = viewport_ui
        secondsToRun = 10000.0
        timeStepsPerSecond = 25
        super().__init__(secondsToRun, 1.0 / timeStepsPerSecond)

        self._stage = omni.usd.get_context().get_stage()
        self._vehicle = Vehicle(self._stage.GetPrimAtPath(vehicle_path))
        self._dest = Destination() if destination else None
        self._debug_render = DebugRenderer()
        self._path_tracker = PurePursuitPathTracker(math.pi / 4)
    
    def on_start(self):
        self._vehicle.accelerate(1.0)

    def on_end(self):
        self._vehicle.brake(1.0)
    
    def _vehicle_is_close_to(self, point, is_end_point=False):
        if not point:
            raise Exception("Point is None")
        curr_vehicle_pos = self._vehicle.curr_position()
        if not curr_vehicle_pos:
            raise Exception("curr_vehicle_pos is None")
        distance = np.linalg.norm(curr_vehicle_pos - point)
        proximity_threshold = 400.0
        if is_end_point:
            proximity_threshold = 200.0

        return tuple([distance, distance < proximity_threshold])

    def _process(self, forward, up, dest_position, distance=None, is_close_to_dest=False):
        """
        Steering/accleleration vehicle control heuristic.
        """
        if (distance is None):
            distance, is_close_to_dest = self._vehicle_is_close_to(dest_position)
        curr_vehicle_pos = self._vehicle.curr_position()

        self._debug_render.update_vehicle(self._vehicle)
        self._debug_render.update_path_to_dest(curr_vehicle_pos, dest_position)

        # FIXME: - currently the extension expect Y-up axis which is not flexible.
        # Project onto XZ plane
        curr_vehicle_pos[1] = 0.0
        forward[1] = 0.0
        dest_position[1] = 0.0

        velocity = self._vehicle.get_velocity()
        speed = self._vehicle_speed(velocity)
        axle_front = Gf.Vec3f(self._vehicle.axle_position(Axle.FRONT))        
        axle_rear = Gf.Vec3f(self._vehicle.axle_position(Axle.REAR))
        axle_front[1] = 0.0
        axle_rear[1] = 0.0

        # self._debug_render.update_path_tracking(axle_front, axle_rear, forward, dest_position)

        steer_angle = self._path_tracker.on_step(
            axle_front,
            axle_rear,
            forward,
            dest_position,
            curr_vehicle_pos
        )

        if steer_angle < 0:
            self._vehicle.steer_left(abs(steer_angle))
        else:
            self._vehicle.steer_right(steer_angle)
        # Accelerate/break control heuristic
        if abs(steer_angle) > 0.1 and speed > 5.0:
            self._vehicle.brake(1.0)
            self._vehicle.accelerate(0.0)
        else:
            if (speed >= self._max_speed):
                self._vehicle.brake(0.8)
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
        self._path_tracker = None

    def enable_debug(self, flag):
        self._debug_render.enable(flag)

# ==============================================================================
# Desitanation
# ==============================================================================
class Destination():
    def __init__(self):
        """
        Models both position of the destination in 3D scene,
        and its visual representation as a sphere.
        """
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
    
    def teardown(self):
        stage = omni.usd.get_context().get_stage()
        stage.RemovePrim(self._prim.GetPath())
        stage.RemovePrim(self._red_mtl_prim.GetPath())

    def position(self):
        return self._prim.GetAttribute("xformOp:translate").Get()