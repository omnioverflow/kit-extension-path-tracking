"""
Vehicle class to manipulate vehicle state and properties.
"""

# pylint: disable=invalid-name
from enum import IntEnum

import numpy as np
import omni.usd
from pxr import Gf, PhysxSchema, Usd, UsdGeom

from .utils import UpAxisHelper


class Axle(IntEnum):
    """Enumeration for vehicle axles."""

    FRONT = (0,)
    REAR = 1


class Wheel(IntEnum):
    """Enumeration for vehicle wheels."""

    FRONT_LEFT = (0,)
    FRONT_RIGHT = (1,)
    REAR_LEFT = (2,)
    REAR_RIGHT = 3


class Vehicle:
    """
    A wrapper created to help manipulating state of a vehicle prim and its
    dynamic properties, such as acceleration, desceleration, steering etc.
    """

    def __init__(self, vehicle_prim, max_steer_angle_radians, rear_steering=True):
        self.up_axis_index: int = UpAxisHelper.get_up_axis_index()
        self._prim = vehicle_prim
        self._path = self._prim.GetPath()
        self._steer_delta = 0.01
        self._stage = omni.usd.get_context().get_stage()
        self._rear_stearing = rear_steering
        self._wheel_prims = {
            Wheel.FRONT_LEFT: self._stage.GetPrimAtPath(f"{self._path}/LeftWheel1References"),
            Wheel.FRONT_RIGHT: self._stage.GetPrimAtPath(f"{self._path}/RightWheel1References"),
            Wheel.REAR_LEFT: self._stage.GetPrimAtPath(f"{self._path}/LeftWheel2References"),
            Wheel.REAR_RIGHT: self._stage.GetPrimAtPath(f"{self._path}/RightWheel2References"),
        }
        steering_wheels = [Wheel.FRONT_LEFT, Wheel.FRONT_RIGHT]
        non_steering_wheels = [Wheel.REAR_LEFT, Wheel.REAR_RIGHT]
        if self._rear_stearing:
            steering_wheels, non_steering_wheels = non_steering_wheels, steering_wheels

        for wheel_prim_key in steering_wheels:
            self._set_max_steer_angle(self._wheel_prims[wheel_prim_key], max_steer_angle_radians)

        for wheel_prim_key in non_steering_wheels:
            self._set_max_steer_angle(self._wheel_prims[wheel_prim_key], 0.0)

        p = self._prim.GetAttribute("xformOp:translate").Get()
        self._p = Gf.Vec4f(p[0], p[1], p[2], 1.0)

    def _set_max_steer_angle(self, wheel_prim, max_steer_angle_radians):
        physx_wheel = PhysxSchema.PhysxVehicleWheelAPI(wheel_prim)
        physx_wheel.GetMaxSteerAngleAttr().Set(max_steer_angle_radians)

    def get_bbox_size(self):
        """Computes size of vehicle's oriented bounding box."""
        purposes = [UsdGeom.Tokens.default_]
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes)
        return bbox_cache.ComputeWorldBound(self._prim).ComputeAlignedRange().GetSize()

    def steer_left(self, value):
        """Steer left if rear steering is enabled, otherwise steer right."""
        if self._rear_stearing:
            self._steer_right_priv(value)
        else:
            self._steer_left_priv(value)

    def steer_right(self, value):
        """Steer right if rear steering is enabled, otherwise steer left."""
        if self._rear_stearing:
            self._steer_left_priv(value)
        else:
            self._steer_right_priv(value)

    def _steer_left_priv(self, value):
        self._prim.GetAttribute("physxVehicleController:steerLeft").Set(value)
        self._prim.GetAttribute("physxVehicleController:steerRight").Set(0.0)

    def _steer_right_priv(self, value):
        self._prim.GetAttribute("physxVehicleController:steerLeft").Set(0.0)
        self._prim.GetAttribute("physxVehicleController:steerRight").Set(value)

    def accelerate(self, value):
        """Accelerate the vehicle."""
        self._vehicle().GetAttribute("physxVehicleController:accelerator").Set(value)

    def brake(self, value):
        """Apply brake to the vehicle."""
        self._prim.GetAttribute("physxVehicleController:brake").Set(value)

    def get_velocity(self):
        """Get the vehicle's velocity."""
        return self._prim.GetAttribute("physics:velocity").Get()

    def get_speed(self):
        """Get the vehicle's speed."""
        return np.linalg.norm(self.get_velocity())

    def curr_position(self):
        """Get the current position of the vehicle."""
        prim = self._vehicle()

        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(prim)
        p = self._p * T
        return Gf.Vec3f(p[0], p[1], p[2])

    def axle_front(self):
        """Get the position of the front axle."""
        return self.axle_position(Axle.FRONT)

    def axle_rear(self):
        """Get the position of the rear axle."""
        return self.axle_position(Axle.REAR)

    def axle_position(self, axle_type):
        """Get the position of the axle based on the axle_type (front or rear)."""
        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(self._vehicle())
        if axle_type == Axle.FRONT:
            wheel_fl = self._wheel_prims[Wheel.FRONT_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_fr = self._wheel_prims[Wheel.FRONT_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_fl[self.up_axis_index] = 0.0
            wheel_fr[self.up_axis_index] = 0.0
            wheel_fl = Gf.Vec4f(wheel_fl[0], wheel_fl[1], wheel_fl[2], 1.0) * T
            wheel_fr = Gf.Vec4f(wheel_fr[0], wheel_fr[1], wheel_fr[2], 1.0) * T

            wheel_fl = Gf.Vec3f(wheel_fl[0], wheel_fl[1], wheel_fl[2])
            wheel_fr = Gf.Vec3f(wheel_fr[0], wheel_fr[1], wheel_fr[2])

            return (wheel_fl + wheel_fr) / 2

        if axle_type == Axle.REAR:
            wheel_rl = self._wheel_prims[Wheel.REAR_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_rr = self._wheel_prims[Wheel.REAR_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_rl[self.up_axis_index] = 0.0
            wheel_rr[self.up_axis_index] = 0.0
            wheel_rl = Gf.Vec4f(wheel_rl[0], wheel_rl[1], wheel_rl[2], 1.0) * T
            wheel_rr = Gf.Vec4f(wheel_rr[0], wheel_rr[1], wheel_rr[2], 1.0) * T

            wheel_rl = Gf.Vec3f(wheel_rl[0], wheel_rl[1], wheel_rl[2])
            wheel_rr = Gf.Vec3f(wheel_rr[0], wheel_rr[1], wheel_rr[2])

            return (wheel_rl + wheel_rr) / 2

        return None

    def _wheel_pos(self, wheel_type):
        R = self.rotation_matrix()
        wheel_pos = self._wheel_prims[wheel_type].GetAttribute("xformOp:translate").Get()
        wheel_pos = Gf.Vec4f(wheel_pos[0], wheel_pos[1], wheel_pos[2], 1.0) * R
        return Gf.Vec3f(wheel_pos[0], wheel_pos[1], wheel_pos[2]) + self.curr_position()

    def wheel_pos_front_left(self):
        """Get the position of the front left wheel."""
        return self._wheel_pos(Wheel.FRONT_LEFT)

    def wheel_pos_front_right(self):
        """Get the position of the front right wheel."""
        return self._wheel_pos(Wheel.FRONT_RIGHT)

    def wheel_pos_rear_left(self):
        """Get the position of the rear left wheel."""
        return self._wheel_pos(Wheel.REAR_LEFT)

    def wheel_pos_rear_right(self):
        """Get the position of the rear right wheel."""
        return self._wheel_pos(Wheel.REAR_RIGHT)

    def rotation_matrix(self):
        """
        Produces vehicle's local-to-world rotation transform.
        """
        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(self._vehicle())
        return Gf.Matrix4d(T.ExtractRotationMatrix(), Gf.Vec3d())

    def forward(self):
        """Produces vehicle's local-to-world forward vector."""
        R = self.rotation_matrix()
        f = self._forward_local()
        return Gf.Vec4f(f[0], f[1], f[2], 1.0) * R

    def up(self):
        """Produces vehicle's local-to-world up vector."""
        R = self.rotation_matrix()
        u = self._up_local()
        return Gf.Vec4f(u[0], u[1], u[2], 1.0) * R

    def _forward_local(self):
        return Gf.Vec3f(0.0, 0.0, 1.0)

    def _up_local(self):
        vec = [0.0, 0.0, 0.0]
        vec[self.up_axis_index] = 1.0
        return Gf.Vec3f(*vec)

    def _vehicle(self):
        return self._stage.GetPrimAtPath(self._path)

    def is_close_to(self, point, lookahead_distance):
        """Check if the vehicle is close to a given point."""
        assert point is not None, "[Vehicle] Point is None"
        curr_vehicle_pos = self.curr_position()
        assert curr_vehicle_pos is not None, "[Vehicle] Current position is None"

        distance = np.linalg.norm(curr_vehicle_pos - point)
        return distance, distance < lookahead_distance
