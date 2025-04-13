import numpy as np
import omni.usd
from pxr import Gf, PhysxSchema, Sdf, UsdGeom, UsdPhysics

# utils/up_axis.py



class UpAxisHelper:
    """
    Static utility class for accessing up-axis metadata from the USD stage
    and performing up-axis–aware vector operations.
    """

    _initialized = False
    _up_axis_token = None
    _up_axis_index: int = -1
    _flat_indices = None

    @staticmethod
    def _initialize():
        if UpAxisHelper._initialized:
            return

        stage = omni.usd.get_context().get_stage()
        if not stage:
            raise RuntimeError("[UpAxisHelper] Failed to retrieve USD stage context.")

        UpAxisHelper._up_axis_token = UsdGeom.GetStageUpAxis(stage).upper()
        UpAxisHelper._up_axis_index = {"X": 0, "Y": 1, "Z": 2}[UpAxisHelper._up_axis_token]
        UpAxisHelper._flat_indices = [i for i in range(3) if i != UpAxisHelper._up_axis_index]

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
    @staticmethod
    def create_mesh_square_axis(stage, path, axis, halfSize):
        if axis == "X":
            points = [
                Gf.Vec3f(0.0, -halfSize, -halfSize),
                Gf.Vec3f(0.0, halfSize, -halfSize),
                Gf.Vec3f(0.0, halfSize, halfSize),
                Gf.Vec3f(0.0, -halfSize, halfSize),
            ]
            normals = [Gf.Vec3f(1, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(1, 0, 0)]
            indices = [0, 1, 2, 3]
            vertexCounts = [4]

            # Create the mesh
            return Utils.create_mesh(stage, path, points, normals, indices, vertexCounts)
        elif axis == "Y":
            points = [
                Gf.Vec3f(-halfSize, 0.0, -halfSize),
                Gf.Vec3f(halfSize, 0.0, -halfSize),
                Gf.Vec3f(halfSize, 0.0, halfSize),
                Gf.Vec3f(-halfSize, 0.0, halfSize),
            ]
            normals = [Gf.Vec3f(0, 1, 0), Gf.Vec3f(0, 1, 0), Gf.Vec3f(0, 1, 0), Gf.Vec3f(0, 1, 0)]
            indices = [0, 1, 2, 3]
            vertexCounts = [4]

            # Create the mesh
            return Utils.create_mesh(stage, path, points, normals, indices, vertexCounts)

        points = [
            Gf.Vec3f(-halfSize, -halfSize, 0.0),
            Gf.Vec3f(halfSize, -halfSize, 0.0),
            Gf.Vec3f(halfSize, halfSize, 0.0),
            Gf.Vec3f(-halfSize, halfSize, 0.0),
        ]
        normals = [Gf.Vec3f(0, 0, 1), Gf.Vec3f(0, 0, 1), Gf.Vec3f(0, 0, 1), Gf.Vec3f(0, 0, 1)]
        indices = [0, 1, 2, 3]
        vertexCounts = [4]

        # Create the mesh
        mesh = Utils.create_mesh(stage, path, points, normals, indices, vertexCounts)

        # text coord
        texCoords = mesh.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
        texCoords.Set([(0, 0), (1, 0), (1, 1), (0, 1)])

        return mesh

    @staticmethod
    def create_mesh(stage, path, points, normals, indices, vertexCounts):
        mesh = UsdGeom.Mesh.Define(stage, path)
        # Fill in VtArrays
        mesh.CreateFaceVertexCountsAttr().Set(vertexCounts)
        mesh.CreateFaceVertexIndicesAttr().Set(indices)
        mesh.CreatePointsAttr().Set(points)
        mesh.CreateDoubleSidedAttr().Set(False)
        mesh.CreateNormalsAttr().Set(normals)
        return mesh

    @staticmethod
    def add_ground_plane(stage, planePath, axis,
                         size=3000.0, position=Gf.Vec3f(0.0), color=Gf.Vec3f(0.2, 0.25, 0.25)):
        # plane xform, so that we dont nest geom prims
        planePath = omni.usd.get_stage_next_free_path(stage, planePath, True)
        planeXform = UsdGeom.Xform.Define(stage, planePath)
        planeXform.AddTranslateOp().Set(position)
        planeXform.AddOrientOp().Set(Gf.Quatf(1.0))
        planeXform.AddScaleOp().Set(Gf.Vec3f(1.0))

        # (Graphics) Plane mesh
        geomPlanePath = planePath + "/CollisionMesh"
        entityPlane = Utils.create_mesh_square_axis(stage, geomPlanePath, axis, size)
        entityPlane.CreateDisplayColorAttr().Set([color])

        # (Collision) Plane
        colPlanePath = planePath + "/CollisionPlane"
        planeGeom = PhysxSchema.Plane.Define(stage, colPlanePath)
        planeGeom.CreatePurposeAttr().Set("guide")
        planeGeom.CreateAxisAttr().Set(axis)

        prim = stage.GetPrimAtPath(colPlanePath)
        UsdPhysics.CollisionAPI.Apply(prim)

        return planePath
