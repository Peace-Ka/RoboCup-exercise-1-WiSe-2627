"""I verify the integrated striker's contact, carrying, and recovery contract."""

from dataclasses import replace
from math import atan2, hypot
import unittest

from ssl_strategy_api.models import BallState, FieldGeometry, RobotState, TeamColor, TeamConfig, WorldState
from ssl_strategy_api.strategies.striker import StrikerStrategy

FIELD = FieldGeometry(9.0, 6.0, 1.0)
CONFIG = TeamConfig(TeamColor.BLUE, (0,), 1)


def scene(robot_x=2.0, gap=0.1, keeper=False, infrared=False):
    robot=RobotState(0,robot_x,0,heading_rad=0,infrared=infrared)
    ball=BallState(robot_x+gap,0)
    opponents={0:RobotState(0,4.36,0,heading_rad=3.14159)} if keeper else {}
    state=WorldState(ball,{0:robot},opponents,FIELD,frame_number=0)
    return state


def align_to_shot(striker,state):
    target=striker._select_shot_target(state,CONFIG)
    heading=atan2(target[1]-state.ball.y_m,target[0]-state.ball.x_m)
    return replace(state,robots_blue={0:replace(state.robots_blue[0],heading_rad=heading)})


class StrikerTests(unittest.TestCase):
    def test_carrying_distance_does_not_authorize_early_kick(self):
        striker=StrikerStrategy()
        state=align_to_shot(striker,scene(robot_x=3.2,gap=0.12,keeper=True))
        striker._carrying=True
        intent=striker.decide(state,CONFIG)[0]
        self.assertEqual(intent.kick_speed_mps,0)
        self.assertTrue(intent.dribbler)
        self.assertGreater(hypot(intent.vx_mps,intent.vy_mps),0)

    def test_carrying_enables_dribbler(self):
        striker=StrikerStrategy()
        state=align_to_shot(striker,scene(keeper=True))
        intent=striker.decide(state,CONFIG)[0]
        self.assertTrue(striker._carrying)
        self.assertTrue(intent.dribbler)
        self.assertEqual(intent.kick_speed_mps,0)

    def test_contact_shot_turns_dribbler_off(self):
        striker=StrikerStrategy()
        intent=striker.decide(scene(infrared=True),CONFIG)[0]
        self.assertEqual(intent.kick_speed_mps,5)
        self.assertFalse(intent.dribbler)

    def test_no_repeat_kick_on_next_frame(self):
        striker=StrikerStrategy()
        state=scene(infrared=True)
        self.assertEqual(striker.decide(state,CONFIG)[0].kick_speed_mps,5)
        self.assertEqual(striker.decide(replace(state,frame_number=1),CONFIG)[0].kick_speed_mps,0)

    def test_respawn_clears_shot_latch(self):
        striker=StrikerStrategy()
        striker.decide(scene(infrared=True),CONFIG)
        new=replace(scene(robot_x=0.9,infrared=True),frame_number=1)
        self.assertEqual(striker.decide(new,CONFIG)[0].kick_speed_mps,5)

    def test_missing_ball_stops_and_clears_shot(self):
        striker=StrikerStrategy()
        state=scene(infrared=True)
        striker.decide(state,CONFIG)
        intent=striker.decide(replace(state,ball=None),CONFIG)[0]
        self.assertEqual((intent.vx_mps,intent.vy_mps,intent.angular_velocity_rad_s,intent.kick_speed_mps),(0,0,0,0))
        self.assertFalse(striker._kick_latched)

    def test_missing_robot_or_control_returns_no_commands(self):
        striker=StrikerStrategy()
        self.assertEqual(striker.decide(replace(scene(),robots_blue={}),CONFIG),{})
        self.assertEqual(striker.decide(scene(),replace(CONFIG,controlled_robot_ids=())),{})

    def test_misaligned_contact_turns_instead_of_shooting(self):
        striker=StrikerStrategy()
        state=scene(infrared=True)
        state=replace(state,robots_blue={0:replace(state.robots_blue[0],heading_rad=1.0)})
        intent=striker.decide(state,CONFIG)[0]
        self.assertEqual(intent.kick_speed_mps,0)
        self.assertTrue(intent.dribbler)
        self.assertLess(intent.angular_velocity_rad_s,0)


if __name__=='__main__':
    unittest.main()
