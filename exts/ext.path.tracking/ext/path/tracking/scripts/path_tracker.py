import omni.usd
import carb
from pxr import Gf, UsdGeom

import math
import numpy as np

from .debug_draw import DebugRenderer
from .stepper import Scenario
from .vehicle import Axle, Vehicle

# ==============================================================================
#
# PurePursuitScenario
#
# ==============================================================================
class PurePursuitScenario(Scenario):
    def __init__(self, lookahead_distance, vehicle_path, trajectory_prim_path, meters_per_unit,
                 close_loop_flag, enable_rear_steering):
        super().__init__(secondsToRun=10000.0, timeStep=1.0/25.0)

        self._MAX_STEER_ANGLE_RADIANS = math.pi / 3

        self._lookahead_distance = lookahead_distance
        self._METERS_PER_UNIT = meters_per_unit
        self._max_speed = 250.0

        self._stage = omni.usd.get_context().get_stage()
        self._vehicle = Vehicle(
            self._stage.GetPrimAtPath(vehicle_path),
            self._MAX_STEER_ANGLE_RADIANS,
            enable_rear_steering
        )
        self._debug_render = DebugRenderer(self._vehicle.get_bbox_size())
        self._path_tracker = PurePursuitPathTracker(math.pi/4)

        self._dest = None
        self._trajectory_prim_path = trajectory_prim_path
        self._trajectory = Trajectory(trajectory_prim_path, close_loop=close_loop_flag)
        self._stopped = False
        self.draw_track = False
        self._close_loop = close_loop_flag
    
    def on_start(self):
        self._vehicle.accelerate(1.0)

    def on_end(self):
        self._trajectory.reset()

    def _process(self, forward, up, dest_position, distance=None, is_close_to_dest=False):
        """
        Steering/accleleration vehicle control heuristic.
        """
        if (distance is None):
            distance, is_close_to_dest = self._vehicle.is_close_to(dest_position, self._lookahead_distance)
        curr_vehicle_pos = self._vehicle.curr_position()

        self._debug_render.update_vehicle(self._vehicle)
        self._debug_render.update_path_to_dest(curr_vehicle_pos, dest_position)

        # FIXME: - currently the extension expect Y-up axis which is not flexible.
        # Project onto XZ plane
        curr_vehicle_pos[1] = 0.0
        forward[1] = 0.0
        dest_position[1] = 0.0

        speed = self._vehicle.get_speed() * self._METERS_PER_UNIT
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

    def on_step(self, deltaTime, totalTime):
        """
        Updates vehicle control on sim update callback in order to stay on tracked path.
        """
        forward = self._vehicle.forward()
        up = self._vehicle.up()
        
        if self._trajectory and self.draw_track:
            self._trajectory.draw()

        dest_position = self._trajectory.point()
        is_end_point = self._trajectory.is_at_end_point()
        # Run vehicle control unless reached the destination
        if dest_position:
            distance, is_close_to_dest = self._vehicle.is_close_to(dest_position, self._lookahead_distance)
            if (is_close_to_dest):
                dest_position = self._trajectory.next_point()                
            else:
                # Compute vehicle steering and acceleration
                self._process(forward, up, dest_position, distance, is_close_to_dest)
        else:
            self._stopped = True
            self._full_stop()

    def recompute_trajectory(self):
        self._trajectory = Trajectory(self._trajectory_prim_path, self._close_loop)

    def set_lookahead_distance(self, distance):
        self._lookahead_distance = distance

    def set_close_trajectory_loop(self, flag):
        self._close_loop = flag
        self._trajectory.set_close_loop(flag)

# ==============================================================================
# 
# PurePursuitPathTracker
# 
# ==============================================================================
class PurePursuitPathTracker():
    """
    Implements path tracking in spirit of Pure Pursuit algorithm.
 
    References
    * Implementation of the Pure Pursuit Path tracking Algorithm,  RC Conlter:
    https://www.ri.cmu.edu/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf
    * https://dingyan89.medium.com/three-methods-of-vehicle-lateral-control-pure-pursuit-stanley-and-mpc-db8cc1d32081
    """

    def __init__(self, max_steer_angle_radians):
        self._max_steer_angle_radians = max_steer_angle_radians

    def _steer_value_from_angle(self, angle):
        """
        Computes vehicle's steering wheel angle in expected range [-1, 1].
        """
        return np.clip(angle / self._max_steer_angle_radians, -1.0, 1.0)

    def on_step(self, front_axle_pos, rear_axle_pos, forward, dest_pos, curr_pos):
        """
        Recomputes vehicle's steering angle on a simulation step.
        """
        front_axle_pos, rear_axle_pos = rear_axle_pos, front_axle_pos
        # Lookahead points to the next destination point
        lookahead = dest_pos - rear_axle_pos
        # Forward vector corrsponds to an axis segment front-to-rear
        forward = front_axle_pos - rear_axle_pos

        lookahead_dist = np.linalg.norm(lookahead)
        forward_dist = np.linalg.norm(forward)
        if lookahead_dist == 0.0 or forward_dist == 0.0:
            raise Exception("Pure pursuit aglorithm: invalid state")

        lookahead.Normalize()
        forward.Normalize()
        
        # Compute a signed angle alpha between lookahead and forward vectors,
        # /!\ left-handed rotation assumed.
        dot = lookahead[0] * forward[0] + lookahead[2] * forward[2]
        cross = lookahead[0] * forward[2] - lookahead[2] * forward[0]
        alpha = math.atan2(cross, dot)

        theta = math.atan(2.0 * forward_dist * math.sin(alpha) / lookahead_dist)
        steer_angle = self._steer_value_from_angle(theta)

        return steer_angle

# ==============================================================================
# 
# Trajectory
# 
# ==============================================================================
class Trajectory():
    """
    A helper class to access coordinates of points that form a BasisCurve prim.
    """
    def __init__(self, prim_path, close_loop=True):
        stage = omni.usd.get_context().get_stage()
        basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)
        if (basis_curves and basis_curves is not None):
            curve_prim = stage.GetPrimAtPath(prim_path)
            self._points = basis_curves.GetPointsAttr().Get()
            self._num_points = len(self._points)
            cache = UsdGeom.XformCache()
            T = cache.GetLocalToWorldTransform(curve_prim)

            for i in range(self._num_points):
                p = Gf.Vec4d(self._points[i][0], self._points[i][1], self._points[i][2], 1.0)
                p_ = p * T
                self._points[i] = Gf.Vec3f(p_[0], p_[1], p_[2])
        else:
            self._points = None
            self._num_points = 0
        self._pointer = 0
        self._close_loop = close_loop

    def point(self):
        """
        Returns current point.
        """
        return self._points[self._pointer] if self._pointer < len(self._points) else None

    def next_point(self):
        """
        Next point on the curve.
        """
        if (self._pointer < self._num_points):
            self._pointer = self._pointer + 1
            if self._pointer >= self._num_points and self._close_loop:
                self._pointer = 0
            return self.point()
        return None

    def is_at_end_point(self):
        """
        Checks if the current point is the last one.
        """
        return self._pointer == (self._num_points - 1)

    def reset(self):
        """
        Resets current point to the first one.
        """
        self._pointer = 0

    def set_close_loop(self, flag):
        self._close_loop = flag