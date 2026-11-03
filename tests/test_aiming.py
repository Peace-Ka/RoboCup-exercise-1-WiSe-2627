"""Aiming tests that do not need the simulator."""

import unittest

from ssl_strategy_api.models import (
    BallState, FieldGeometry, RobotState, TeamColor, TeamConfig, VelocitySource, WorldState,
)
from ssl_strategy_api.strategies.aiming import KeeperModel, LearnedAimer, choose_target

FIELD = FieldGeometry(length_m=9.0, width_m=6.0, goal_width_m=1.0)
BLUE = TeamConfig(team=TeamColor.BLUE, controlled_robot_ids=(0,), attack_direction_x=1)


def world(ball_xy, keeper_xy=None, ball_v=None, frame=0):
    ball = BallState(ball_xy[0], ball_xy[1])
    if ball_v is not None:
        ball = BallState(ball_xy[0], ball_xy[1], ball_v[0], ball_v[1], VelocitySource.MEASURED)
    yellow = {}
    if keeper_xy is not None:
        yellow = {0: RobotState(0, keeper_xy[0], keeper_xy[1], heading_rad=3.14159)}
    return WorldState(ball, {0: RobotState(0, 0.0, 0.0, 0.0)}, yellow, FIELD, frame_number=frame)


class AimingTests(unittest.TestCase):
    def test_no_keeper_aims_at_centre(self):
        self.assertEqual(choose_target(world((2.0, 1.0)), BLUE), (4.5, 0.0))

    def test_target_stays_inside_posts(self):
        x, y = choose_target(world((3.0, 0.0), keeper_xy=(4.36, 0.0)), BLUE)
        self.assertEqual(x, 4.5)
        self.assertLess(abs(y), FIELD.goal_width_m / 2.0)

    def test_aims_away_from_keeper(self):
        _, y = choose_target(world((3.0, 0.0), keeper_xy=(4.36, 0.35)), BLUE)
        self.assertLess(y, 0.0)
        _, y = choose_target(world((3.0, 0.0), keeper_xy=(4.36, -0.35)), BLUE)
        self.assertGreater(y, 0.0)

    def test_attacking_left_goal(self):
        config = TeamConfig(team=TeamColor.BLUE, controlled_robot_ids=(0,), attack_direction_x=-1)
        x, _ = choose_target(world((-3.0, 0.0), keeper_xy=(-4.36, 0.0)), config)
        self.assertEqual(x, -4.5)

    def test_prediction_respects_speed_limit(self):
        model = KeeperModel()
        y = model.keeper_y_after(0.0, 10.0, 0.5)
        self.assertLessEqual(y, model.v_max_mps * 0.5 + 1e-9)
        self.assertLessEqual(y, model.y_limit_m + 1e-9)

    def test_learns_a_slow_keeper(self):
        """A keeper that moves at 0.8 m/s should lower the learned v_max."""
        aimer = LearnedAimer()
        keeper_y = 0.0
        for frame in range(200):
            # Ball flies toward the goal along y = -0.3, keeper chases at 0.8 m/s.
            state = world((2.0, -0.3), keeper_xy=(4.36, keeper_y), ball_v=(4.0, 0.0), frame=frame)
            aimer.observe(state, BLUE)
            keeper_y = max(-0.3, keeper_y - 0.8 * 0.025)
            if frame % 20 == 19:
                keeper_y = 0.0        # new shot: keeper back in the centre
        self.assertLess(aimer.model.v_max_mps, 1.5)
        self.assertGreater(len(aimer.model.samples), 50)

    def test_skipped_frames_are_ignored(self):
        aimer = LearnedAimer()
        for frame in (0, 5, 10):
            aimer.observe(world((2.0, -0.3), (4.36, 0.0), (4.0, 0.0), frame), BLUE)
        self.assertEqual(aimer.model.samples, [])

    def test_no_learning_when_disabled(self):
        aimer = LearnedAimer(learn=False)
        for frame in range(10):
            aimer.observe(world((2.0, -0.3), (4.36, -0.02 * frame), (4.0, 0.0), frame), BLUE)
        self.assertEqual(aimer.model.samples, [])


if __name__ == "__main__":
    unittest.main()
