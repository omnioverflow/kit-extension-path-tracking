#
import omni
from pxr import Usd, UsdGeom
from omni.physx.scripts import utils

import re

def traverse_stage():
    stage = omni.usd.get_context().get_stage()
    # Traverse all prims in the stage starting at this path
    curr_prim = stage.GetPrimAtPath("/")
    for prim in Usd.PrimRange(curr_prim):
        if (prim.IsA(UsdGeom.Mesh)):
            print(prim.GetName())

def attach_physx(prim):
    utils.setRigidBody(prim, "convexHull", False)

def check_name(name, key):
    return len(re.findall(key, name)) > 0