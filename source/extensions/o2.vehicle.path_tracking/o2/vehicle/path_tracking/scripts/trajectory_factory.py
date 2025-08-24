"""TrajectoryFactory for creating and authoring trajectory curves in USD."""

import math
from typing import Iterable, List, Optional, Tuple

import numpy as np

# Optional dependency: 'cmap' is available in the Kit app runtime, but may be missing in bare test envs
try:
    from cmap import Colormap  # type: ignore
except Exception:  # pragma: no cover - fallback for test environments without cmap
    Colormap = None  # type: ignore

import omni.usd
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt


DEFAULT_CMAP_NAME = "RdYlGn_r"


def _to_gf_vec3f(v: Iterable[float]) -> Gf.Vec3f:
    x, y, z = list(v)[:3]
    return Gf.Vec3f(float(x), float(y), float(z))


def _apply_colormap_to_curve(
    curve: UsdGeom.BasisCurves,
    num_points: int,
    cmap_name: str,
    reverse: bool = False,
) -> None:
    """Apply per-vertex color gradient using cmap.Colormap if available."""
    if Colormap is None:
        # Silently skip coloring if the optional dependency isn't present (e.g., unit tests)
        return
    cm = Colormap(cmap_name)
    t = np.linspace(0.0, 1.0, num_points)
    if reverse:
        t = t[::-1]
    rgba = cm(t)  # shape (num_points, 4): RGBA float in [0,1]
    # convert to Gf.Vec3f, ignoring alpha
    colors = [Gf.Vec3f(*tuple(rgb[:3])) for rgb in rgba]
    pv = UsdGeom.Gprim(curve.GetPrim()).CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex)
    pv.Set(Vt.Vec3fArray(colors))


class TrajectoryFactory:
    """Static factory for authoring trajectory curves on a given USD stage."""

    # ---------- Geometry authoring ----------
    @staticmethod
    def circle_points(
        center: Tuple[float, float, float],
        radius: float,
        num_points: int,
        axis: UsdGeom.Tokens = UsdGeom.Tokens.z,
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
        axis: UsdGeom.Tokens = UsdGeom.Tokens.z,
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
        axis: UsdGeom.Tokens = UsdGeom.Tokens.z,
        periodic: bool = True,
        width: float = 0.05,        # e.g., "viridis", "inferno"
        reverse_cmap: bool = False,
        cmap: Optional[str] = DEFAULT_CMAP_NAME,
    ) -> UsdGeom.BasisCurves:
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

        if cmap:
            _apply_colormap_to_curve(curve, num_points, cmap, reverse_cmap)

        # Ensure /World remains default prim
        try:
            prefixes = prim_path.GetPrefixes()
            if prefixes and prefixes[0] == Sdf.Path("/World"):
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
    stage = omni.usd.get_context().get_stage()
    radius = 1000.0
    center = (-radius, 0, 0)
    TrajectoryFactory.create_linear_circle(
        stage=stage,
        prim_path="/World/ColoredCircle",
        center=center,
        radius=radius,
        num_points=128,
        axis=UsdGeom.Tokens.y,
        periodic=True,
        width=10.0,
        reverse_cmap=True,
        cmap=DEFAULT_CMAP_NAME,
    )
