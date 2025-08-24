"""Utility functions."""

from pathlib import PurePath
from typing import Iterable, Optional

import numpy as np
import omni.usd
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics


class UpAxisHelper:
    """
    Static utility class for accessing up-axis metadata from the USD stage
    and performing up-axis-aware vector operations.
    """

    _initialized = False
    _up_axis_token = None
    _up_axis_index: int = -1
    _flat_indices: Optional[Iterable[int]] = []

    @staticmethod
    def _initialize():
        if UpAxisHelper._initialized:
            return

        stage = omni.usd.get_context().get_stage()
        if not stage:
            raise RuntimeError("[UpAxisHelper] Failed to retrieve USD stage context.")

        UpAxisHelper._up_axis_token = UsdGeom.GetStageUpAxis(stage).upper()
        UpAxisHelper._up_axis_index = {"X": 0, "Y": 1, "Z": 2}[
            UpAxisHelper._up_axis_token
        ]
        UpAxisHelper._flat_indices = [
            i for i in range(3) if i != UpAxisHelper._up_axis_index
        ]

        UpAxisHelper._initialized = True

    @staticmethod
    def get_up_axis_index() -> int:
        """Returns the index (0=X, 1=Y, 2=Z) of the stage's up-axis."""
        UpAxisHelper._initialize()
        return UpAxisHelper._up_axis_index

    @staticmethod
    def get_flat_indices():
        """Returns the two indices that are not the up-axis."""
        UpAxisHelper._initialize()
        return UpAxisHelper._flat_indices

    @staticmethod
    def flatten(vec3):
        """
        Projects a 3D vector onto the ground plane (by removing the up-axis component).

        Args:
            vec3 (list | tuple | Gf.Vec3f): Input 3D vector.

        Returns:
            np.ndarray: 2D flattened vector.
        """
        UpAxisHelper._initialize()
        return np.array([vec3[i] for i in UpAxisHelper._flat_indices])

    @staticmethod
    def up_vector():
        """
        Returns a Gf.Vec3f unit vector along the up-axis (X, Y, or Z).
        """
        UpAxisHelper._initialize()
        vec = [0.0, 0.0, 0.0]
        vec[UpAxisHelper._up_axis_index] = 1.0
        return Gf.Vec3f(*vec)


class Utils:
    """Utility functions for creating meshes and handling USD stage operations."""

    @staticmethod
    def create_mesh_square_axis(stage, path, axis, half_size):
        """Create a square mesh aligned with the specified axis."""
        if axis == "X":
            points = [
                Gf.Vec3f(0.0, -half_size, -half_size),
                Gf.Vec3f(0.0, half_size, -half_size),
                Gf.Vec3f(0.0, half_size, half_size),
                Gf.Vec3f(0.0, -half_size, half_size),
            ]
            normals = [
                Gf.Vec3f(1, 0, 0),
                Gf.Vec3f(1, 0, 0),
                Gf.Vec3f(1, 0, 0),
                Gf.Vec3f(1, 0, 0),
            ]
            indices = [0, 1, 2, 3]
            vertex_counts = [4]

            return Utils.create_mesh(
                stage, path, points, normals, indices, vertex_counts
            )

        if axis == "Y":
            points = [
                Gf.Vec3f(-half_size, 0.0, -half_size),
                Gf.Vec3f(half_size, 0.0, -half_size),
                Gf.Vec3f(half_size, 0.0, half_size),
                Gf.Vec3f(-half_size, 0.0, half_size),
            ]
            normals = [
                Gf.Vec3f(0, 1, 0),
                Gf.Vec3f(0, 1, 0),
                Gf.Vec3f(0, 1, 0),
                Gf.Vec3f(0, 1, 0),
            ]
            indices = [0, 1, 2, 3]
            vertex_counts = [4]

            return Utils.create_mesh(
                stage, path, points, normals, indices, vertex_counts
            )

        points = [
            Gf.Vec3f(-half_size, -half_size, 0.0),
            Gf.Vec3f(half_size, -half_size, 0.0),
            Gf.Vec3f(half_size, half_size, 0.0),
            Gf.Vec3f(-half_size, half_size, 0.0),
        ]
        normals = [
            Gf.Vec3f(0, 0, 1),
            Gf.Vec3f(0, 0, 1),
            Gf.Vec3f(0, 0, 1),
            Gf.Vec3f(0, 0, 1),
        ]
        indices = [0, 1, 2, 3]
        vertex_counts = [4]

        mesh = Utils.create_mesh(stage, path, points, normals, indices, vertex_counts)

        # text coord
        texCoords = mesh.CreatePrimvar(
            "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying
        )
        texCoords.Set([(0, 0), (1, 0), (1, 1), (0, 1)])

        return mesh

    @staticmethod
    def create_mesh(stage, path, points, normals, indices, vertex_counts):
        """Create a mesh with the given points, normals, indices, and vertex counts."""
        mesh = UsdGeom.Mesh.Define(stage, path)
        # Fill in VtArrays
        mesh.CreateFaceVertexCountsAttr().Set(vertex_counts)
        mesh.CreateFaceVertexIndicesAttr().Set(indices)
        mesh.CreatePointsAttr().Set(points)
        mesh.CreateDoubleSidedAttr().Set(False)
        mesh.CreateNormalsAttr().Set(normals)
        return mesh

    @staticmethod
    def add_ground_plane(
        stage,
        plane_path,
        axis,
        size=3000.0,
        position=Gf.Vec3f(0.0),
        color=Gf.Vec3f(0.2, 0.25, 0.25),
    ):
        """Create a ground plane in the USD stage."""
        # Parent xform (no transforms applied unless we hit fallback path)
        plane_path = omni.usd.get_stage_next_free_path(stage, plane_path, True)
        UsdGeom.Xform.Define(stage, plane_path)

        col_plane_path = plane_path + "/CollisionPlane"

        # Preferred: use PhysX helper utility if available
        try:
            from omni.physx.scripts import physicsUtils  # type: ignore

            physicsUtils.add_ground_plane(
                stage=stage,
                planePath=col_plane_path,
                axis=axis,
                size=float(size),
                position=position,
                color=color,
            )
        except Exception:
            # Fallback: define a USD Physics plane and apply transforms/color via a mesh if desired
            plane_xform = UsdGeom.Xform.Define(stage, plane_path)
            plane_xform.AddTranslateOp().Set(position)
            plane_xform.AddOrientOp().Set(Gf.Quatf(1.0))
            plane_xform.AddScaleOp().Set(Gf.Vec3f(1.0))

            # Simple visual mesh (optional) to see the plane
            geom_plane_path = plane_path + "/CollisionMesh"
            entity_plane = Utils.create_mesh_square_axis(
                stage, geom_plane_path, axis, size
            )
            entity_plane.CreateDisplayColorAttr().Set([color])

            # Define physics plane (USD schema)
            plane = UsdPhysics.Plane.Define(stage, col_plane_path)
            # Map axis string ("X"/"Y"/"Z") to enum when available
            axis_upper = str(axis).upper()
            axis_enum = getattr(getattr(UsdPhysics, "Axis", object), axis_upper, None)
            attr = plane.CreateAxisAttr()
            if axis_enum is not None:
                attr.Set(axis_enum)
            else:
                attr.Set(axis_upper)

        return plane_path

    @staticmethod
    def get_stage_next_free_path(stage: Usd.Stage, path: str) -> str:
        """Get the next free path in the stage by appending a numeric suffix if needed."""
        # Mirror omni.usd.get_stage_next_free_path behavior with prepend_default_prim=False
        return omni.usd.get_stage_next_free_path(stage, path, False)

    @staticmethod
    def split_path_to_list(path: str) -> tuple[str, ...]:
        """Split a USD path into its component parts."""
        return PurePath(path).parts[1:]

    @staticmethod
    def ensure_xform_hierarchy_from_prim_path(
        stage: Usd.Stage, prim_path: str | Sdf.Path
    ) -> UsdGeom.Xform:
        """
        Ensures that the parent path of the given prim_path exists in the stage.
        Expects Xform-only; raises ValueError if any prim exists at the path that is not an Xform.
        Returns the parent xform prim (as UsdGeom.Xform).
        """
        if isinstance(prim_path, Sdf.Path):
            prim_path = str(prim_path)

        ordered_prim_names = Utils.split_path_to_list(prim_path)
        if not ordered_prim_names:
            raise ValueError(f"Prim path '{prim_path}' has no parent path.")

        return Utils.ensure_xform_hierarchy(stage, ordered_prim_names)

    @staticmethod
    def ensure_xform_hierarchy(
        stage: Usd.Stage, ordered_prim_names: tuple[str, ...]
    ) -> UsdGeom.Xform:
        """
        Ensures that the full xform hierarchy /a/b/.../{last} exists in the stage.
        Expects Xform-only; raises ValueError if any prim exists at the path that is not an Xform.
        Returns the final xform prim (as UsdGeom.Xform).
        """
        # perform sanity checks for the input, that ordered_prim_names is a tuple
        if not isinstance(ordered_prim_names, tuple):
            raise ValueError(
                f"Input ordered prim names must be a tuple, got {type(ordered_prim_names)}"
            )

        if not ordered_prim_names:
            raise ValueError("Input ordered prim names cannot be empty")

        curr_prim_path = Sdf.Path.absoluteRootPath
        for next_path in ordered_prim_names:
            if not Sdf.Path.IsValidIdentifier(next_path):
                raise ValueError(f"Invalid USD identifier: {next_path}")

            curr_prim_path = curr_prim_path.AppendChild(next_path)
            curr_prim = stage.GetPrimAtPath(curr_prim_path)
            if curr_prim and curr_prim.IsValid() and not curr_prim.IsA(UsdGeom.Xform):
                raise ValueError(
                    f"Conflict at {curr_prim_path}: existing prim is '{curr_prim.GetTypeName()}', expected 'Xform'."
                )

        curr_prim_path = Sdf.Path.absoluteRootPath
        xform = None
        for next_path in ordered_prim_names:
            curr_prim_path = curr_prim_path.AppendChild(next_path)
            xform = UsdGeom.Xform.Define(stage, curr_prim_path)

        return xform
