import omni.usd
from enum import IntEnum
from pxr import Gf, Usd, UsdGeom, PhysxSchema

import numpy as np

# ==============================================================================
# Vehicle
# ==============================================================================
class Axle(IntEnum):
    FRONT = 0,
    REAR = 1
class Wheel(IntEnum):
    FRONT_LEFT = 0,
    FRONT_RIGHT = 1,
    REAR_LEFT = 2,
    REAR_RIGHT = 3

class Vehicle():
    """
    A wrapper created to help manipulating state of a vehicle prim and its
    dynamic properties, such as acceleration, desceleration, steering etc.
    """

    def __init__(self, vehicle_prim, max_steer_angle_radians, rear_steering=False):
        self._prim = vehicle_prim
        self._path = self._prim.GetPath()
        self._steer_delta = 0.01
        self._stage = omni.usd.get_context().get_stage()
        self._rear_stearing = rear_steering
        self._wheel_prims = {
            Wheel.FRONT_LEFT : 
                self._stage.GetPrimAtPath(f"{self._path}/LeftWheel1References"),
            Wheel.FRONT_RIGHT :
                self._stage.GetPrimAtPath(f"{self._path}/RightWheel1References"),
            Wheel.REAR_LEFT :
                self._stage.GetPrimAtPath(f"{self._path}/LeftWheel2References"),
            Wheel.REAR_RIGHT :
                self._stage.GetPrimAtPath(f"{self._path}/RightWheel2References")
        }
        steering_wheels = []
        if self._rear_stearing:
            steering_wheels = [Wheel.REAR_LEFT, Wheel.REAR_RIGHT]
        else:
            steering_wheels = [Wheel.FRONT_LEFT, Wheel.FRONT_RIGHT]

        for wheel_prim_key in steering_wheels:
            self._set_max_steer_angle(self._wheel_prims[wheel_prim_key], max_steer_angle_radians)

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
        if self._rear_stearing:
            self._steer_right_priv(value)
        else:
            self._steer_left_priv(value)

    def steer_right(self, value):
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
        self._vehicle().GetAttribute("physxVehicleController:accelerator").Set(value)

    def brake(self, value):
        self._prim.GetAttribute("physxVehicleController:brake").Set(value)

    def get_velocity(self):
        return self._prim.GetAttribute("physics:velocity").Get()

    def get_speed(self):
        return np.linalg.norm(self.get_velocity())

    def curr_position(self):
        prim = self._vehicle()
        
        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(prim)
        p = self._p * T
        return Gf.Vec3f(p[0], p[1], p[2])

    def axle_front(self):
        return self.axle_position(Axle.FRONT)

    def axle_rear(self):
        return self.axle_position(Axle.REAR)

    def axle_position(self, type):
        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(self._vehicle())
        if type == Axle.FRONT:
            wheel_fl = self._wheel_prims[Wheel.FRONT_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_fr = self._wheel_prims[Wheel.FRONT_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_fl[1]=0.0
            wheel_fr[1]=0.0
            wheel_fl = Gf.Vec4f(wheel_fl[0], wheel_fl[1], wheel_fl[2], 1.0) * T
            wheel_fr = Gf.Vec4f(wheel_fr[0], wheel_fr[1], wheel_fr[2], 1.0) * T

            wheel_fl = Gf.Vec3f(wheel_fl[0], wheel_fl[1], wheel_fl[2])
            wheel_fr = Gf.Vec3f(wheel_fr[0], wheel_fr[1], wheel_fr[2])

            return (wheel_fl + wheel_fr) / 2
        elif type == Axle.REAR:
            wheel_rl = self._wheel_prims[Wheel.REAR_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_rr = self._wheel_prims[Wheel.REAR_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_rl[1]=0.0
            wheel_rr[1]=0.0
            wheel_rl = Gf.Vec4f(wheel_rl[0], wheel_rl[1], wheel_rl[2], 1.0) * T
            wheel_rr = Gf.Vec4f(wheel_rr[0], wheel_rr[1], wheel_rr[2], 1.0) * T

            wheel_rl = Gf.Vec3f(wheel_rl[0], wheel_rl[1], wheel_rl[2])
            wheel_rr = Gf.Vec3f(wheel_rr[0], wheel_rr[1], wheel_rr[2])

            return (wheel_rl + wheel_rr) / 2
        else:
            return None

    def _wheel_pos(self, type):
        R = self.rotation_matrix()
        wheel_pos = self._wheel_prims[type].GetAttribute("xformOp:translate").Get()
        wheel_pos = Gf.Vec4f(wheel_pos[0], wheel_pos[1], wheel_pos[2], 1.0) * R
        return Gf.Vec3f(wheel_pos[0], wheel_pos[1], wheel_pos[2]) + self.curr_position()

    def wheel_pos_front_left(self):
        return self._wheel_pos(Wheel.FRONT_LEFT)
    
    def wheel_pos_front_right(self):
        return self._wheel_pos(Wheel.FRONT_RIGHT)

    def wheel_pos_rear_left(self):
        return self._wheel_pos(Wheel.REAR_LEFT)

    def wheel_pos_rear_right(self):
        return self._wheel_pos(Wheel.REAR_RIGHT)

    def rotation_matrix(self):
        """
        Produces vehicle's local-to-world rotation transform.
        """
        cache = UsdGeom.XformCache()
        T = cache.GetLocalToWorldTransform(self._vehicle())
        return Gf.Matrix4d(T.ExtractRotationMatrix(), Gf.Vec3d())

    def forward(self):
        R = self.rotation_matrix()
        f = self._forward_local()
        return Gf.Vec4f(f[0], f[1], f[2], 1.0) * R

    def up(self):
        R = self.rotation_matrix()
        u = self._up_local()
        return Gf.Vec4f(u[0], u[1], u[2], 1.0) * R

    def _forward_local(self):
        return Gf.Vec3f(0.0, 0.0, 1.0)

    def _up_local(self):
        return Gf.Vec3f(0.0, 1.0, 0.0)

    def _vehicle(self):
        return self._stage.GetPrimAtPath(self._path)

    def is_close_to(self, point, lookahead_distance):
        if not point:
            raise Exception("[Vehicle] Point is None")
        curr_vehicle_pos = self.curr_position()
        if not curr_vehicle_pos:
            raise Exception("[Vechicle] Current position is None")
        distance = np.linalg.norm(curr_vehicle_pos - point)
        return tuple([distance, distance < lookahead_distance])