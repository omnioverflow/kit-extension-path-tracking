"""Tests for utils.py."""

import omni.usd
import omni.kit.app
from omni.kit.test import AsyncTestCase
from pxr import UsdGeom

from ..scripts.utils import Utils


class TestUtils(AsyncTestCase):
    """Tests for utils.py."""

    async def setUp(self):
        """Set up a new empty stage for each test."""
        self._app = omni.kit.app.get_app()
        self._usd = omni.usd.get_context()
        await self._usd.new_stage_async()
        await self._app.next_update_async()
        self._stage = self._usd.get_stage()

    async def tearDown(self):
        """Close stage to ensure clean state for next tests."""
        await self._app.next_update_async()
        await self._usd.close_stage_async()
        await self._app.next_update_async()
        self._stage = None

    async def test_get_stage_next_free_path_unique_suffix_when_taken(self):
        """It should append a numeric suffix when the requested path is taken, and return the same path when free."""
        # Arrange: create a prim at /Foo
        UsdGeom.Xform.Define(self._stage, "/Foo")
        await self._app.next_update_async()

        p1 = Utils.get_stage_next_free_path(self._stage, "/Foo")

        # Assert: it should not return the taken path and should keep the base prefix
        self.assertNotEqual(p1, "/Foo")
        self.assertTrue(str(p1).startswith("/Foo"))

        # Create prim at the suggested unique path and request again
        UsdGeom.Xform.Define(self._stage, p1)
        await self._app.next_update_async()
        p2 = Utils.get_stage_next_free_path(self._stage, "/Foo")
        self.assertNotEqual(p2, "/Foo")
        self.assertNotEqual(p2, str(p1))
        self.assertTrue(str(p2).startswith("/Foo"))

        # Also verify that for a free path we get the same path back
        p_free = Utils.get_stage_next_free_path(self._stage, "/Bar")
        self.assertEqual(str(p_free), "/Bar")

    async def test_ensure_xform_hierarchy_creates_ancestors(self):
        """Test that ensure_xform_hierarchy creates missing ancestor paths as Xforms."""
        target = "/A/B/C/D"

        # Precondition: none of the ancestors exist
        for path in ["/A", "/A/B", "/A/B/C"]:
            prim = self._stage.GetPrimAtPath(path)
            self.assertFalse(prim.IsValid())

        Utils.ensure_xform_hierarchy_from_prim_path(self._stage, target)
        await self._app.next_update_async()

        # Assert: ancestors created as Xforms
        for path in ["/A", "/A/B", "/A/B/C"]:
            prim = self._stage.GetPrimAtPath(path)
            self.assertTrue(prim.IsValid(), f"Missing ancestor prim {path}")
            self.assertEqual(prim.GetTypeName(), "Xform")

        # Now we should be able to define the final prim without errors
        final_prim = UsdGeom.Xform.Define(self._stage, target)
        self.assertTrue(final_prim.GetPrim().IsValid())
