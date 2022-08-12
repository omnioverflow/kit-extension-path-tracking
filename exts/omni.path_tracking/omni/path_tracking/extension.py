import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf
from omni.physx.scripts import utils

from .debug_renderer import *
# from . import VehicleFactory
# from . import Vehicle
from .stepper import *
from .path_tracking import *
from .ui import *

from enum import IntEnum
import asyncio, random, re
import numpy as np

# ==============================================================================
# Desitanation
# ==============================================================================
class Destination():
    def __init__(self):
        res, path = omni.kit.commands.execute("CreateMeshPrimCommand", prim_type="Sphere")
        if res:
            stage = omni.usd.get_context().get_stage()
            self._prim = stage.GetPrimAtPath(path)
            
            # xform = UsdGeom.Xformable(self._prim)
            # transform = xform.AddTransformOp()
            x = random.uniform(5000.0, 10000.0)
            z = random.uniform(5000.0, 10000.0)
            # transform.Set(Gf.Matrix4d().SetTranslateOnly(Gf.Vec3d(x, 0.0, z)))

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
    def __init__(self, vehicle_prim):
        self._prim = vehicle_prim
        self._path = self._prim.GetPath()
        self._steer_delta = 0.01
        stage = omni.usd.get_context().get_stage()
        self._wheel_prims = {
            Wheel.FRONT_LEFT : 
                stage.GetPrimAtPath(f"{self._path}/LeftWheel1References/Wheel_FL"),
            Wheel.FRONT_RIGHT :
                stage.GetPrimAtPath(f"{self._path}/RightWheel1References/Wheel_FR"),
            Wheel.REAR_LEFT :
                stage.GetPrimAtPath(f"{self._path}/LeftWheel2References/WHeel_RL"),
            Wheel.REAR_RIGHT :
                stage.GetPrimAtPath(f"{self._path}/RightWheel2References/Wheel_RR")
        }

    def steer_left(self, value):
        if value < 0.0 or value > 1.0:
            breakpt = 1
        self._prim.GetAttribute("physxVehicleController:steerLeft").Set(value)
        self._prim.GetAttribute("physxVehicleController:steerRight").Set(0.0)

    def steer_right(self, value):
        if value < 0.0 or value > 1.0:
            breakpt = 1
        self._prim.GetAttribute("physxVehicleController:steerLeft").Set(0.0)
        self._prim.GetAttribute("physxVehicleController:steerRight").Set(value)
    
    def steer_left_tmp(self, value):
        left_value = self._prim.GetAttribute("physxVehicleController:steerLeft").Get()
        right_value = self._prim.GetAttribute("physxVehicleController:steerRight").Get()

        if (right_value > 0.0):
            if (value < 0.3):
                right_value = right_value - 2 * self._steer_delta
            else:
                right_value = right_value - 5 * self._steer_delta
            right_value = max(0.0, right_value)
            self._prim.GetAttribute("physxVehicleController:steerRight").Set(right_value)
        else:
            left_value = left_value + self._steer_delta
            left_value = min(1.0, left_value)
            self._prim.GetAttribute("physxVehicleController:steerLeft").Set(left_value)

    def steer_right_tmp(self, value):
        left_value = self._prim.GetAttribute("physxVehicleController:steerLeft").Get()
        right_value = self._prim.GetAttribute("physxVehicleController:steerRight").Get()

        if (left_value > 0.0):
            if (value < 0.3):
                left_value = left_value - 2 * self._steer_delta
            else:
                left_value = left_value - 5 * self._steer_delta
            left_value = max(0.0, left_value)
            self._prim.GetAttribute("physxVehicleController:steerLeft").Set(left_value)
        else:
            right_value = right_value + self._steer_delta
            right_value = min(1.0, right_value)
            self._prim.GetAttribute("physxVehicleController:steerRight").Set(right_value)

    def accelerate(self, value):
        if (value < 0.0 or value > 1.0):
            breakpt = 1
        self._prim.GetAttribute("physxVehicleController:accelerator").Set(value)

    def brake(self, value):
        self._prim.GetAttribute("physxVehicleController:brake").Set(value)

    def get_velocity(self):
        return self._prim.GetAttribute("physics:velocity").Get()  

    def curr_position(self):
        return self._prim.GetAttribute("xformOp:translate").Get()

    def axle_front(self):
        return self.axle_position(Axle.FRONT)

    def axle_rear(self):
        return self.axle_position(Axle.REAR)

    def axle_position(self, type):
        R = self.rotation_matrix()
        curr_pos = self.curr_position()
        if type == Axle.FRONT:
            wheel_fl = self._wheel_prims[Wheel.FRONT_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_fr = self._wheel_prims[Wheel.FRONT_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_fl = Gf.Vec4f(wheel_fl[0], wheel_fl[1], wheel_fl[2], 1.0) * R
            wheel_fr = Gf.Vec4f(wheel_fr[0], wheel_fr[1], wheel_fr[2], 1.0) * R
            wheel_fl = Gf.Vec3f(wheel_fl[0], wheel_fl[1], wheel_fl[2]) + curr_pos
            wheel_fr = Gf.Vec3f(wheel_fr[0], wheel_fr[1], wheel_fr[2]) + curr_pos
            return (wheel_fl + wheel_fr) / 2
        elif type == Axle.REAR:
            wheel_rl = self._wheel_prims[Wheel.REAR_LEFT].GetAttribute("xformOp:translate").Get()
            wheel_rr = self._wheel_prims[Wheel.REAR_RIGHT].GetAttribute("xformOp:translate").Get()
            wheel_rl = Gf.Vec4f(wheel_rl[0], wheel_rl[1], wheel_rl[2], 1.0) * R
            wheel_rr = Gf.Vec4f(wheel_rr[0], wheel_rr[1], wheel_rr[2], 1.0) * R
            wheel_rl = Gf.Vec3f(wheel_rl[0], wheel_rl[1], wheel_rl[2]) + curr_pos
            wheel_rr = Gf.Vec3f(wheel_rr[0], wheel_rr[1], wheel_rr[2]) + curr_pos
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
        attr_rotate = self._prim.GetAttribute("xformOp:orient").Get()
        return Gf.Matrix4d().SetRotate(attr_rotate)

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

# ==============================================================================
# SimpleScenario
# ==============================================================================
class SimpleScenario(Scenario):
    def __init__(self, viewport_ui, meters_per_unit, vehicle_path, destination=True):
        self.METERS_PER_UNIT = meters_per_unit
        self._viewport_ui = viewport_ui
        secondsToRun = 10000.0
        timeStepsPerSecond = 25
        super().__init__(secondsToRun, 1.0 / timeStepsPerSecond)

        self._stage = omni.usd.get_context().get_stage()
        self._vehicle = Vehicle(self._stage.GetPrimAtPath(vehicle_path))
        self._dest = Destination() if destination else None
        self._debug_render = DebugRenderer()
        self._motion_controller = PurePursuitPathTracker(math.pi / 4)
        # Emissive materials
        self._emissive_red_light_path = "/World/forklift/Looks/RedLightsOmniPBR"
        self._emissive_mtl_path = "/World/forklift/Looks/OrangeLightsOmniPBR"
        self._emissive_pointer = 0
        self._emissive_pointer_half = 30
        self._emissive_pointer_max = self._emissive_pointer_half * 2 - 1
        self._emissive = np.arange(0.0, 10000.0, 10000.0/self._emissive_pointer_half)
        self._emissive = np.concatenate((self._emissive, np.repeat([0], self._emissive_pointer_half)))
        self._emissive_rgb = [1.0, 0.5, 0.0]
        self._emissive_first_call = True
    
    def on_start(self):
        print("[SimpleScenario] on_start")
        self._vehicle.accelerate(1.0)

    def on_end(self):
        print("[SimpleScenarion] on_end")

    def _update_mtl_red(self, light_is_on):
        mtl_prim = self._stage.GetPrimAtPath(self._emissive_red_light_path)
        omni.usd.create_material_input(mtl_prim,
            "emissive_color",
            Gf.Vec3f(1, 0, 0),
            Sdf.ValueTypeNames.Color3f)
        intensity = 5000.0 if light_is_on else 0.0
        omni.usd.create_material_input(
            mtl_prim,
            "emissive_intensity",
            intensity,
            Sdf.ValueTypeNames.Float
        )

    def _update_mtl(self):
        # Update materials
        emissive_mtl_prim = self._stage.GetPrimAtPath(self._emissive_mtl_path)

        if (self._emissive_first_call):
            omni.usd.create_material_input(emissive_mtl_prim,
                "enable_emission",
                True,
                Sdf.ValueTypeNames.Bool)
            omni.usd.create_material_input(
                    emissive_mtl_prim,
                    "emissive_color",
                    Gf.Vec3f(self._emissive_rgb[0], self._emissive_rgb[1], self._emissive_rgb[2]),
                    Sdf.ValueTypeNames.Color3f,
                )
            self._emissive_first_call = False

        omni.usd.create_material_input(emissive_mtl_prim,
            "emissive_intensity",
            self._emissive[self._emissive_pointer],
            Sdf.ValueTypeNames.Float)
        self._emissive_pointer = self._emissive_pointer + 1
        if (self._emissive_pointer > self._emissive_pointer_max):
            self._emissive_pointer = 0
    
    def _vehicle_is_close_to(self, point):
        if not point:
            raise Exception("point is None")
        curr_vehicle_pos = self._vehicle.curr_position()
        if not curr_vehicle_pos:
            raise Exception("curr_vehicle_pos is None")
        distance = np.linalg.norm(curr_vehicle_pos - point)
        return tuple([distance, distance < 400.0])

    def _process(self, forward, up, dest_position, distance=None, is_close_to_dest=False):
        if (distance is None):
            distance, is_close_to_dest = self._vehicle_is_close_to(dest_position)
        curr_vehicle_pos = self._vehicle.curr_position()

        # self._debug_render.update_vehicle(self._vehicle)
        # self._debug_render.update_path_to_dest(curr_vehicle_pos, dest_position)

        # Project onto xz
        curr_vehicle_pos[1] = 0.0
        forward[1] = 0.0
        dest_position[1] = 0.0

        velocity = self._vehicle.get_velocity()
        speed = self._vehicle_speed(velocity)
        axle_front = Gf.Vec3f(self._vehicle.axle_position(Axle.FRONT))
        axle_front[1] = 0.0
        axle_rear = Gf.Vec3f(self._vehicle.axle_position(Axle.REAR))
        axle_rear[1] = 0.0

        self._debug_render.update_path_tracking(axle_front, axle_rear, forward, dest_position)

        steer_angle = self._motion_controller.on_step(
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
        if steer_angle > 0.3 and speed > 5.0:
            self._vehicle.brake(1.0)
            self._vehicle.accelerate(0.0)
            self._update_mtl_red(light_is_on=True)
        else:
            self._vehicle.brake(0.0)
            self._vehicle.accelerate(0.7)

        # Update mtl
        self._update_mtl()

        # Update viewport stats
        if self._viewport_ui:
            self._viewport_ui.set_steer_angle(steer_angle)
            self._viewport_ui.set_vehicle_velocity(velocity)
            self._viewport_ui.set_vehicle_speed(speed)
            self._viewport_ui.set_distance_label(distance * self.METERS_PER_UNIT)

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
        speed = math.sqrt(speed) * self.METERS_PER_UNIT
        return speed

    def set_meters_per_unit(self, value):
        self.METERS_PER_UNIT = value

    def teardown(self):
        print("[SimpleScenario] teardown")
        super().abort()
        self._dest.teardown()
        self._dest = None
        self._stage = None
        self._vehicle = None
        self._debug_render = None
        self._motion_controller = None

    def enable_debug(self, flag):
        self._debug_render.enable(flag)

        # camera intrinsic
        # real trajectory (GT trajectory) ground-truth trajectory
        # validation

# ==============================================================================
# Trajectory
# ==============================================================================
class Trajectory():
    def __init__(self, prim_path):
        stage = omni.usd.get_context().get_stage()
        basic_curves = UsdGeom.BasisCurves.Get(stage, prim_path)
        if (basic_curves and basic_curves is not None):
            curve_prim = stage.GetPrimAtPath(prim_path)
            self._points = basic_curves.GetPointsAttr().Get()
            translation_vec = curve_prim.GetAttribute("xformOp:translate").Get()
            rotate = curve_prim.GetAttribute("xformOp:rotateXYZ").Get()
    
            Rx = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.XAxis(), rotate[0]))
            Ry = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.YAxis(), rotate[1]))
            Rz = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.ZAxis(), rotate[2]))
            print(f"Rx {Rx}")
            print(f"Ry {Ry}")
            print(f"Rz {Rz}")
            R = Rx * Ry * Rz
            print(f"R {R}")
            T = Gf.Matrix4d().SetTranslate(translation_vec)
            self._num_points = len(self._points)
            for i in range(self._num_points):
                print(f"translation_vec {translation_vec}")
                print(f"translation_vec type {type(translation_vec)}")
                print(f"before {i}: {self._points[i]}")
                # self._points[i] = self._points[i] * R + Gf.Vec3f(translation_vec)
                p = Gf.Vec4d(self._points[i][0], self._points[i][1], self._points[i][2], 1.0)
                p_ = p * R * T
                self._points[i] = Gf.Vec3f(p_[0], p_[1], p_[2])
                # self._points[i] = self._points[i] * R * T
                print(f"after {i}: {self._points[i]}")
        else:
            self._points = None
            self._num_points = 0
        self._pointer = 0

    def point(self):
        return self._points[self._pointer] if self._pointer < len(self._points) else None

    def next_point(self):

        if (self._pointer < self._num_points):
            self._pointer = self._pointer + 1
            return self.point()
        return None

    def reset(self):
        self._pointer = 0

    def draw(self):
        draw_interface = get_debug_draw_interface()
        for i in range(len(self._points) - 1):
            p0 = self._points[i]
            p1 = self._points[i+1]
            draw_interface.draw_line(
                carb.Float3(p0[0], p0[1], p0[2]),
                0xFF000000, 5,
                carb.Float3(p1[0], p1[1], p1[2]),
                0xFF000000, 5,
            )


# ==============================================================================
# TrajectoryScenario
# ==============================================================================
class TrajectoryScenario(SimpleScenario):
    def __init__(self, viewport_ui, meters_per_unit, vehicle_path, trajectory_prim_path):
        super().__init__(viewport_ui, meters_per_unit, vehicle_path, destination=False)
        self._dest = None
        self._trajectory_prim_path = trajectory_prim_path
        self._trajectory = Trajectory(trajectory_prim_path)
        self._stopped = False
        self.draw_track = False

    def on_step(self, deltaTime, totalTime):
        forward = self._vehicle.forward()
        up = self._vehicle.up()
        
        if self._trajectory and self.draw_track:
            self._trajectory.draw()

        dest_position = self._trajectory.point()
        # Run vehicle control unless reached the destination (i.e. dest_position is None)
        if dest_position:
            distance, is_close_to_dest = self._vehicle_is_close_to(dest_position)
            if (is_close_to_dest):
                dest_position = self._trajectory.next_point()
                distance, is_close_to_dest = self._vehicle_is_close_to(dest_position)
            if dest_position:
                    self._process(forward, up, dest_position, distance, is_close_to_dest)
            else:
                self._full_stop()
        elif not self._stopped:
            self._stopped = True
            self._full_stop()

    def on_end(self):
        print("[TrajectoryScenario] on_end")
        self._trajectory.reset()

    def teardown(self):
        print(f"[TrajectoryScenario] teardown {super}")
        super().teardown()

    def recompute_trajectory(self):
        self._trajectory = Trajectory(self._trajectory_prim_path)

    def reset(self):
        self._stopped = False

# ==============================================================================
# VehicleMotionPlanningExtension
# ==============================================================================
class VehicleMotionPlanningExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[lifecycle] **** Extension startup")

        self._ext_id = ext_id
        self.setup()
        self.build_ui()

        self._vehicle_paths = []
        self._trajectory_paths = []
        self._scenarios = []
        self._scenario_managers = []
        self._prepare_scene()

    def on_shutdown(self):
        print("[lifecycle] **** Extension shutdown")
        for manager in self._scenario_managers:
            manager.stop_scenario()
        self._window = None
        self._scenario_managers = []
        self._scenarios = []
        self._viewport_ui.teardown()
        self._viewport_ui = None

    def setup(self):
        self.METERS_PER_UNIT = 0.01
        UsdGeom.SetStageMetersPerUnit(omni.usd.get_context().get_stage(), self.METERS_PER_UNIT)

    def _prepare_scene(self):
        # asyncio.ensure_future(omni.kit.app.get_app().next_update_async())
        stage = omni.usd.get_context().get_stage()
        # Traverse all prims in the stage starting at this path (root):
        # * Use simple name-based and type-based heuristic to find vehicles (forklifts)
        #   and trajectories
        # * Delete lights
        curr_prim = stage.GetPrimAtPath("/")
        to_be_deleted_paths = []
        for prim in Usd.PrimRange(curr_prim):
                prim_name = prim.GetName()
                # prim_type = prim.GetTypeName()
                if prim.IsA(UsdGeom.BasisCurves):
                    if (len(re.findall("BasisCurves", prim_name)) > 0):
                        self._trajectory_paths.append(prim.GetPath().pathString)
                elif prim.IsA(UsdGeom.Xform):
                    if (len(re.findall("forklift_sim", prim_name)) > 0):
                        self._vehicle_paths.append(prim.GetPath().pathString)
                elif (
                      prim.IsA(UsdLux.DistantLight) or 
                      prim.IsA(UsdLux.DomeLight) or
                      prim.IsA(UsdLux.SphereLight) or
                      prim.IsA(UsdLux.CylinderLight) or
                      prim.IsA(UsdLux.DiskLight)
                ):
                    to_be_deleted_paths.append(prim.GetPath().pathString)
        omni.kit.commands.execute("DeletePrimsCommand", paths=to_be_deleted_paths)

    def start_sim(self):
        for manager in self._scenario_managers:
            manager.run_scenario_force_play()

    def _next_free_vehicle_position(self, y=120.0, z=0.0):
        return ((len(self._vehicle_paths) - 1) * 400.0, y, z)

    def _on_click_start_scenario(self):
        print("[lifecycle] Start vehicle scenario")
        
        vehicle_count = len(self._vehicle_paths)
        trajectory_count = len(self._trajectory_paths)
        scenario_count = len(self._scenarios)
        assert(vehicle_count == trajectory_count)

        if scenario_count < vehicle_count:
            for i in range(scenario_count, vehicle_count):
                scenario = TrajectoryScenario(
                    self._viewport_ui, self.METERS_PER_UNIT, 
                    self._vehicle_paths[i] + "/WizardVehicle1/Vehicle",
                    self._trajectory_paths[i]
                )
                scenario.enable_debug(self._enable_debug_checkbox.model.get_value_as_bool())
                self._scenarios.append(scenario)
                scenario_manager = ScenarioManager(scenario)
                self._scenario_managers.append(scenario_manager)
        for scenario in self._scenarios:
            scenario.reset()
        ScenarioManager.play()

    def _on_click_load_forklift(self):
        print("[lifecycle] Load forklift from the existing USD file")
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        forklift_prim_path = "/forklift_sim"
        forklift_prim_path = omni.usd.get_stage_next_free_path(
            usd_context.get_stage(),
            forklift_prim_path, 
            True
        )
        forklift_usd_path = f"{ext_path}/data/forklift_v11.usd"
        res, err = omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=forklift_prim_path,
            asset_path=forklift_usd_path,
            usd_context=usd_context,
        )
        if (res):
            self._vehicle_paths.append(forklift_prim_path)
            vehicle = usd_context.get_stage().GetPrimAtPath(forklift_prim_path + "/WizardVehicle1/Vehicle")
            vehicle.GetAttribute("xformOp:translate").Set(self._next_free_vehicle_position())
        # usd_context.open_stage(forklift_path)
        # await usd_context.open_stage_async(forklift_path)
        # await omni.kit.app.get_app().next_update_async()

    def _on_click_load_ground_plane(self):
        print("[lifecycle] Load ground plane from the existing USD file")
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        ground_plane_prim_path = "/GroundPlane"
        ground_plane = usd_context.get_stage().GetPrimAtPath(ground_plane_prim_path)
        if (ground_plane and ground_plane is not None):
            return
        ground_plane_usd_path = f"{ext_path}/data/ground_plane.usd"
        res = omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=ground_plane_prim_path,
            asset_path=ground_plane_usd_path,
            usd_context=usd_context,
        )

    def _on_click_load_basic_curve(self):
        print("[lifecycle] Load basic curve from the existing USD file")
        usd_context = omni.usd.get_context()
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(self._ext_id)
        basic_curve_prim_path = "/BasisCurves"
        basic_curve_prim_path = omni.usd.get_stage_next_free_path(
            usd_context.get_stage(),
            basic_curve_prim_path, 
            True
        )
        basic_curve_usd_path = f"{ext_path}/data/curve_5.usd"
        res = omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=basic_curve_prim_path,
            asset_path=basic_curve_usd_path,
            usd_context=usd_context,
        )
        if (res):
            self._trajectory_paths.append(basic_curve_prim_path)
            curve = usd_context.get_stage().GetPrimAtPath(basic_curve_prim_path)
            curve.GetAttribute("visibility").Set(
                self._visibility_token(self._hide_paths_checkbox.model.as_bool)
            )
            curve.GetAttribute("xformOp:translate").Set(self._next_free_vehicle_position(y=1.0))

    def _on_click_track_selected(self):
        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if len(selected_paths) == 1:
            if len(self._trajectory_paths) > 0:
                self._trajectory_paths[0] = selected_paths[0]
            else:
                self._trajectory_paths.append(selected_paths[0])
            if len(self._scenarios) and len(self._scenario_managers):
                manager = self._scenario_managers[0]
                scenario = self._scenarios[0]
                scenario.recompute_trajectory()
                manager.set_scenario(scenario)
                
    def _on_click_compute_obstacles(self):
        pass

    def _on_click_recompute_trajectories(self):
        assert(len(self._scenarios) == len(self._scenario_managers))
        for i in range(len(self._scenario_managers)):
            scenario = self._scenarios[i]
            manager = self._scenario_managers[i]
            scenario.recompute_trajectory()
            manager.set_scenario(scenario)

    def _on_click_find_boxes_and_attach_physics(self):
        stage = omni.usd.get_context().get_stage()
        curr_prim = stage.GetPrimAtPath("/")
        for prim in Usd.PrimRange(curr_prim):
                prim_name = prim.GetName()
                if prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Mesh):
                    if len(re.findall("box", prim_name)) > 0:
                        utils.setRigidBody(prim, "convexHull", False)

    def _changed_enable_debug(self, model):
        flag = model.as_bool
        for scenario in self._scenarios:
            scenario.enable_debug(flag)

    def _visibility_token(self, flag):
        return "invisible" if flag else "inherited"

    def _changed_hide_paths(self, model):
        flag = model.as_bool
        stage = omni.usd.get_context().get_stage()
        for path in self._trajectory_paths:
            stage.GetPrimAtPath(path).GetAttribute("visibility").Set(
                self._visibility_token(flag)
            )

    def _changed_draw_track(self, model):
        for scenario in self._scenarios:
            scenario.draw_track = model.as_bool

    def build_ui(self):
        self._viewport_ui = None
        # self._viewport_ui = ViewportUI()
        # self._viewport_ui.build_viewport()
        
        self._window = ui.Window("Vehicle Path Planner", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                width = 64
                height = 16
                with ui.HStack(width=width, height=height):
                    ui.Label("Enable path planning: ")
                    self._path_planning_checkbox = ui.CheckBox()
                    # self._path_planning_checkbox.model.set_value(self._create_renderer)
                    # self._path_planning_checkbox.model.add_value_changed_fn(
                    #        lambda box: toggle_renderer(box)
                    # )
                    ui.Spacer(height=20)
                with ui.HStack(width=width, height=height):
                    ui.Label("Enable debug: ")
                    self._enable_debug_checkbox = ui.CheckBox()
                    self._enable_debug_checkbox.model.add_value_changed_fn(
                        self._changed_enable_debug
                    )
                    ui.Spacer(height=20)
                with ui.HStack(width=width, height=height):
                    ui.Label("Hide paths: ")
                    self._hide_paths_checkbox = ui.CheckBox()
                    self._hide_paths_checkbox.model.add_value_changed_fn(
                        self._changed_hide_paths
                    )
                    ui.Spacer(height=20)
                with ui.HStack(width=width, height=height):
                    ui.Label("Draw track: ")
                    self._draw_track_checkbox = ui.CheckBox()
                    self._draw_track_checkbox.model.add_value_changed_fn(
                        self._changed_draw_track
                    )
                    self._draw_track_checkbox.model.set_value(False)
                    ui.Spacer(height=20)

                ui.Button("Start Scenario", clicked_fn=self._on_click_start_scenario)
                ui.Button("Load forklift", clicked_fn=self._on_click_load_forklift)
                ui.Button("Load ground plane", clicked_fn=self._on_click_load_ground_plane)
                ui.Button("Load basic curve", clicked_fn=self._on_click_load_basic_curve)
                ui.Button("Track selected", clicked_fn=self._on_click_track_selected)
                ui.Button("Compute obstacles", clicked_fn=self._on_click_compute_obstacles)
                ui.Button("Recompute trajectories", clicked_fn=self._on_click_recompute_trajectories)
                ui.Button("Find boxes and attach physics", clicked_fn=self._on_click_find_boxes_and_attach_physics)
        # viewport = ui.Workspace.get_window("Viewport")
        # self._window.dock_in(viewport, ui.DockPosition.BOTTOM)
        self._window.deferred_dock_in("Property")
        # dock_in_window is deprecated unfortunatelly
        # self._window.dock_in_window("Viewport", ui.DockPosition.RIGHT, ratio=0.1)
