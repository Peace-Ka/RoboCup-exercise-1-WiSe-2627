"""Member 1's movement helper. Implement this together before integrating it.

This module calculates one frame's motion request. It does not decide where the
ball should be approached or when to kick; those decisions belong to striker.py.
"""

from typing import Optional, Tuple

from ssl_strategy_api.models import RobotIntent, RobotState


def move_to_target(
    robot: RobotState,
    target_xy: Tuple[float, float],
    desired_heading_rad: Optional[float] = None,
    *,
    max_speed_mps: float = 1.0,
) -> RobotIntent:
    """Request movement toward a field-coordinate target, optionally turning.

    Agreed behavior for the finished helper:
    - Positions are meters; headings are radians; velocities are field-relative.
    - Slow down near the target and stop translation within 0.05 m.
    - Limit the velocity vector's magnitude to max_speed_mps (0 through 2).
    - Turn using the shortest angle, at no more than 3 rad/s.
    - Continue turning at the target if a desired heading was supplied.
    - Request no turn if the desired heading or measured heading is missing.
    - Never request a kick or enable the dribbler.

    Member 2 can use dataclasses.replace() to add ball-handling commands to the
    returned intent. Call this helper again with the latest state each frame.
    """
    # Step 1: calculate position error, distance, and bounded linear velocity.
    # Step 2: wrap heading error to [-pi, pi) and calculate bounded rotation.
    # Step 3: return RobotIntent with the calculated motion.
    raise NotImplementedError("Movement helper is the team's first implementation task")
