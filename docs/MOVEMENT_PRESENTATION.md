# My movement implementation: presentation notes

## My contribution in one sentence

I implemented a reusable controller that turns a robot's current position and a
requested target into bounded movement and rotation commands.

## What existed before

The course supplied robot observations, command data types, simulator adapters,
and an example striker. That striker requested a changing velocity direction and
a constant rotation; it did not steer toward a target. My `movement.py` initially
contained only the agreed interface and raised `NotImplementedError`.

I completed that helper while keeping the supplied adapters and exercise evaluation
runner unchanged. I added a separate movement demonstration so I could test my
contribution before the full shooting strategy was ready.

## Why the team needs my function

My aiming teammate chooses a goal target. My striker teammate decides where the
robot should stand behind the ball and when it should move into contact. I execute
those requested movements. My evaluation teammate measures the integrated result.

This separation means the striker can change its approach strategy without
rewriting movement calculations, and I can tune the controller without rewriting
shot selection. I kept the agreed function signature stable for that handoff.

## How I calculate movement

I subtract current position from target position:

```text
dx = target_x - robot_x
dy = target_y - robot_y
distance = sqrt(dx*dx + dy*dy)
```

If the robot is within 5 cm of the target, I request zero linear velocity. I check
this before normalizing the direction, which also avoids division by zero when
the robot is exactly at the target.

Otherwise, I choose:

```text
speed = min(requested_maximum_speed, 1.5 * distance)
vx = speed * dx / distance
vy = speed * dy / distance
```

The factor 1.5 has units of inverse seconds. At a distance of 0.20 m, the requested
speed is 0.30 m/s unless the caller selected a lower limit. Far away, it saturates
at the requested speed. Near the target, it decreases, making the approach gentler.

I bound total speed rather than independently bounding x and y. For a diagonal
movement at 1 m/s, both components are approximately 0.707 m/s. Setting both to
1 m/s would produce a combined speed of about 1.414 m/s and violate that limit.

## How I calculate rotation

I compare the requested absolute heading with the observed heading and wrap the
error into [-pi, pi). This chooses the shortest turn across the angle boundary.
For example, +178 degrees to -178 degrees requires a +4 degree turn, not -356.

I multiply angle error by a heading gain of 3/s and limit angular speed to 3 rad/s.
Within 3 degrees, I request zero rotation. I handle translation and rotation
independently, so arriving at the point does not stop an unfinished turn.
At exactly 180 degrees, I consistently choose the negative turn.

If a heading is omitted or unobserved, I request no rotation. Missing heading does
not crash my calculation, but the existing adapter needs a measured heading to
convert and transmit field-relative commands.

## Design decisions I can explain

- I used a proportional controller because it is small, understandable, and directly
  testable. I did not add reinforcement learning to a basic point-movement helper.
- I made the function stateless. New targets take effect on the next call without
  resetting anything, which matters when the ball respawns.
- I used physical units and field coordinates, matching the course API.
- I left the coordinate transformation to the adapter to avoid applying it twice.
- I kept ball handling out of my helper; the returned intent has no kick or dribbler.
- I validated inputs so malformed targets and invalid speeds fail clearly.
- I added tolerances to avoid chasing tiny position and heading errors indefinitely.

## What I tested

I wrote 18 standard-library unit tests covering axis directions, diagonal magnitude,
slowing down, stopping boundaries, translated coordinates, angle wraparound,
angular limits, turning at a reached position, zero-speed rotation, absent headings,
large angles, invalid inputs, stateless retargeting, no ball handling, and adapter
coordinate conversion. All 18 tests passed.

I then used the actual rSoccer physics backend for six scenarios: straight movement,
diagonal movement, turning in place, crossing the angle boundary, a slow approach,
and changing targets mid-run. All six after-trials remained inside both tolerances
for their final simulated second. A single moment of crossing the target would
not satisfy this check.

## Before/after evidence

In the diagonal trial, both runs started at (-1.0, -0.6) m, facing 180 degrees.
The requested target was (0.7, 0.6) m, facing 0 degrees.

| Observation | Supplied example | My movement controller |
|---|---:|---:|
| Final distance after 8 simulated seconds | 215.78 cm | 4.84 cm |
| Final absolute heading error | 113.11 degrees | 2.96 degrees |
| First time within both tolerances | Not reached | 3.35 seconds |
| Stayed within both tolerances during final second | No | Yes |

The baseline uses its original 0.8 m/s request and ignores the target; my controller
uses a 1 m/s limit. I use this comparison to show the difference between the supplied
demo and target-following behavior, not to claim a fair algorithm speed benchmark.
The chart is `results/movement/comparison.png`; raw data is beside it.

## Limitations and next steps

I have verified a point controller, not a complete striker. I do not plan collision-free
paths or prevent entry into the penalty area. The striker must supply suitable
waypoints and use infrared contact to decide when the ball is possessed.

My tolerances and gains are tested starting values. They are not proof of optimality
or guaranteed convergence under every collision or starting condition. I have not
added explicit acceleration limits, velocity feedback, or braking prediction.
Integration may expose cases that need further tuning.

The next milestone is for Member 2 to call my helper during approach and contact,
then for Member 4 to measure repeatable shooting performance. I will investigate
movement-specific failures from those runs.

## Suggested demonstration

1. I show the stable function signature and the movement/heading calculations.
2. I show the 18 passing checks.
3. I run the separate before/after movement demo and point out the marked target.
4. I show the measured chart and explain the comparison's limits.
5. I show how the striker adds dribbler behavior with `dataclasses.replace()`.
