"""Test the ExtensionModel class."""

import gc

import carb
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni.kit.test import AsyncTestCase

from ..scripts.logging import redirect_carb_logs_to_stdout
from ..scripts.model import ExtensionModel


async def cleanup_stage(stage):
    """Cleanup the USD stage: if a stage is already open from previous tests, close it cleanly first"""
    app = omni.kit.app.get_app()
    usd_context = omni.usd.get_context()
    try:
        if usd_context.get_stage() is not None:
            try:
                usd_context.get_selection().set_selected_prim_paths([], False)
            except Exception:
                pass
            await app.next_update_async()
            await usd_context.close_stage_async()
            await app.next_update_async()
            gc.collect()
    except Exception:
        pass


async def new_stage():
    """Create a new USD stage for the test."""
    app = omni.kit.app.get_app()
    usd_context = omni.usd.get_context()
    await usd_context.new_stage_async()
    await app.next_update_async()


async def setup_stage():
    """Setup a USD stage and clean up any previous stages."""
    app = omni.kit.app.get_app()
    usd_context = omni.usd.get_context()
    await cleanup_stage(usd_context.get_stage())
    await new_stage()


async def close_stage(context=None, app=None):
    """Helper to close the USD stage and flush subscribers."""
    if context is None:
        context = omni.usd.get_context()
    if app is None:
        app = omni.kit.app.get_app()
    await app.next_update_async()
    await context.close_stage_async()
    await app.next_update_async()


def clear_stage_cache():
    """Clear the USD stage cache."""
    try:
        from pxr import Usd  # type: ignore
        Usd.StageCache.Get().Clear()
    except Exception as e:
        carb.log_warn(f"Failed to clear USD stage cache: {e}")


def clear_selection(usd_context=None):
    """Clear the current selection in the USD context."""
    if usd_context is None:
        usd_context = omni.usd.get_context()
    try:
        usd_context.get_selection().set_selected_prim_paths([], False)
    except Exception as e:
        carb.log_error(f"Failed to clear selection: {e}")

async def wait_for_app_update(app=None, count=1):
    """Wait for the application to process the next update."""
    if app is None:
        app = omni.kit.app.get_app()

    for _ in range(count):
        await app.next_update_async()


class TestExtensionModel(AsyncTestCase):
    """Test class for the ExtensionModel."""

    async def setUp(self):
        """Set up the test environment."""
        redirect_carb_logs_to_stdout()

        await setup_stage()

        app = omni.kit.app.get_app()
        ext_manager = app.get_extension_manager()
        self._ext_id = ext_manager.get_enabled_extension_id("o2.vehicle.path_tracking")

        self.DEFAULT_LOOKAHEAD = 550.0
        self.MAX_LOOKAHEAD = 1200.0
        self.MIN_LOOKAHEAD = 300.0

    async def tearDown(self):
        """Tear down the test environment."""
        app = omni.kit.app.get_app()
        usd_context = omni.usd.get_context()

        try:
            clear_selection(usd_context)
            await close_stage(usd_context, app)
            clear_stage_cache
        except Exception:
            pass
        finally:
            self._ext_id = None
            gc.collect()

    async def test_load_preset(self):
        """Test loading the preset scene."""
        ext_model = ExtensionModel(
            self._ext_id,
            default_lookahead_distance=self.DEFAULT_LOOKAHEAD,
            max_lookahed_distance=self.MAX_LOOKAHEAD,
            min_lookahed_distance=self.MIN_LOOKAHEAD,
        )
        ext_model.load_preset_scene()

        stage = omni.usd.get_context().get_stage()
        ground_plane = stage.GetPrimAtPath("/World/GroundPlane")
        vehicle_template = stage.GetPrimAtPath("/World/VehicleTemplate")
        curve = stage.GetPrimAtPath("/World/BasisCurves")

        self.assertTrue(ground_plane is not None)
        self.assertTrue(vehicle_template is not None)
        self.assertTrue(curve is not None)

        ext_model.teardown()
        del ext_model, stage, ground_plane, vehicle_template, curve

        await wait_for_app_update()

    async def test_extension_model(self):
        """Test the hello function."""
        ext_model = ExtensionModel(
            self._ext_id,
            default_lookahead_distance=self.DEFAULT_LOOKAHEAD,
            max_lookahed_distance=self.MAX_LOOKAHEAD,
            min_lookahed_distance=self.MIN_LOOKAHEAD,
        )
        assert ext_model is not None

        ext_model.teardown()
        del ext_model

        await wait_for_app_update()

    # async def test_attachments_preset(self):
    #     """Test loading the attachments preset."""
    #     self.assertTrue(True)
