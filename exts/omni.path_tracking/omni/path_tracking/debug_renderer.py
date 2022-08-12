import carb
from omni.debugdraw import get_debug_draw_interface
import omni.kit.app
from pxr import Gf

import math

class DebugRenderer():
    def __init__(self):
        self._debug_draw = get_debug_draw_interface()
        self._curr_time = 0.0
        self._color = 0x60FFFFFF
        self._line_thickness = 2.0
        self._size = 250.0
        self._enabled = True
        # update_stream = omni.kit.app.get_app().get_update_event_stream()
        # self._update_sub = update_stream.create_subscription_to_pop(self._on_update, name="omni.physx demo test update")

    def on_update(self, event):
        if not self._enabled:
            return
        dt = event.payload["dt"]
        self._curr_time = self._curr_time + dt
        x = math.cos(self._curr_time) * self._size
        z = math.sin(self._curr_time) * self._size
        self._debug_draw.draw_line(
                carb.Float3(0.0, 0.0, 0.0), self._color, self._line_thickness,
                carb.Float3(x, self._size, z), self._color, self._line_thickness
            )

        self._debug_draw.draw_sphere(carb.Float3(0.0, 0.0, 0.0), self._size, 0x70FFFFFF)

    def _draw_segment(self, start, end, color, thickness):
        self._debug_draw.draw_line(
            carb.Float3(start[0], start[1], start[2]),
            color, thickness,
            carb.Float3(end[0], end[1], end[2]),
            color, thickness
        )

    def update_path_tracking(self, front_axle_pos, rear_axle_pos, forward, dest_pos):
        if not self._enabled:
            return
        color = 0xFFFF4500
        thickness = 10.0
        self._draw_segment(rear_axle_pos, dest_pos, color, thickness)
        color = 0xFF00FA9A
        self._draw_segment(rear_axle_pos, front_axle_pos, color, thickness)

    def update_vehicle(self, vehicle):
        curr_vehicle_pos = vehicle.curr_position()
        forward = vehicle.forward()
        up = vehicle.up()
        if not self._enabled:
            return     
        s = 500
        t = self._line_thickness * 2
        x = curr_vehicle_pos[0]
        y = curr_vehicle_pos[1]
        z = curr_vehicle_pos[2]
        # self._debug_draw.draw_sphere(carb.Float3(x, y, z), self._size, 0x70FFFFFF)

        # Draw forward
        self._debug_draw.draw_line(
            carb.Float3(x, y, z),
            0xFF0000FF, t,
            carb.Float3(x + s * forward[0], y + s * forward[1], z + s * forward[2]),
            0xFF0000FF, t
        )
        # Draw up
        self._debug_draw.draw_line(
            carb.Float3(x, y, z),
            0xFF00FF00, t,
            carb.Float3(x + s * up[0], y + s * up[1], z + s * up[2]),
            0xFF00FF00, t
        )
        # Draw axle separation
        af = vehicle.axle_front()
        ar = vehicle.axle_rear()
        axle_color = 0xFF8A2BE2
        self._debug_draw.draw_line(
            carb.Float3(af[0], af[1], af[2]),
            axle_color, t*4,
            carb.Float3(ar[0], ar[1], ar[2]),
            axle_color, t*4
        )
        # Draw front axle
        fl = vehicle.wheel_pos_front_left()
        fr = vehicle.wheel_pos_front_right()
        front_axle_color = 0xFFFF1493
        self._debug_draw.draw_line(
            carb.Float3(fl[0], fl[1], fl[2]),
            front_axle_color, t*2,
            carb.Float3(fr[0], fr[1], fr[2]),
            front_axle_color, t*2
        )
        # Draw rear axle
        rl = vehicle.wheel_pos_front_left()
        rr = vehicle.wheel_pos_front_right()
        rear_axle_color = 0xFFCD853F
        self._debug_draw.draw_line(
            carb.Float3(rl[0], rl[1], rl[2]),
            rear_axle_color, t*2,
            carb.Float3(rr[0], rr[1], rr[2]),
            rear_axle_color, t*2
        )

    def update_path_to_dest(self, vehicle_pos, dest_pos):
        if not self._enabled:
            return
        if dest_pos:
            self._debug_draw.draw_line(
                carb.Float3(vehicle_pos[0], vehicle_pos[1], vehicle_pos[2]), self._color, self._line_thickness,
                carb.Float3(dest_pos[0], dest_pos[1], dest_pos[2]), self._color, self._line_thickness
            )

    def enable(self, value):
        self._enabled = value