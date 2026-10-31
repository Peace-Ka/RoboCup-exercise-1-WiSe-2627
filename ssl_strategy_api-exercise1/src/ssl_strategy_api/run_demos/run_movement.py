"""I compare the supplied starter motion with my controller in rSoccer.

Run: python -m ssl_strategy_api.run_demos.run_movement --no-render
The default visual comparison shows the same start/target before and after.
"""

import argparse
import csv
import json
from math import ceil, cos, degrees, hypot, isfinite, pi, sin
from pathlib import Path
import time

import pygame
from rsoccer_gym.Entities import Ball, Frame, Robot
from rsoccer_gym.ssl.ssl_gym_base import SSLBaseEnv

from ssl_strategy_api.models import FieldGeometry, RobotIntent, TeamColor, TeamConfig
from ssl_strategy_api.adapters.rsoccer import to_rsoccer_commands, world_state_from_rsoccer_frame
from ssl_strategy_api.strategies.movement import (
    HEADING_TOLERANCE_RAD, POSITION_TOLERANCE_M, move_to_target,
)


STEP_SECONDS = 0.025
SCENARIOS = {
    'diagonal': ((-1.0, -0.6, 180.0), (0.7, 0.6), 0.0, 1.0),
    'straight': ((-1.0, 0.0, 90.0), (0.7, 0.0), 0.0, 1.0),
    'turn-only': ((0.0, 0.0, 0.0), (0.0, 0.0), pi / 2, 0.0),
    'angle-wrap': ((0.0, 0.0, 178.0), (0.0, 0.0), -178 * pi / 180, 0.0),
    'slow-contact': ((-0.5, 0.0, 0.0), (0.0, 0.0), 0.0, 0.2),
    'retarget': ((-1.0, -0.6, 180.0), (0.7, 0.6), 0.0, 1.0),
}


class MovementEnv(SSLBaseEnv):
    """I keep the ball/opponent away to isolate point movement and heading."""

    def __init__(self, start, render=False):
        self.start = start
        super().__init__(field_type=1, n_robots_blue=1, n_robots_yellow=1,
                         time_step=STEP_SECONDS, render_mode='human' if render else None)
        self.geometry = FieldGeometry(self.field.length, self.field.width, self.field.goal_width)

    def _get_commands(self, action):
        return action

    def _frame_to_observations(self):
        return world_state_from_rsoccer_frame(self.frame, self.geometry, frame_number=self.steps)

    def _calculate_reward_and_done(self):
        return 0.0, False

    def _get_initial_positions_frame(self):
        frame = Frame()
        x, y, heading = self.start
        frame.ball = Ball(x=-1.8, y=1.6)
        frame.robots_blue[0] = Robot(yellow=False, id=0, x=x, y=y, theta=heading)
        frame.robots_yellow[0] = Robot(yellow=True, id=0, x=1.8, y=-1.6, theta=180)
        return frame


def run_trial(mode, scenario, duration, render):
    start, initial_target, heading, speed = SCENARIOS[scenario]
    env = MovementEnv(start, render)
    config = TeamConfig(TeamColor.BLUE, (0,), 1)
    rows = []
    target = initial_target
    switched = False
    reached = None
    max_command_speed = 0.0
    max_command_turn = 0.0
    try:
        state, _ = env.reset(seed=1)
        for step in range(ceil(duration / STEP_SECONDS) + 1):
            tick = time.monotonic()
            seconds = step * STEP_SECONDS
            if scenario == 'retarget' and seconds >= duration / 2 and not switched:
                target = (-0.5, 0.3)
                switched = True
                reached = None
            robot = state.robots_blue[0]
            distance = hypot(target[0] - robot.x_m, target[1] - robot.y_m)
            angle_error = (heading - robot.heading_rad + pi) % (2*pi) - pi
            if reached is None and distance <= POSITION_TOLERANCE_M and abs(angle_error) <= HEADING_TOLERANCE_RAD:
                reached = seconds
            rows.append(dict(mode=mode, scenario=scenario, time_s=seconds,
                             x_m=robot.x_m, y_m=robot.y_m, target_x_m=target[0], target_y_m=target[1],
                             distance_m=distance, heading_error_deg=degrees(angle_error)))
            if render:
                pygame.display.set_caption(f'Movement {mode.upper()} | {scenario} | error {distance:.3f} m')
                # I draw the target and tolerance on the simulator field.
                renderer = env.field_renderer
                center = (int(target[0] * renderer.scale + renderer.center_x),
                          int(target[1] * renderer.scale + renderer.center_y))
                pygame.draw.circle(env.window_surface, (255, 255, 255), center,
                                   max(3, int(POSITION_TOLERANCE_M * renderer.scale)), 2)
                pygame.draw.line(env.window_surface, (255, 255, 255),
                                 (center[0]-8, center[1]), (center[0]+8, center[1]), 2)
                pygame.draw.line(env.window_surface, (255, 255, 255),
                                 (center[0], center[1]-8), (center[0], center[1]+8), 2)
                pygame.display.flip()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt
            if step * STEP_SECONDS >= duration:
                break
            if mode == 'before':
                # I retain the original example here so Member 2 can change striker.py.
                theta = state.frame_number * 0.1 if state.frame_number is not None else 0.0
                intents = {0: RobotIntent(vx_mps=0.8*cos(theta), vy_mps=0.8*sin(theta),
                                         angular_velocity_rad_s=1.0)}
            else:
                intents = {0: move_to_target(robot, target, heading, max_speed_mps=speed)}
            command = intents[0]
            max_command_speed = max(max_command_speed, hypot(command.vx_mps, command.vy_mps))
            max_command_turn = max(max_command_turn, abs(command.angular_velocity_rad_s))
            state, _, _, _, _ = env.step(to_rsoccer_commands(state, config, intents))
            if render:
                time.sleep(max(0.0, STEP_SECONDS - (time.monotonic() - tick)))
    finally:
        env.close()
    tail = rows[-min(40, len(rows)):]
    result = dict(mode=mode, scenario=scenario, duration_s=duration,
                  final_distance_m=rows[-1]['distance_m'],
                  final_heading_error_deg=rows[-1]['heading_error_deg'],
                  first_reached_s=reached,
                  settled_last_second=all(r['distance_m'] <= POSITION_TOLERANCE_M
                                         and abs(r['heading_error_deg']) <= degrees(HEADING_TOLERANCE_RAD)
                                         for r in tail),
                  max_command_speed_mps=max_command_speed, max_command_turn_rad_s=max_command_turn)
    print(json.dumps(result), flush=True)
    return rows, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--mode', choices=['before', 'after', 'compare'], default='compare')
    parser.add_argument('--scenario', choices=[*SCENARIOS, 'all'], default='diagonal')
    parser.add_argument('--duration-seconds', type=float, default=8.0)
    parser.add_argument('--output-dir', type=Path, default=Path('results/movement'))
    args = parser.parse_args()
    if not isfinite(args.duration_seconds) or args.duration_seconds < 2:
        parser.error('--duration-seconds must be finite and at least 2')
    modes = ['before', 'after'] if args.mode == 'compare' else [args.mode]
    scenarios = list(SCENARIOS) if args.scenario == 'all' else [args.scenario]
    rows, summary = [], []
    try:
        for scenario in scenarios:
            for mode in modes:
                trial_rows, result = run_trial(mode, scenario, args.duration_seconds, args.render)
                rows.extend(trial_rows)
                summary.append(result)
    except KeyboardInterrupt:
        print('Movement demonstration stopped.')
        return 130
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'trajectory.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    # I make failed controller trials visible to automated checks, without grading the starter.
    return 1 if any(r['mode'] == 'after' and not r['settled_last_second'] for r in summary) else 0


if __name__ == '__main__':
    raise SystemExit(main())
