# My movement controller - Member 1

## Status

I implemented `move_to_target()` and verified it with 18 automated tests and six
controlled rSoccer scenarios. My controller is available for striker integration.
The default `StrikerStrategy` still contains the supplied circular-motion starter;
I isolated the movement demonstration from Member 2's unfinished shooting behavior.

## The stable interface

```python
move_to_target(robot, target_xy, desired_heading_rad=None, *, max_speed_mps=1.0)
```

- `robot`: latest `RobotState`.
- `target_xy`: `(x, y)` in meters, in field coordinates.
- `desired_heading_rad`: absolute field heading in radians; `None` requests no turn.
- `max_speed_mps`: total speed limit from 0 through 2 m/s. Zero allows turning in place.
- Result: a new, immutable `RobotIntent`; kick speed is zero and dribbler is off.

I stop requesting translation within 0.05 m and rotation within 3 degrees.
I calculate translation and rotation independently. I slow translation with a
position gain of 1.5/s and rotation with a heading gain of 3/s. These are verified
starting values, not globally optimal settings.

I use field coordinates. The adapter performs the rotation into robot coordinates
once; callers must not rotate the returned velocity again.

## Member 2 integration example

```python
from dataclasses import replace
from ssl_strategy_api.models import TeamColor
from ssl_strategy_api.strategies.movement import move_to_target

robots = state.robots_blue if config.team == TeamColor.BLUE else state.robots_yellow
robot = robots.get(robot_id)
if robot is None:
    return {}

intent = move_to_target(
    robot,
    target_xy=approach_point,
    desired_heading_rad=shot_heading,
    max_speed_mps=1.0,
)
# During contact, a lower speed limit and the dribbler can be requested:
# intent = replace(move_to_target(robot, ball_position, shot_heading,
#                                 max_speed_mps=0.2), dribbler=True)
return {robot_id: intent}
```

`approach_point`, `shot_heading`, `ball_position`, and `robot_id` come from the
striker's decisions. This example is a caller pattern, not a complete shooting strategy.
I do not modify the passed robot or any previous intent.

The caller must run this function with the newest observation every frame. A
changed target takes effect immediately because I keep no controller state.

## Important caller decisions

- The striker checks distance and heading error itself to change stages. A zero
  velocity alone does not prove readiness: the caller may have set speed to zero,
  omitted a heading, or supplied a robot with missing heading information.
- The striker confirms infrared contact and shot alignment before kicking.
- My 5 cm position tolerance is for point movement. The striker should use infrared
  contact for ball acquisition rather than interpreting that tolerance as possession.
- I calculate translation when heading is missing, but request zero rotation. The
  current rSoccer adapter cannot transmit motion without a known robot heading.
- I raise `ValueError` for malformed/non-finite targets, non-finite supplied headings,
  invalid speed limits, and overflowing displacement. I do not silently accept them.
- I choose the negative turn at an exact 180-degree tie; either direction is equally short.

## Scope and limits

I control movement to a point and heading. I do not avoid obstacles, enforce field
or penalty-area boundaries, choose targets, predict ball motion, dribble, or kick.
The striker owns those decisions. I use proportional position control without an
acceleration limiter or velocity feedback. Real inertia and collisions can still
cause overshoot; the simulator checks establish behavior for the listed scenarios,
not every possible starting state. The helper is not a learned controller.

## Reproduce verification

With the `rsoccer` environment active, from the repository root:

```sh
python -m unittest discover -s tests -v
python -m ssl_strategy_api.run_demos.run_movement --no-render --scenario all
python -m ssl_strategy_api.run_demos.run_movement --scenario diagonal
```

The last command opens the before/after windows in sequence. The white cross marks
the target. Each trial resets to the same start. Before uses the supplied striker;
after calls my helper. This illustrates target control, not a speed-matched benchmark.
The starter ignores the target; it is not a previous implementation of my helper.

The headless demo writes `results/movement/trajectory.csv` and `summary.json`.
It exits nonzero if an after-trial fails to remain within both tolerances throughout
the last simulated second. `--output-dir` selects another destination.
For presentation charts, `python scripts/plot_movement.py` requires matplotlib in
that interpreter; plotting is optional and not a controller/runtime dependency.

## Measured results

All trials ran for 8 simulated seconds. Arrival means both tolerances are met;
all six after-trials remained within them throughout the last second.
For retargeting, the target changes at 4 seconds and arrival time is measured from
trial start, so 6.375 seconds corresponds to 2.375 seconds after the change.

| Scenario | Final position error (cm) | Absolute heading error (degrees) | First arrival (s) |
|---|---:|---:|---:|
| diagonal | 4.839 | 2.957 | 3.350 |
| straight | 4.905 | 2.977 | 2.950 |
| turn-only | 0.003 | 2.824 | 1.225 |
| angle-wrap | 0.004 | 2.809 | 0.125 |
| slow-contact | 4.812 | 0.000 | 2.525 |
| retarget | 4.941 | 2.780 | 6.375 |

My diagonal comparison ended 4.84 cm from the target, versus 215.78 cm for the
supplied circular-motion example. This is a fixed-target movement check; scoring
performance awaits Member 2's striker integration and Member 4's evaluation.
