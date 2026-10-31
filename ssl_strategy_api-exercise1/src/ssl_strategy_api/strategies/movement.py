"""My stateless position and heading controller (Member 1).

I calculate field-relative motion only. The striker chooses targets and controls
ball handling; the existing adapter converts motion into robot coordinates.
"""

from math import hypot, isfinite, pi, radians
from typing import Optional, Tuple

from ssl_strategy_api.models import MotionLimits, RobotIntent, RobotState


POSITION_GAIN = 1.5  # I reduce speed proportionally as distance decreases (1/s).
HEADING_GAIN = 3.0  # I reduce turn speed proportionally as angle decreases (1/s).
POSITION_TOLERANCE_M = 0.05
HEADING_TOLERANCE_RAD = radians(3.0)
_LIMITS = MotionLimits()


def move_to_target(
    robot: RobotState,
    target_xy: Tuple[float, float],
    desired_heading_rad: Optional[float] = None,
    *,
    max_speed_mps: float = 1.0,
) -> RobotIntent:
    """Calculate one frame's motion toward a point and optional heading.

    Args:
        robot: Latest observed robot state; coordinates are meters.
        target_xy: Target (x, y) in FIELD coordinates, in meters.
        desired_heading_rad: Absolute field heading, or None for no turn request.
        max_speed_mps: Total planar speed limit, from 0 to 2 m/s inclusive.
            Zero disables translation while still allowing rotation.

    Returns:
        A fresh RobotIntent with field-relative linear velocity, angular velocity
        in rad/s, zero kick speed, and dribbler=False. Translation stops within
        5 cm; rotation stops within 3 degrees. These decisions are independent.
        If measured heading is absent, translation is still calculated but the
        turn request is zero. The simulator adapter requires a known heading
        before it can transmit the motion command.

    Raises:
        ValueError: Target is not a finite numeric pair, the supplied heading is
            not finite, displacement overflows, or the speed limit is invalid.

    Call again each frame. I do not keep state, plan around obstacles, constrain
    targets to the field, predict motion, or decide when a shot is ready.
    """
    try:
        target_x, target_y = target_xy
    except (TypeError, ValueError) as exc:
        raise ValueError("target_xy must contain exactly two finite numbers") from exc
    _require_finite("target x", target_x)
    _require_finite("target y", target_y)
    _require_finite("max_speed_mps", max_speed_mps)
    if not 0.0 <= max_speed_mps <= _LIMITS.max_linear_speed_mps:
        raise ValueError("max_speed_mps must be between 0 and 2 m/s")
    if desired_heading_rad is not None:
        _require_finite("desired_heading_rad", desired_heading_rad)

    dx = target_x - robot.x_m
    dy = target_y - robot.y_m
    distance = hypot(dx, dy)
    _require_finite("distance to target", distance)

    vx = vy = 0.0
    if distance > POSITION_TOLERANCE_M:
        # I bound total speed, rather than x and y separately, to handle diagonals.
        speed = min(max_speed_mps, POSITION_GAIN * distance)
        vx = speed * (dx / distance)
        vy = speed * (dy / distance)

    omega = 0.0
    if desired_heading_rad is not None and robot.heading_rad is not None:
        # I reduce each heading first so subtraction cannot overflow for large angles.
        error = ((desired_heading_rad % (2 * pi))
                 - (robot.heading_rad % (2 * pi)) + pi) % (2 * pi) - pi
        if abs(error) > HEADING_TOLERANCE_RAD:
            omega = max(-_LIMITS.max_angular_speed_rad_s,
                        min(_LIMITS.max_angular_speed_rad_s, HEADING_GAIN * error))

    return RobotIntent(vx_mps=vx, vy_mps=vy, angular_velocity_rad_s=omega)


def _require_finite(name: str, value: float) -> None:
    try:
        valid = isfinite(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not valid:
        raise ValueError(f"{name} must be a finite number")
