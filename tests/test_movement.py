"""I check the movement contract without requiring the simulator."""

from dataclasses import replace
from math import hypot, pi, radians
import unittest

from ssl_strategy_api.models import RobotState
from ssl_strategy_api.adapters.rsoccer import rsoccer_command_payloads
from ssl_strategy_api.models import FieldGeometry, TeamColor, TeamConfig, WorldState
from ssl_strategy_api.strategies.movement import move_to_target


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.robot = RobotState(0, 0.0, 0.0, heading_rad=0.0)

    def test_axis_directions(self):
        for target in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            with self.subTest(target=target):
                intent = move_to_target(self.robot, target)
                self.assertAlmostEqual(intent.vx_mps, target[0])
                self.assertAlmostEqual(intent.vy_mps, target[1])

    def test_diagonal_speed_limit(self):
        for speed in [0, 0.1, 0.4, 1, 2]:
            for target in [(10, 10), (-10, 10), (10, -10), (-10, -10)]:
                with self.subTest(speed=speed, target=target):
                    intent = move_to_target(self.robot, target, max_speed_mps=speed)
                    self.assertAlmostEqual(hypot(intent.vx_mps, intent.vy_mps), speed)
                    self.assertAlmostEqual(intent.vx_mps / target[0], intent.vy_mps / target[1])

    def test_stops_at_and_within_tolerance(self):
        for target in [(0, 0), (0.01, 0), (0.05, 0), (-0.05, 0)]:
            with self.subTest(target=target):
                intent = move_to_target(self.robot, target)
                self.assertEqual((intent.vx_mps, intent.vy_mps), (0, 0))
        self.assertGreater(move_to_target(self.robot, (0.05001, 0)).vx_mps, 0)

    def test_slows_near_target(self):
        velocities = [move_to_target(self.robot, (d, 0)).vx_mps for d in [0.1, 0.2, 0.4, 2]]
        self.assertEqual(velocities, sorted(velocities))
        self.assertAlmostEqual(velocities[0], 0.15)

    def test_uses_position_error_not_absolute_target(self):
        shifted = replace(self.robot, x_m=2, y_m=-3)
        self.assertEqual(move_to_target(shifted, (3, -2)), move_to_target(self.robot, (1, 1)))

    def test_shortest_turn_across_angle_boundary(self):
        for current, target, sign in [(178, -178, 1), (-178, 178, -1)]:
            # I check a 4-degree correction beyond the 3-degree tolerance.
            robot = replace(self.robot, heading_rad=radians(current))
            intent = move_to_target(robot, (0, 0), radians(target))
            self.assertAlmostEqual(intent.angular_velocity_rad_s, sign * 3 * radians(4))

    def test_small_wraparound_turn_is_already_aligned(self):
        robot = replace(self.robot, heading_rad=radians(179))
        self.assertEqual(move_to_target(robot, (0, 0), radians(-179)).angular_velocity_rad_s, 0)

    def test_angular_limit_and_half_turn_tie(self):
        self.assertEqual(move_to_target(self.robot, (0, 0), pi).angular_velocity_rad_s, -3)
        self.assertEqual(move_to_target(self.robot, (0, 0), pi / 2).angular_velocity_rad_s, 3)

    def test_rotation_continues_at_position_target(self):
        intent = move_to_target(self.robot, (0, 0), pi / 2)
        self.assertEqual((intent.vx_mps, intent.vy_mps), (0, 0))
        self.assertGreater(intent.angular_velocity_rad_s, 0)

    def test_zero_speed_still_allows_turning(self):
        intent = move_to_target(self.robot, (1, 1), pi / 2, max_speed_mps=0)
        self.assertEqual((intent.vx_mps, intent.vy_mps), (0, 0))
        self.assertGreater(intent.angular_velocity_rad_s, 0)

    def test_missing_or_aligned_heading(self):
        for robot, heading in [(self.robot, None), (replace(self.robot, heading_rad=None), 1),
                               (self.robot, 0), (self.robot, radians(2))]:
            with self.subTest(robot=robot, heading=heading):
                intent = move_to_target(robot, (1, 0), heading)
                self.assertEqual(intent.angular_velocity_rad_s, 0)
                self.assertGreater(intent.vx_mps, 0)

    def test_equivalent_and_large_headings(self):
        self.assertEqual(move_to_target(self.robot, (0, 0), 20*pi).angular_velocity_rad_s, 0)
        intent = move_to_target(self.robot, (0, 0), 1e308)
        self.assertLessEqual(abs(intent.angular_velocity_rad_s), 3)

    def test_no_ball_handling_or_hidden_state(self):
        first = move_to_target(self.robot, (1, 0))
        move_to_target(self.robot, (-1, 0), pi)
        self.assertEqual(first, move_to_target(self.robot, (1, 0)))
        self.assertEqual(first.kick_speed_mps, 0)
        self.assertIs(first.dribbler, False)
        self.assertLess(move_to_target(self.robot, (-1, 0)).vx_mps, 0)

    def test_invalid_speed(self):
        for speed in [-1, 2.01, float('nan'), float('inf'), 'fast', None]:
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                move_to_target(self.robot, (1, 0), max_speed_mps=speed)

    def test_invalid_target(self):
        for target in [None, (), (1,), (1, 2, 3), ('x', 0), (float('nan'), 0), (0, float('inf'))]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                move_to_target(self.robot, target)

    def test_invalid_heading(self):
        for heading in [float('nan'), float('inf'), 'north']:
            with self.subTest(heading=heading), self.assertRaises(ValueError):
                move_to_target(self.robot, (0, 0), heading)

    def test_overflowing_displacement(self):
        robot = replace(self.robot, x_m=-1e308)
        with self.assertRaises(ValueError):
            move_to_target(robot, (1e308, 0))

    def test_adapter_rotates_field_velocity_exactly_once(self):
        robot = replace(self.robot, heading_rad=pi/2)
        state = WorldState(None, {0: robot}, {}, FieldGeometry(9, 6, 1))
        config = TeamConfig(TeamColor.BLUE, (0,), 1)
        intent = move_to_target(robot, (1, 0))
        payload = rsoccer_command_payloads(state, config, {0: intent})[0]
        self.assertAlmostEqual(intent.vx_mps, 1)
        self.assertAlmostEqual(payload['v_x'], 0)
        self.assertAlmostEqual(payload['v_y'], -1)


if __name__ == '__main__':
    unittest.main()
