"""
Note: DebugRenderer relies on `omni.debugdraw` utility to optionally provide
a debug overlay with additional info regarding current state of vehicle,
path tracking destination etc.
Using omni.ui.scene would be more future proof as it will break
dependency on `omni.debugdraw` which may change or not guaranteed to be
kept in the future in Kit-based apps.

"""

# pylint: disable=too-few-public-methods, invalid-name
from enum import IntEnum

import carb
from omni.debugdraw import get_debug_draw_interface
from pxr import Gf


class DebugColor(IntEnum):
    """
    Human-readable color names with ARGB values for use in debug visualization.
    """

    WHITE = 0xFFFFFFFF
    BLACK = 0xFF000000
    RED = 0xFFFF0000
    GREEN = 0xFF00FF00
    BLUE = 0xFF0000FF
    ORANGE = 0xFFFFA500
    CHARTREUSE = 0xFF7FFF00
    LIME = 0xFF00FF00
    SPRING_GREEN = 0xFF00FF7F
    MEDIUM_SPRING_GREEN = 0xFF00FA9A
    PALE_GREEN = 0xFF98FB98
    SEA_GREEN = 0xFF2E8B57
    FOREST_GREEN = 0xFF228B22
    DARK_OLIVE_GREEN = 0xFF556B2F


class ColorMap:
    """
    Maps debug visualization entities to specific named colors.
    """

    FORWARD_LINE = DebugColor.RED
    UP_LINE = DebugColor.GREEN
    FRONT_AXLE_LINE = DebugColor.CHARTREUSE
    REAR_AXLE_LINE = DebugColor.LIME
    VEHICLE_HEADING_LINE = DebugColor.SPRING_GREEN
    TRAJECTORY_LINE = DebugColor.MEDIUM_SPRING_GREEN
    LOOKAHEAD_LINE = DebugColor.PALE_GREEN
    DESTINATION_POINT = DebugColor.SEA_GREEN
    PATH_TO_DEST_LINE = DebugColor.FOREST_GREEN
    STEERING_LEFT = DebugColor.DARK_OLIVE_GREEN
    STEERING_RIGHT = DebugColor.CHARTREUSE
    TEXT_OVERLAY = DebugColor.WHITE
    DEBUG_BOUNDING_BOX = DebugColor.GREEN


class LineThicknessMap:
    """
    Maps debug visualization entities to standardized line thickness values.
    These values control the visual prominence of lines.
    """

    FORWARD_LINE = 4.0
    UP_LINE = 4.0
    FRONT_AXLE_LINE = 10.0
    REAR_AXLE_LINE = 10.0
    VEHICLE_HEADING_LINE = 4.0
    TRAJECTORY_LINE = 2.0
    LOOKAHEAD_LINE = 8.0
    DESTINATION_POINT = 3.0
    PATH_TO_DEST_LINE = 3.0
    STEERING_LEFT = 5.0
    STEERING_RIGHT = 5.0
    TEXT_OVERLAY = 1.0
    DEBUG_BOUNDING_BOX = 1.0


class DebugDrawMode(IntEnum):
    """
    Enum for different debug draw modes.
    """

    NONE = 0
    DEBUG = 1
    VERBOSE_DEBUG = 2

    def __str__(self):
        return self.name


class DebugDrawState:
    """
    Singleton controller for managing the current debug draw mode.
    """

    _instance = None

    def __init__(self):
        self._mode = DebugDrawMode.VERBOSE_DEBUG

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugDrawState, cls).__new__(cls)
            cls._instance._mode = DebugDrawMode.VERBOSE_DEBUG
        return cls._instance

    def set_mode(self, mode: DebugDrawMode):
        """Set the current debug draw mode."""
        if not isinstance(mode, DebugDrawMode):
            raise ValueError(f"Expected DebugDrawMode, got {type(mode)}")
        self._mode = mode

    def get_mode(self) -> DebugDrawMode:
        """Get the current debug draw mode."""
        return self._mode

    def is_debug(self) -> bool:
        """Check if the current mode is DEBUG or VERBOSE_DEBUG."""
        return self._mode >= DebugDrawMode.DEBUG

    def is_verbose_debug(self) -> bool:
        """Check if the current mode is VERBOSE_DEBUG."""
        return self._mode == DebugDrawMode.VERBOSE_DEBUG


class DebugRenderer:
    """
    DebugRenderer is a utility class that provides methods to draw debug
    TODO: refactor to use omni.ui.scene instead of omni.debugdraw as the latter
    is deprecated and may not be available in future versions of Kit.
    """

    def __init__(self, vehicle_bbox_size):
        self._debug_draw = get_debug_draw_interface()
        self._vehicle_size = max(vehicle_bbox_size)
        self._enabled = True
        self._trajectory_segments_cache: list[tuple] = []
        # update_stream = omni.kit.app.get_app().get_update_event_stream()
        # self._update_sub = update_stream.create_subscription_to_pop(self._on_update, name="omni.physx update")

    @property
    def enabled(self):
        """Gets or sets whether debug drawing is currently enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("enabled must be a boolean")
        self._enabled = value

    def clear_trajectory_cache(self):
        """Clears cached trajectory segments."""
        self._trajectory_segments_cache = []

    def invalidate_debug_state(self):
        """Resets debug-related internal state to default values."""
        self.clear_trajectory_cache()
        self._enabled = True

    def _draw_segment(self, start, end, color, thickness):
        self._debug_draw.draw_line(
            carb.Float3(start[0], start[1], start[2]),
            color,
            thickness,
            carb.Float3(end[0], end[1], end[2]),
            color,
            thickness,
        )

    def _draw_trajectory(self, points: list[Gf.Vec3f]):
        """
        Draws the full trajectory as a sequence of connected lines.
        Only runs if debug drawing is enabled and a valid points list is provided.

        Args:
            points (list[Gf.Vec3f]): The list of trajectory points to draw.
        """
        if not self._trajectory_segments_cache:
            self._trajectory_segments_cache = [
                (points[i], points[i + 1]) for i in range(len(points) - 1)
            ]

        for p1, p2 in self._trajectory_segments_cache:
            self._draw_segment(
                p1, p2, ColorMap.TRAJECTORY_LINE, LineThicknessMap.TRAJECTORY_LINE
            )

    def draw_vehicle_debug(
        self, vehicle, trajectory, front_axle_pos, rear_axle_pos, forward, up
    ):
        """
        Draws the vehicle debug overlay.
        """
        if not self._enabled:
            return

        curr_vehicle_pos = vehicle.curr_position()
        forward = vehicle.forward()
        up = vehicle.up()

        x = curr_vehicle_pos[0]
        y = curr_vehicle_pos[1]
        z = curr_vehicle_pos[2]

        s = self._vehicle_size / 2

        # Draw forward
        self._debug_draw.draw_line(
            carb.Float3(x, y, z),
            ColorMap.FORWARD_LINE,
            LineThicknessMap.FORWARD_LINE,
            carb.Float3(x + s * forward[0], y + s * forward[1], z + s * forward[2]),
            ColorMap.FORWARD_LINE,
            LineThicknessMap.FORWARD_LINE,
        )
        # Draw up
        self._debug_draw.draw_line(
            carb.Float3(x, y, z),
            ColorMap.UP_LINE,
            LineThicknessMap.UP_LINE,
            carb.Float3(x + s * up[0], y + s * up[1], z + s * up[2]),
            ColorMap.UP_LINE,
            LineThicknessMap.UP_LINE,
        )

        self._draw_trajectory(trajectory.get_all_points())

        if DebugDrawState().is_verbose_debug():
            af = front_axle_pos
            ar = rear_axle_pos
            # Draw axle axis connecting front to rear
            self._debug_draw.draw_line(
                carb.Float3(af[0], af[1], af[2]),
                ColorMap.FRONT_AXLE_LINE,
                LineThicknessMap.FRONT_AXLE_LINE,
                carb.Float3(ar[0], ar[1], ar[2]),
                ColorMap.FRONT_AXLE_LINE,
                LineThicknessMap.FRONT_AXLE_LINE,
            )

            # Draw front axle
            fl = vehicle.wheel_pos_front_left()
            fr = vehicle.wheel_pos_front_right()
            self._debug_draw.draw_line(
                carb.Float3(fl[0], fl[1], fl[2]),
                ColorMap.FRONT_AXLE_LINE,
                LineThicknessMap.FRONT_AXLE_LINE,
                carb.Float3(fr[0], fr[1], fr[2]),
                ColorMap.FRONT_AXLE_LINE,
                LineThicknessMap.FRONT_AXLE_LINE,
            )

            # Draw rear axle
            rl = vehicle.wheel_pos_rear_left()
            rr = vehicle.wheel_pos_rear_right()

            self._debug_draw.draw_line(
                carb.Float3(rl[0], rl[1], rl[2]),
                ColorMap.REAR_AXLE_LINE,
                LineThicknessMap.REAR_AXLE_LINE,
                carb.Float3(rr[0], rr[1], rr[2]),
                ColorMap.REAR_AXLE_LINE,
                LineThicknessMap.REAR_AXLE_LINE,
            )

    def update_path_to_dest(self, vehicle_pos, dest_pos):
        """
        Draws a debug line from the vehicle's current position to the destination point.
        """
        if not self._enabled:
            return
        if dest_pos:
            self._debug_draw.draw_line(
                carb.Float3(vehicle_pos[0], vehicle_pos[1], vehicle_pos[2]),
                ColorMap.LOOKAHEAD_LINE,
                LineThicknessMap.LOOKAHEAD_LINE,
                carb.Float3(dest_pos[0], dest_pos[1], dest_pos[2]),
                ColorMap.LOOKAHEAD_LINE,
                LineThicknessMap.LOOKAHEAD_LINE,
            )
