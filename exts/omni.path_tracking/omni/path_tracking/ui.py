import omni.ui as ui
import math

DEFAULT_BTN_HEIGHT = 22
COLLAPSABLE_FRAME_HEIGHT = 32
LINE_HEIGHT = 32

class ExtensionUI():
    
    def __init__(self, controller):
        self._controller = controller

    def build_ui(self):
        self._viewport_ui = None
        # self._viewport_ui = ViewportUI()
        # self._viewport_ui.build_viewport()
        
        self._window = ui.Window("Vehicle Path Tracking Extension", width=300, height=300)
        with self._window.frame:
            with ui.VStack():
                self._settings_frame = ui.CollapsableFrame("SETTINGS", collapsed=False, height=COLLAPSABLE_FRAME_HEIGHT)
                with self._settings_frame:
                    with ui.VStack():
                        width = 64
                        height = 16
                        with ui.HStack(width=width, height=height):
                            ui.Label("Enable debug: ")
                            self._enable_debug_checkbox = ui.CheckBox()
                            self._enable_debug_checkbox.model.add_value_changed_fn(
                                self._controller._changed_enable_debug
                            )
                        ui.Spacer(height=LINE_HEIGHT/4)
                        with ui.HStack(width=width, height=height):
                            ui.Label("Up-axis: Y-axis (fixed)")
                        ui.Spacer(height=LINE_HEIGHT/4)

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
                            "Load a smaple BasisCurve", 
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
        pass

# ==============================================================================
# Additional Optional UI overlay on Viewport itself.
# ==============================================================================
class ViewportUI:
    def __init__(self):
        self._vehicle_velocity_label = None
        self._vehicle_speed_label = None
        self._steer_angle_label = None
        self._distance_label = None

    def build_viewport(self):
        window = ui.Workspace.get_window("Viewport")
        with window.frame:
            with ui.ZStack():
                ui.Rectangle(width=480, height=200, style={"background_color": 0xAA444444})
                with ui.VStack(width=50, height=100, style={"margin": 20, "padding": 20}):
                    label_style = {"font_size" : 24, "margin_height": 10}
                    self._vehicle_velocity_label = ui.Label("(0.0, 0.0, 0.0)", style=label_style)
                    self._vehicle_speed_label = ui.Label("0 kmh", style=label_style)
                    self._steer_angle_label = ui.Label("0.0", style=label_style)
                    self._distance_label = ui.Label("", style=label_style)

    def teardown(self):
        self._vehicle_velocity_label = None
        self._vehicle_speed_label = None
        self._steer_angle_label = None
        self._distance_label = None
        # Clear viewport
        frame = ui.Workspace.get_window("Viewport").frame
        frame.clear()
        frame.rebuild()
    
    def set_vehicle_velocity(self, value):
        self._vehicle_velocity_label.text = f"Velocity vector: ({value[0]:9.2f}, {value[1]:9.2f}, {value[2]:9.2f})"

    def set_vehicle_speed(self, value):
        self._vehicle_speed_label.text = f"Speed: {value:9.2f} km/h"

    def set_steer_angle(self, value):
        self._steer_angle_label.text = f"Steer control: {value:9.3f}"

    def set_distance_label(self, value):
        self._distance_label.text = f"Distance: {value:9.3f}m"