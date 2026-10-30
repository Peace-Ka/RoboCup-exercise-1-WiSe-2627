# Member 1: movement.py

Your job is to move a robot to a supplied point and optionally turn it to a supplied
heading. Your teammate decides which point and heading to supply.

## The interface your teammate can use

```python
from ssl_strategy_api.strategies.movement import move_to_target

intent = move_to_target(
    robot,
    target_xy=(0.5, 1.0),
    desired_heading_rad=0.0,
    max_speed_mps=1.0,
)
return {robot_id: intent}
```

This call raises `NotImplementedError` until we implement the helper. The current
placeholder striker does not call it, so the existing simulator demo remains usable.

The result is a `RobotIntent` in meters/second and radians/second. Do not rotate
the velocity into robot coordinates: the supplied adapter already does that.
The movement helper never kicks or activates the dribbler. For contact, Member 2
can use `dataclasses.replace(intent, dribbler=True)`.

## Implement in three small steps

1. **Position error:** subtract the robot's x and y from the target x and y.
   Use `math.hypot(dx, dy)` for distance. If within 0.05 m, set both linear
   velocities to zero. Check this before dividing by distance.
2. **Speed:** start with a proportional speed: `speed = min(max_speed_mps,
   position_gain * distance)`. Multiply it by the unit direction `(dx/distance,
   dy/distance)`. This limits diagonal motion correctly. A position gain of
   1.5 per second is an initial value to tune, not an optimal value.
3. **Heading:** if both headings exist, compute `error = (desired - current +
   math.pi) % (2 * math.pi) - math.pi`. Multiply by a heading gain and clamp
   to [-3, 3] rad/s. Add a small heading tolerance to stop tiny corrections.
   If either heading is absent, request zero rotation.

Reject a non-finite target, a non-finite supplied heading, or a maximum speed outside
0 through 2 m/s with `ValueError`. Keep tuning constants near the top of the file.
Keep rotation independent from translation: arriving at the point should not prevent
the robot from finishing its turn.

## Before handing it over

Check these behaviors with small numerical examples, then in the simulator:

- A target directly to the right produces positive x velocity.
- A diagonal target never exceeds the requested total speed.
- A robot at the target does not divide by zero or move away.
- A closer target requests a lower speed.
- Turning from +179 degrees to -179 degrees takes the short +2 degree turn.
- At the target, an unfinished requested turn still works.
- Missing heading information does not crash the helper.
- Every returned intent has zero kick speed and the dribbler off.

Once implemented, add a small standard-library `unittest` file for these controller
properties. No new test framework is needed. Then check motion in a short simulator run.

Obstacle avoidance, penalty-area planning, ball approach positions, and kick timing
belong to the striker's behavior. They are not prerequisites for handing over this helper.

Member 2 can start writing the three-stage striker now using the agreed signature.
Keep the helper signature stable so integration only requires the implementation.
