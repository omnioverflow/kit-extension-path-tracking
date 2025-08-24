"""
UI module for vehicle-to-curve path tracking extension.
"""

# pylint: disable=too-many-statements
from typing import List, Optional

import omni.usd
from omni import ui
from pxr import UsdGeom

# Note: Avoid importing TrajectoryFactory at module import time to prevent test-time import errors
# when optional deps (e.g., cmap) are unavailable. We'll import it lazily in the click handler.

DEFAULT_BTN_HEIGHT = 22
COLLAPSABLE_FRAME_HEIGHT = 32
LINE_HEIGHT = 32
LABEL_WIDTH = 150
LABEL_INNER_WIDTH = 70
ELEM_MARGIN = 4
BTN_WIDTH = 32
VSPACING = ELEM_MARGIN * 2
BORDER_RADIUS = 4

CollapsableFrameStyle = {
    "CollapsableFrame": {
        "background_color": 0xFF333333,
        "secondary_color": 0xFF333333,
        "color": 0xFF00B976,
        "border_radius": BORDER_RADIUS,
        "border_color": 0x0,
        "border_width": 0,
        "font_size": 14,
        "padding": ELEM_MARGIN * 2,
        "margin_width": ELEM_MARGIN,
        "margin_height": ELEM_MARGIN,
    },
    "CollapsableFrame:hovered": {"secondary_color": 0xFF3C3C3C},
    "CollapsableFrame:pressed": {"secondary_color": 0xFF333333},
    "Button": {"margin_height": 0, "margin_width": ELEM_MARGIN, "border_radius": BORDER_RADIUS},
    "Button:selected": {"background_color": 0xFF666666},
    "Button.Label:disabled": {"color": 0xFF888888},
    "Slider": {"margin_height": 0, "margin_width": ELEM_MARGIN, "border_radius": BORDER_RADIUS},
    "Slider:disabled": {"color": 0xFF888888},
    "ComboBox": {"margin_height": 0, "margin_width": ELEM_MARGIN, "border_radius": BORDER_RADIUS},
    "Label": {"margin_height": 0, "margin_width": ELEM_MARGIN},
    "Label:disabled": {"color": 0xFF888888},
}

TREE_VIEW_STYLE = {
    "TreeView:selected": {"background_color": 0x66FFFFFF},
    "TreeView.Item": {"color": 0xFFCCCCCC},
    "TreeView.Item:selected": {"color": 0xFFCCCCCC},
    "TreeView.Header": {"background_color": 0xFF000000},
}

IMPORTANT_BUTTON_STYLE = {"Button": {"background_color": 0x7000B976}}


class AttachedItem(ui.AbstractItem):
    """Single item of the model"""

    def __init__(self, text):
        super().__init__()
        self.name_model = ui.SimpleStringModel(text)


class AttachmentModel(ui.AbstractItemModel):
    """
    Represents the list active vehicle-to-curve attachments.
    It is used to make a single level tree appear like a simple list.
    """

    def __init__(self, items: List[object]):
        super().__init__()
        self.attachments_changed(items)

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            return []
        return self._attachments

    def get_item_value_model_count(self, _item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item, _column_id):
        """
        Return value model.
        It's the object that tracks the specific value.
        In our case we use ui.SimpleStringModel.
        """
        if item and isinstance(item, AttachedItem):
            return item.name_model
        return None

    def attachments_changed(self, attachments):
        """Updates the model with new attachment list."""
        self._attachments = []
        for i, attachment in enumerate(attachments, start=1):
            self._attachments.append(AttachedItem(f"[{i}] {attachment}"))
        self._item_changed(None)


class ExtensionUI:
    """Main UI panel for the extension."""

    def __init__(self, controller):
        self._controller = controller

        self._window: Optional[ui.Window] = None
        self._settings_frame: Optional[ui.CollapsableFrame] = None
        self._controls_frame: Optional[ui.CollapsableFrame] = None
        self._attachments_frame: Optional[ui.CollapsableFrame] = None
        self._attachment_label: Optional[ui.Label] = None
        self._attachment_model: Optional[AttachmentModel] = None
        self._lookahead_field: Optional[ui.FloatField] = None
        self._checkbox_trajectory_loop: Optional[ui.CheckBox] = None

    def build_ui(self, lookahead_distance, attachments):
        """Constructs the UI layout."""
        self._window = ui.Window("Vehicle Path Tracking Extension (Beta)", width=300, height=300)
        with self._window.frame:
            with ui.HStack():
                # Column #1
                with ui.VStack():
                    self._settings_frame = ui.CollapsableFrame(
                        "SETTINGS", collapsed=False, height=COLLAPSABLE_FRAME_HEIGHT, style=CollapsableFrameStyle
                    )
                    with self._settings_frame:
                        with ui.VStack():
                            width = 64
                            height = 16
                            with ui.HStack(width=width, height=height):
                                ui.Label("Enable debug: ")
                                enable_debug_checkbox = ui.CheckBox()
                                enable_debug_checkbox.model.add_value_changed_fn(
                                    self._controller.on_changed_enabled_debug
                                )
                            ui.Spacer(height=LINE_HEIGHT / 4)
                            ui.Label("REFERENCE COORDINATE SYSTEM: Up-axis: Y-axis (fixed)")
                            ui.Spacer(height=LINE_HEIGHT / 4)
                            with ui.HStack(width=width, height=height):
                                ui.Label("Pure Pursuit look ahead distance: ")
                                self._lookahead_field = ui.FloatField(width=64.0)
                                self._lookahead_field.model.set_value(lookahead_distance)
                                self._lookahead_field.model.add_end_edit_fn(self._notify_lookahead_distance_changed)
                            with ui.HStack(width=width, height=height):
                                ui.Label("Trajectory Loop:")
                                self._checkbox_trajectory_loop = ui.CheckBox(name="TracjectoryLoop")
                                self._checkbox_trajectory_loop.model.set_value(False)
                                self._checkbox_trajectory_loop.model.add_value_changed_fn(
                                    self._controller.on_trajectory_loop_value_changed
                                )

                    self._controls_frame = ui.CollapsableFrame(
                        "CONTROLS", collapsed=False, height=COLLAPSABLE_FRAME_HEIGHT, style=CollapsableFrameStyle
                    )
                    with self._controls_frame:
                        with ui.HStack():
                            with ui.VStack():
                                ui.Button(
                                    "Start Scenario",
                                    clicked_fn=self._controller.on_click_start_scenario,
                                    height=DEFAULT_BTN_HEIGHT,
                                    style=IMPORTANT_BUTTON_STYLE,
                                )
                                ui.Spacer(height=LINE_HEIGHT / 8)
                                ui.Button(
                                    "Stop Scenario",
                                    clicked_fn=self._controller.on_click_stop_scenario,
                                    height=DEFAULT_BTN_HEIGHT,
                                    style=IMPORTANT_BUTTON_STYLE,
                                )
                                ui.Line(height=LINE_HEIGHT / 2)
                                ui.Button(
                                    "Load a preset scene",
                                    clicked_fn=self._controller.on_click_load_preset_scene,
                                    height=DEFAULT_BTN_HEIGHT,
                                )
                                ui.Line(height=LINE_HEIGHT / 2)
                                ui.Button(
                                    "Load a ground plane",
                                    clicked_fn=self._controller.on_click_load_ground_plane,
                                    height=DEFAULT_BTN_HEIGHT,
                                )
                                ui.Spacer(height=LINE_HEIGHT / 8)
                                ui.Button(
                                    "Load a sample vehicle template",
                                    clicked_fn=self._controller.on_click_load_sample_vehicle,
                                    height=DEFAULT_BTN_HEIGHT,
                                )
                                ui.Spacer(height=LINE_HEIGHT / 8)
                                ui.Button(
                                    "Define a circular trajectory",
                                    clicked_fn=self._on_click_define_circular_trajectory,
                                    height=DEFAULT_BTN_HEIGHT,
                                )
                                ui.Spacer(height=LINE_HEIGHT / 8)
                                ui.Button(
                                    "Load a sample BasisCurve",
                                    clicked_fn=self._controller.on_click_load_basis_curve,
                                    height=DEFAULT_BTN_HEIGHT,
                                )

                    self._attachments_frame = ui.CollapsableFrame(
                        "VEHICLE-TO-CURVE ATTACHMENTS",
                        collapsed=False,
                        height=COLLAPSABLE_FRAME_HEIGHT,
                        style=CollapsableFrameStyle,
                    )
                    with self._attachments_frame:
                        with ui.VStack():
                            ui.Label(
                                "(1) Select WizardVehicle Xform and corresponding BasisCurve;\n"
                                "(2) Click 'Attach Selected'",
                                width=32,
                            )
                            ui.Spacer(height=LINE_HEIGHT / 8)
                            ui.Button(
                                "Attach Selected",
                                clicked_fn=self._controller.on_click_attach_selected,
                                height=DEFAULT_BTN_HEIGHT,
                                style=IMPORTANT_BUTTON_STYLE,
                            )
                            ui.Spacer(height=LINE_HEIGHT / 8)
                            ui.Button("Clear All Attachments", clicked_fn=self._controller.on_click_clear_attachments)

                self._attachments_frame = ui.CollapsableFrame(
                    "VEHICLE-TO-CURVE attachments",
                    collapsed=False,
                    height=COLLAPSABLE_FRAME_HEIGHT,
                    style=CollapsableFrameStyle,
                )
                with self._attachments_frame:
                    with ui.VStack(direction=ui.Direction.TOP_TO_BOTTOM, height=20, style=CollapsableFrameStyle):
                        if attachments and len(attachments) > 0:
                            self._attachment_label = ui.Label(
                                "Active vehicle-to-curve attachments:", alignment=ui.Alignment.TOP
                            )
                        else:
                            self._attachment_label = ui.Label("No active vehicle-to-curve attachments")
                        self._attachment_model = AttachmentModel(attachments)
                        ui.TreeView(
                            self._attachment_model,
                            root_visible=False,
                            header_visible=False,
                            style={"TreeView.Item": {"margin": 4}},
                        )

        self._window.deferred_dock_in("Property")

    def _on_click_define_circular_trajectory(self):
        """Creates a circular BasisCurves trajectory on the current stage."""
        # Lazy import to avoid importing optional deps during test discovery
        from .trajectory_factory import TrajectoryFactory

        stage = omni.usd.get_context().get_stage()
        radius = 1000.0
        center = (-radius, 0.0, 0.0)
        TrajectoryFactory.create_linear_circle(
            stage=stage,
            prim_path="/World/CircularTrajectory",
            center=center,
            radius=radius,
            num_points=128,
            axis=UsdGeom.Tokens.y,  # Circle in XZ plane (Y-up)
            periodic=True,
            width=10.0,
            reverse_cmap=False,
        )

    def teardown(self):
        """Clean up and release UI references."""
        self._controller = None
        self._settings_frame = None
        self._controls_frame = None
        self._attachments_frame = None
        self._window = None

    def get_lookahead_distance(self):
        """Returns current lookahead distance."""
        return self._lookahead_field.model.as_float

    def set_lookahead_distance(self, distance):
        """Sets lookahead distance."""
        self._lookahead_field.model.set_value(distance)

    def _notify_lookahead_distance_changed(self, model):
        """Internal callback for lookahead distance change."""
        self._controller.on_lookahead_distance_changed(model.as_float)

    def update_attachment_info(self, attachments):
        """Updates the UI with current attachment info."""
        self._attachment_model.attachments_changed(attachments)
        self._attachment_label.text = (
            "Active vehicle-to-curve attachments:" if attachments else "No active vehicle-to-curve attachments"
        )
