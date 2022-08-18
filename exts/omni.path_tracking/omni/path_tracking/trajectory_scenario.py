import carb
import omni.usd
from omni.debugdraw import get_debug_draw_interface
from pxr import Gf, UsdGeom
from .simple_scenario import SimpleScenario

# ==============================================================================
# 
# Trajectory
# 
# ==============================================================================
class Trajectory():
    """
    A helper class to access coordinates of points that form a BasisCurve prim.
    """
    def __init__(self, prim_path):
        stage = omni.usd.get_context().get_stage()
        basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)
        if (basis_curves and basis_curves is not None):
            curve_prim = stage.GetPrimAtPath(prim_path)
            self._points = basis_curves.GetPointsAttr().Get()
            translation_vec = curve_prim.GetAttribute("xformOp:translate").Get()
            rotate = curve_prim.GetAttribute("xformOp:rotateXYZ").Get()
    
            Rx = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.XAxis(), rotate[0]))
            Ry = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.YAxis(), rotate[1]))
            Rz = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d.ZAxis(), rotate[2]))
            carb.log_info(f"Rx {Rx}")
            carb.log_info(f"Ry {Ry}")
            carb.log_info(f"Rz {Rz}")
            R = Rx * Ry * Rz
            carb.log_info(f"R {R}")
            T = Gf.Matrix4d().SetTranslate(translation_vec)
            self._num_points = len(self._points)
            for i in range(self._num_points):
                carb.log_info(f"translation_vec {translation_vec}")
                carb.log_info(f"translation_vec type {type(translation_vec)}")
                carb.log_info(f"before {i}: {self._points[i]}")
                
                p = Gf.Vec4d(self._points[i][0], self._points[i][1], self._points[i][2], 1.0)
                p_ = p * R * T
                self._points[i] = Gf.Vec3f(p_[0], p_[1], p_[2])

                carb.log_info(f"after {i}: {self._points[i]}")
        else:
            self._points = None
            self._num_points = 0
        self._pointer = 0

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

    def draw(self):
        """
        Draw debug overlay with segments formed by consecutive point pairs.
        """
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
# 
# TrajectoryScenario
# 
# ==============================================================================
class TrajectoryScenario(SimpleScenario):
    """
    Scenario for vehicle path tracking.
    """

    def __init__(self, vehicle_path, trajectory_prim_path, meters_per_unit, viewport_ui=None):
        super().__init__(viewport_ui, meters_per_unit, vehicle_path, destination=False)
        self._dest = None
        self._trajectory_prim_path = trajectory_prim_path
        self._trajectory = Trajectory(trajectory_prim_path)
        self._stopped = False
        self.draw_track = False

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
            distance, is_close_to_dest = self._vehicle_is_close_to(dest_position, is_end_point)
            if (is_close_to_dest):
                dest_position = self._trajectory.next_point()                
            else:
                # Compute vehicle steering and acceleration
                self._process(forward, up, dest_position, distance, is_close_to_dest)
        else:
            self._stopped = True
            self._full_stop()            

    def on_end(self):
        self._trajectory.reset()

    def teardown(self):
        super().teardown()

    def recompute_trajectory(self):
        self._trajectory = Trajectory(self._trajectory_prim_path)

    def reset(self):
        self._stopped = False