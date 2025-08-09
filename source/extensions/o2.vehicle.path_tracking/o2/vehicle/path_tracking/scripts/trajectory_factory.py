from __future__ import annotations
import math
from typing import Iterable, List, Tuple, Optional

import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, Tf


def _to_gf_vec3f(v: Iterable[float]) -> Gf.Vec3f:
    x, y, z = list(v)[:3]
    return Gf.Vec3f(float(x), float(y), float(z))


class TrajectoryFactory:
    """Static factory for authoring trajectory curves on a given USD stage."""

    # ---------- Geometry authoring ----------
    @staticmethod
    def circle_points(
        center: Tuple[float, float, float],
        radius: float,
        num_points: int,
        axis: Tf.Token = UsdGeom.Tokens.z,
    ) -> List[Gf.Vec3f]:
        """
        Sample points on a circle in the plane perpendicular to the given axis (UsdGeom.Tokens.x/y/z).
        - center: (x, y, z)
        - radius: circle radius
        - num_points: number of points to sample (>= 3)
        - axis: UsdGeom.Tokens.x, .y, or .z (normal to the plane)
        """
        if num_points < 3:
            raise ValueError("num_points must be >= 3")
        center_v = _to_gf_vec3f(center)
        axis_token = str(axis).lower()
        points: List[Gf.Vec3f] = []
        for i in range(num_points):
            t = (i / float(num_points)) * 2.0 * math.pi
            c = math.cos(t) * radius
            s = math.sin(t) * radius
            if axis_token == "z":
                # XY plane
                p = Gf.Vec3f(center_v[0] + c, center_v[1] + s, center_v[2])
            elif axis_token == "y":
                # XZ plane
                p = Gf.Vec3f(center_v[0] + c, center_v[1], center_v[2] + s)
            elif axis_token == "x":
                # YZ plane
                p = Gf.Vec3f(center_v[0], center_v[1] + c, center_v[2] + s)
            else:
                raise ValueError(f"Invalid axis '{axis_token}', must be UsdGeom.Tokens.x/y/z.")
            points.append(p)
        return points

    @staticmethod
    def create_circle(
        stage: Usd.Stage,
        prim_path: str | Sdf.Path,
        center: Tuple[float, float, float],
        radius: float,
        num_points: int,
        *,
        axis: Tf.Token = UsdGeom.Tokens.z,
        periodic: bool = True,
        width: float = 0.05,
    ) -> UsdGeom.BasisCurves:
        """Convenience alias to linear circle."""
        return TrajectoryFactory.create_linear_circle(
            stage=stage,
            prim_path=prim_path,
            center=center,
            radius=radius,
            num_points=num_points,
            axis=axis,
            periodic=periodic,
            width=width,
        )

    @staticmethod
    def create_linear_circle(
        stage: Usd.Stage,
        prim_path: str | Sdf.Path,
        center: Tuple[float, float, float],
        radius: float,
        num_points: int,
        *,
        axis: Tf.Token = UsdGeom.Tokens.z,
        periodic: bool = True,
        width: float = 0.05,
    ) -> UsdGeom.BasisCurves:
        """Create a linear BasisCurves circle at prim_path using sampled points."""
        if isinstance(prim_path, str):
            prim_path = Sdf.Path(prim_path)

        points = TrajectoryFactory.circle_points(center, radius, num_points, axis=axis)

        prim_path = omni.usd.get_stage_next_free_path(stage, prim_path, True)

        curve = UsdGeom.BasisCurves.Define(stage, prim_path)
        curve.CreateTypeAttr(UsdGeom.Tokens.linear)
        curve.CreateWrapAttr(UsdGeom.Tokens.periodic if periodic else UsdGeom.Tokens.nonperiodic)
        curve.CreatePointsAttr(points)
        curve.CreateCurveVertexCountsAttr([len(points)])
        curve.CreateWidthsAttr([width] * len(points))

        # Ensure /World is default prim if we author under it
        try:
            if prim_path.GetPrefixes() and prim_path.GetPrefixes()[0] == Sdf.Path("/World"):
                world = stage.GetPrimAtPath("/World")
                if world and not stage.GetDefaultPrim():
                    stage.SetDefaultPrim(world)
        except Exception:
            pass

        return curve

    @staticmethod
    def create_bezier_curve(
        stage: Usd.Stage,
        prim_path: str | Sdf.Path,
        control_points: Iterable[Iterable[float]],
        *,
        periodic: bool = False,
        width: float = 0.05,
    ) -> UsdGeom.BasisCurves:
        """Create a cubic Bezier BasisCurves from explicit control points (3*n+1)."""
        if isinstance(prim_path, str):
            prim_path = Sdf.Path(prim_path)

        pts = [_to_gf_vec3f(p) for p in control_points]
        curve = UsdGeom.BasisCurves.Define(stage, prim_path)
        curve.CreateTypeAttr(UsdGeom.Tokens.cubic)
        curve.CreateBasisAttr(UsdGeom.Tokens.bezier)
        curve.CreateWrapAttr(UsdGeom.Tokens.periodic if periodic else UsdGeom.Tokens.nonperiodic)
        curve.CreatePointsAttr(pts)
        curve.CreateCurveVertexCountsAttr([len(pts)])
        curve.CreateWidthsAttr([width] * len(pts))
        return curve


if __name__ == "__main__":
    # Example usage
    stage = omni.usd.get_context().get_stage()
    TrajectoryFactory.create_linear_circle(
        stage=stage,
        prim_path="/World/Circle",
        center=(0.0, 0.0, 0.0),
        radius=100.0,
        num_points=32,
        axis=UsdGeom.Tokens.z,
        periodic=True,
        width=0.5
    )