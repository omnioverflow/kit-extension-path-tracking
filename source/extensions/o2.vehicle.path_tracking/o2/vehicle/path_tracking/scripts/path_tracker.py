"""Path tracking implementation for vehicle simulation."""

import math
from typing import Optional

import numpy as np
import omni.usd
from pxr import Gf, UsdGeom

from .debug_draw import DebugRenderer
from .stepper import Scenario
from .trajectory import Trajectory
from .utils import UpAxisHelper
from .vehicle import Axle, Vehicle


class PurePursuitScenario(Scenario):
    """
    Implements a path tracking scenario for vehicle simulation in Omniverse.
    """

    def __init__(
        self,
        lookahead_distance,
        vehicle_path,
        trajectory_prim_path,
        meters_per_unit,
        close_loop_flag,
        enable_rear_steering,
    ):
        super().__init__(seconds_to_run=10000.0, time_step=1.0 / 25.0)

        self._MAX_STEER_ANGLE_RADIANS = math.pi / 3

        self._lookahead_distance = lookahead_distance
        self.meters_per_unit = meters_per_unit
        self._max_speed = 250.0

        self._stage = omni.usd.get_context().get_stage()
        self._vehicle = Vehicle(
            self._stage.GetPrimAtPath(vehicle_path), self._MAX_STEER_ANGLE_RADIANS, enable_rear_steering
        )
        self._debug_render = DebugRenderer(self._vehicle.get_bbox_size())
        self._path_tracker = PurePursuitPathTracker(math.pi / 4)

        self._dest = None
        self._trajectory_prim_path = trajectory_prim_path
        self._trajectory = Trajectory(trajectory_prim_path, close_loop=close_loop_flag)
        self._stopped = False
        self.draw_track = False
        self._close_loop = close_loop_flag

        up_axis_token = UsdGeom.GetStageUpAxis(self._stage)
        self._up_axis_index = {"X": 0, "Y": 1, "Z": 2}[up_axis_token.upper()]
        self._flat_indices = [i for i in range(3) if i != self._up_axis_index]
        up = UpAxisHelper.get_up_axis_index()
        self._steer_sign = 1 if up == 2 else -1

    def on_start(self):
        self._vehicle.accelerate(1.0)

    def on_end(self):
        self._trajectory.reset()

    def _process(self, forward, up, dest_position, distance=None):
        """
        Steering/acceleration vehicle control heuristic, generalized for any stage up-axis.
        """
        if distance is None:
            distance, _ = self._vehicle.is_close_to(dest_position, self._lookahead_distance)

        curr_vehicle_pos = self._vehicle.curr_position()

        speed = self._vehicle.get_speed() * self.meters_per_unit
        axle_front = self._vehicle.axle_position(Axle.FRONT)
        axle_rear = self._vehicle.axle_position(Axle.REAR)

        self._debug_render.draw_vehicle_debug(self._vehicle, self._trajectory, axle_front, axle_rear, forward, up)
        self._debug_render.update_path_to_dest(curr_vehicle_pos, dest_position)

        steer_angle = self._path_tracker.on_step(axle_front, axle_rear, dest_position)

        asjusted_steer_angle = steer_angle * self._steer_sign
        if asjusted_steer_angle < 0:
            self._vehicle.steer_left(abs(steer_angle))
        else:
            self._vehicle.steer_right(abs(steer_angle))

        # Heuristic for throttle/brake control
        if abs(steer_angle) > 0.1 and speed > 5.0:
            self._vehicle.brake(1.0)
            self._vehicle.accelerate(0.0)
        else:
            if speed >= self._max_speed:
                self._vehicle.brake(0.8)
                self._vehicle.accelerate(0.0)
            else:
                self._vehicle.brake(0.0)
                self._vehicle.accelerate(0.7)

    def _full_stop(self):
        self._vehicle.accelerate(0.0)
        self._vehicle.brake(1.0)

    def set_meters_per_unit(self, value):
        """Sets meters per unit for the path tracker."""
        self.meters_per_unit = value

    def teardown(self):
        """Tears down the path tracker."""
        self._dest.teardown()
        self._dest = None
        self._stage = None
        self._vehicle = None
        self._debug_render = None
        self._path_tracker = None

    def enable_debug(self, flag):
        """Enables/disables debug rendering."""
        self._debug_render.enable = flag

    def on_step(self, _delta_time, _total_time):
        """
        Updates vehicle control on sim update callback in order to stay on tracked path.
        """
        forward = self._vehicle.forward()
        up = self._vehicle.up()

        if self._trajectory and self.draw_track:
            self._trajectory.draw()

        dest_position = self._trajectory.point()
        # Run vehicle control unless reached the destination
        if dest_position:
            distance, is_close_to_dest = self._vehicle.is_close_to(dest_position, self._lookahead_distance)
            if is_close_to_dest:
                dest_position = self._trajectory.next_point()
            else:
                self._process(forward, up, dest_position, distance)
        else:
            self._stopped = True
            self._full_stop()

    def recompute_trajectory(self):
        """Recomputes trajectory points."""
        self._trajectory = Trajectory(self._trajectory_prim_path, self._close_loop)

    def set_lookahead_distance(self, distance):
        """Sets lookahead distance for the path tracker."""
        self._lookahead_distance = distance

    def set_close_trajectory_loop(self, flag):
        """Sets trajectory loop flag."""
        self._close_loop = flag
        self._trajectory.close_loop = flag


class PurePursuitPathTracker:
    """
    Implements path tracking in spirit of Pure Pursuit algorithm.
    References
    * Implementation of the Pure Pursuit Path tracking Algorithm,  RC Conlter:
    https://www.ri.cmu.edu/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf
    * https://dingyan89.medium.com/three-methods-of-vehicle-lateral-control-pure-pursuit-stanley-and-mpc-db8cc1d32081
    """

    def __init__(self, max_steer_angle_radians):
        self._max_steer_angle_radians = max_steer_angle_radians
        self._debug_enabled = False

    def _steer_value_from_angle(self, angle):
        """
        Computes vehicle's steering wheel angle in expected range [-1, 1].
        """
        return np.clip(angle / self._max_steer_angle_radians, -1.0, 1.0)

    def on_step(self, front_axle_pos, rear_axle_pos, dest_vec):
        """Recomputes vehicle's steering angle on a simulation step."""
        front_axle_flat = UpAxisHelper.flatten(front_axle_pos)
        rear_axle_flat = UpAxisHelper.flatten(rear_axle_pos)
        dest_flat = UpAxisHelper.flatten(dest_vec)

        lookahead = dest_flat - rear_axle_flat
        forward = front_axle_flat - rear_axle_flat

        lookahead_dist = np.linalg.norm(lookahead)
        forward_dist = np.linalg.norm(forward)

        assert lookahead_dist > 0.0 and forward_dist > 0.0

        lookahead /= lookahead_dist
        forward /= forward_dist

        dot = np.dot(lookahead, forward)
        cross = lookahead[0] * forward[1] - lookahead[1] * forward[0]
        alpha = math.atan2(cross, dot)

        theta = math.atan(2.0 * forward_dist * math.sin(alpha) / lookahead_dist)
        return self._steer_value_from_angle(theta)
