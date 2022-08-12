import omni.ui as ui
import math

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