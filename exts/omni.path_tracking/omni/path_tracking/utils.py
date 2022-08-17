import omni.usd
from pxr import UsdGeom, Sdf, Gf, UsdPhysics, PhysxSchema

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