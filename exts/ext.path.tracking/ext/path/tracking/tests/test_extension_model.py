from email.policy import default
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni.kit.test import AsyncTestCaseFailOnLogError

# from omni.kit.test_suite.helpers import wait_stage_loading

from ..scripts.model import ExtensionModel

class TestExtensionModel(AsyncTestCaseFailOnLogError):
    async def setUp(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        ext_manager = omni.kit.app.get_app().get_extension_manager()
        self._ext_id = ext_manager.get_enabled_extension_id("omni.path.tracking")

    async def tearDown(self):
        self._ext_id = None

    async def test_load_preset(self):
        ext_model = ExtensionModel(self._ext_id)
        ext_model.load_preset_scene()

        stage = omni.usd.get_context().get_stage()
        ground_plane = stage.GetPrimAtPath("/World/GroundPlane")
        vehicle_template = stage.GetPrimAtPath("/World/VehicleTemplate")
        curve = stage.GetPrimAtPath("/World/BasisCurves")

        self.assertTrue(ground_plane is not None)
        self.assertTrue(vehicle_template is not None)
        self.assertTrue(curve is not None)

    async def test_hello(self):
        ext_model = ExtensionModel(self._ext_id)

    async def test_attachments_preset(self):
        # TODO: provide impl
        self.assertTrue(True)