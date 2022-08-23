import omni.ui as ui

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
        "color": 0xFFFFFFFF,
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


class ExtensionUI():
    
    def __init__(self, controller):
        self._controller = controller

    def build_ui(self, lookahead_distance):
        self._window = ui.Window("Vehicle Path Tracking Extension", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                self._settings_frame = ui.CollapsableFrame(
                    "SETTINGS", collapsed=False,
                    height=COLLAPSABLE_FRAME_HEIGHT,
                    style=CollapsableFrameStyle
                )
                with self._settings_frame:
                    with ui.VStack():
                        width = 64
                        height = 16
                        with ui.HStack(width=width, height=height):
                            ui.Label("Enable debug: ")
                            enable_debug_checkbox = ui.CheckBox()
                            enable_debug_checkbox.model.add_value_changed_fn(
                                self._controller._changed_enable_debug
                            )
                        ui.Spacer(height=LINE_HEIGHT/4)
                        ui.Label("REFERENCE COORDINATE SYSTEM")
                        with ui.HStack(width=width, height=height):
                            ui.Label("Up-axis: Y-axis (fixed)")
                        ui.Spacer(height=LINE_HEIGHT/4)
                        ui.Label("PURE PURSUIT ALGORITHM")
                        with ui.HStack(width=width, height=height):
                            ui.Label("Look ahead distance: ")
                            self._lookahead_field = ui.FloatField(width=64.0)
                            self._lookahead_field.model.set_value(lookahead_distance)
                            self._lookahead_field.model.add_end_edit_fn(self._submit_lookahead_distance)

                self._controls_frame = ui.CollapsableFrame("CONTROLS", collapsed=False, height=COLLAPSABLE_FRAME_HEIGHT)
                with self._controls_frame:
                    with ui.VStack():
                        ui.Button(
                            "Start Scenario", 
                            clicked_fn=self._controller._on_click_start_scenario, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Line(height=LINE_HEIGHT)
                        ui.Button(
                            "Load a preset scene",
                            clicked_fn=self._controller._on_click_load_preset_scene, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Line(height=LINE_HEIGHT)
                        ui.Button(
                            "Load a ground plane", 
                            clicked_fn=self._controller._on_click_load_ground_plane, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Button(
                            "Load a car model", 
                            clicked_fn=self._controller._on_click_load_sample_vehicle, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Button(
                            "Load a sample BasisCurve", 
                            clicked_fn=self._controller._on_click_load_basis_curve, height=DEFAULT_BTN_HEIGHT
                        )

                ui.Line(height=LINE_HEIGHT)

                self._atachments_frame = ui.CollapsableFrame(
                    "VEHICLE-TO-CURVE ATTACHMENTS", 
                    collapsed=False, height=COLLAPSABLE_FRAME_HEIGHT
                )
                with self._atachments_frame:
                    with ui.VStack():
                        with ui.HStack(width=width, height=height):
                            ui.Label(
                                "(1) Select WizardVehicle Xform and corresponding BasisCurve;\n(2) Click 'Attach Selected'",
                                width=32
                            )
                        ui.Button(
                            "Attach Selected", 
                            clicked_fn=self._controller._on_click_attach_selected, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Button(
                            "Recompute trajectories",
                            clicked_fn=self._controller._on_click_recompute_trajectories, height=DEFAULT_BTN_HEIGHT
                        )
                        ui.Button("Clear All Attachments", clicked_fn=self._controller._on_click_clear_attachments)

        # viewport = ui.Workspace.get_window("Viewport")
        # self._window.dock_in(viewport, ui.DockPosition.BOTTOM)
        # Dock extension window alongside 'Property' extension.
        self._window.deferred_dock_in("Property")
        # dock_in_window is deprecated unfortunatelly
        # self._window.dock_in_window("Viewport", ui.DockPosition.RIGHT, ratio=0.1)

    def teardown(self):
        self._controller = None
        self._settings_frame = None
        self._controls_frame = None
        self._atachments_frame = None
        self._window = None

    def get_lookahead_distance(self):
        return self._lookahead_field.model.as_float

    def set_lookahead_distance(self, distance):
        self._lookahead_field.model.set_value(distance)

    def _submit_lookahead_distance(self, model):
        self._controller._changed_lookahead_distance(model.as_float)