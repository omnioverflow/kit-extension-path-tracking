"""Trajectory helper for reading BasisCurves points from the USD stage."""

from typing import Optional

import omni.usd
from pxr import Gf, UsdGeom


class Trajectory:
    """
    A helper class to access coordinates of points that form a BasisCurve prim.
    """

    def __init__(self, prim_path, close_loop=True):
        self._points: list[Gf.Vec3f] = []
        self._points_cache: Optional[list[Gf.Vec3f]] = None

        stage = omni.usd.get_context().get_stage()
        basis_curves = UsdGeom.BasisCurves.Get(stage, prim_path)
        if basis_curves and basis_curves is not None:
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

    @property
    def close_loop(self) -> bool:
        """Whether the trajectory is closed (i.e., loops back to the start)."""
        return self._close_loop

    @close_loop.setter
    def close_loop(self, value: bool) -> None:
        self._close_loop = value

    def get_all_points(self) -> list:
        """
        Returns all trajectory points as a list of Gf.Vec3f.
        Uses internal cache for performance.
        """
        if self._points_cache is None:
            self._points_cache = list(self._points) if self._points else []
        return self._points_cache

    def point(self):
        """
        Returns current point.
        """
        return self._points[self._pointer] if self._pointer < len(self._points) else None

    def next_point(self):
        """
        Next point on the curve.
        """
        if self._pointer < self._num_points:
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
