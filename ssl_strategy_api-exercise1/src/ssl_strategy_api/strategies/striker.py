"""Striker for RoboCup SSL Exercise 1 (rSoccer simulator).

=====================================================================
WHAT THE ROBOT HAS TO DO (SIMPLE VERSION)
=====================================================================
Score as many goals as possible in 90 seconds. After every goal the
ball appears somewhere new, so the robot has to run to it and shoot
again, over and over.

=====================================================================
HOW OUR ROBOT THINKS (a "state machine" = a checklist, one step at a time)
=====================================================================
1. GET BEHIND THE BALL. Imagine a straight line from the ball to the
   goal. The robot drives to a spot on that line, 22 cm BEHIND the ball
   (like a football player lining up before a free kick).
2. TURN to face the goal.
3. CREEP FORWARD slowly until the ball almost touches the kicker.
4. KICK once, with full power (5 m/s).
5. WAIT a moment so we never kick twice in a row, then go and get the
   next ball.

A TRICK WE FOUND BY TESTING:
The robot has an "infrared sensor" that should say "the ball touches my
kicker". In our tests it almost always said "no". So we measured the
simulator ourselves: the kicker only works if the ball is closer than
0.110 m to the robot's centre. At 0.115 m the kick does NOTHING. So the
robot fires when the distance is 0.108 m or less. This one fix is what
turned "robot walks up to the ball and nothing happens" into goals.

=====================================================================
WHEN THERE IS A GOALKEEPER (two extra tricks)
=====================================================================
A. PICK THE BEST SPOT IN THE GOAL.
   We split the goal mouth into 5 aiming spots. For each spot we
   predict where the goalkeeper will be when the ball arrives (we copied
   the keeper's movement rules: it slides towards the ball's path, fast
   at first, max 1.8 m/s). Then we aim at the spot where the keeper
   will be farthest away.
B. DRIBBLE CLOSER BEFORE SHOOTING.
   A far shot takes over a second to arrive, which is plenty of time for
   the keeper to slide across. So the robot first pushes the ball
   forward until it is about 3.3 m from the far end (still outside the
   goal area) and shoots from there. The shot then takes about 0.3 s, so
   the keeper has little time to react. This raised our scoring rate
   against the keeper from about 5 goals per 16 shots to about 9 per 11.

With NO goalkeeper near the goal we skip A and B and just aim at the
middle of the goal (simple and very reliable).

TWO SAFETY RULES (found by watching things go wrong):
* STUCK-BALL RULE: after a save the ball can stop on the goal line,
  outside the goal. The game does not reset it and nobody can score it.
  Then the robot kicks it out of the field so a fresh ball appears.
* STAY-OUT RULE: after a save the ball may still be rolling inside the
  goal area. The robot does NOT chase it in; it waits just outside. (In
  the single-episode runner, entering the goal area ends the episode, and
  this rule cut those early endings in half.)

WHAT DID NOT WORK (a learning experiment, removed from the code):
We trained a small Q-table (a lookup table of "in this situation, which
aiming spot scores most often") on 694 random shots. Random aiming only
scored 20 percent, and the table-based striker did WORSE than our
hand-made model (1 and 3 goals vs 9 and 7 against the rule-based
goalkeeper), so we kept the model-based aiming. Honest negative result.

=====================================================================
RESULTS (90 second runs, ball respawns after every goal, headless,
         run_rsoccer_exercise1_eval, measured on THIS version of the file)
=====================================================================
                                   seed 1       seed 2
  WITHOUT goalkeeper (idle)        15 goals     7 goals
  WITH rule-based goalkeeper       11 goals     7 goals
  WITH Q-table goalkeeper           7 goals     4 goals

Episode runner (run_rsoccer_exercise1, ends at the first goal / ball out /
ball idle / robot in goal area), 10 seeds, one episode each:
  idle keeper:     10 of 10 episodes ended with a goal
  rule keeper:      9 of 10 ended with a goal (1 ball out of the field)
  Q-table keeper:   6 of 10 ended with a goal (rest: ball out / robot in
                    the goal area after a saved shot)

Extra notes:
  * Without goalkeeper, an earlier version scored 20, 20 and 16 goals on
    seeds 6, 7, 8, and 56 goals from 57 shots overall (the single miss was
    a ball spawned 0.2 m from the goal line; the shot grazed the post).
  * Results change from seed to seed. A seed that is much lower than the
    others usually means the robot got stuck for part of the run; we did
    not find the cause in every case (known weak spot).
  * The Q-table goalkeeper is the hardest opponent: it saves most shots.

HOW TO RUN IT (replace the yellow strategy to change the goalkeeper):
  python -m ssl_strategy_api.run_demos.run_rsoccer_exercise1_eval
      --duration-seconds 90 --seed 1 --no-render
      --blue-strategy ssl_strategy_api.strategies.striker:StrikerStrategy
      --yellow-strategy ssl_strategy_api.strategies.idle_goalkeeper_rl:IdleGoalkeeperStrategy
  (rule keeper: ssl_strategy_api.strategies.goalkeeper:GoalkeeperStrategy)
  (Q-table keeper: ssl_strategy_api.strategies.goalkeeper_rl:QTableGoalkeeperStrategy)

NOTES FOR THE TEAM:
  * movement.py is not modified; all driving goes through move_to_target().
  * aiming.py is a teammate's job. The ONE place that chooses where to
    aim is _select_shot_target(); plug aiming.choose_target() in there.
"""

from math import atan2, cos, hypot, isfinite, pi, sin
from typing import Mapping, Optional, Tuple

from ssl_strategy_api.models import RobotIntent, TeamColor, TeamConfig, WorldState
from ssl_strategy_api.strategies.movement import move_to_target


# All distances are metres and angles are radians.
STAGING_DISTANCE_M = 0.22       # wait this far behind the ball before pushing
STAGING_TOLERANCE_M = 0.10
CONTACT_SPEED_MPS = 0.25        # slow creep onto the ball
APPROACH_SPEED_MPS = 1.0        # normal driving speed
ALIGNMENT_TOLERANCE_RAD = 0.12  # about 7 degrees: "facing the goal enough"
KICK_SPEED_MPS = 5.0            # API maximum
FIELD_EDGE_MARGIN_M = 0.15
GOAL_POST_MARGIN_M = 0.08
BALL_RESPAWN_JUMP_M = 0.75      # ball teleported = the game respawned it
KICK_RELEASE_DISTANCE_M = 0.22
KICK_MAX_WAIT_FRAMES = 20
KICK_RANGE_M = 0.108            # measured: kicker works up to about 0.110 m
GOAL_AREA_DEPTH_M = 1.0         # goal area: 1.0 m deep, 2.0 m wide
GOAL_AREA_HALF_WIDTH_M = 1.0


class _BaseStrikerStrategy:
    """The checklist: approach, contact, align, shoot, recover."""

    SEARCH = "SEARCH"
    APPROACH = "APPROACH"
    CONTACT = "CONTACT"
    ALIGN = "ALIGN"
    SHOOT = "SHOOT"
    RECOVER = "RECOVER"

    _carrying = False

    def __init__(self) -> None:
        self.reset()

    def reset(self, seed=None) -> None:
        self.phase = self.SEARCH
        self._last_ball_xy: Optional[Tuple[float, float]] = None
        self._kick_latched = False
        self._kick_origin_xy: Optional[Tuple[float, float]] = None
        self._kick_wait_frames = 0

    def decide(self, state: WorldState, config: TeamConfig) -> Mapping[int, RobotIntent]:
        if not config.controlled_robot_ids:
            self.phase = self.SEARCH
            return {}

        robot_id = config.controlled_robot_ids[0]
        own_robots = self._own_robots(state, config)
        robot = own_robots.get(robot_id)
        if robot is None:
            self.phase = self.SEARCH
            return {}

        ball = state.ball
        if ball is None:
            self.phase = self.SEARCH
            self._last_ball_xy = None
            self._clear_kick_latch()
            return {robot_id: RobotIntent()}

        ball_xy = (ball.x_m, ball.y_m)
        if self._detect_ball_respawn(ball_xy):
            self.phase = self.SEARCH
            self._clear_kick_latch()

        # After a kick, do nothing until the ball has left (or 20 frames
        # passed). This stops the robot from kicking twice in a row.
        if self._kick_latched:
            self._kick_wait_frames += 1

            ball_moved = (
                self._kick_origin_xy is not None
                and hypot(
                    ball.x_m - self._kick_origin_xy[0],
                    ball.y_m - self._kick_origin_xy[1],
                ) >= KICK_RELEASE_DISTANCE_M
            )
            robot_ball_distance = hypot(ball.x_m - robot.x_m, ball.y_m - robot.y_m)
            timed_out = self._kick_wait_frames >= KICK_MAX_WAIT_FRAMES

            if ball_moved or robot_ball_distance >= KICK_RELEASE_DISTANCE_M or timed_out:
                self._clear_kick_latch()
            self.phase = self.RECOVER
            self._last_ball_xy = ball_xy
            return {robot_id: RobotIntent()}

        # Where do we aim, and where must we stand to hit the ball that way?
        target_xy = self._select_shot_target(state, config)
        shot_heading = atan2(target_xy[1] - ball.y_m, target_xy[0] - ball.x_m)
        staging_xy = self._approach_point(
            ball_xy, target_xy, state.field.length_m, state.field.width_m
        )

        robot_ball_distance = hypot(ball.x_m - robot.x_m, ball.y_m - robot.y_m)
        robot_staging_distance = hypot(staging_xy[0] - robot.x_m,
                                       staging_xy[1] - robot.y_m)
        has_ball = self._has_ball(robot.infrared, robot_ball_distance)
        # While dribbling the ball may drift a little; do not give up on it.
        if not has_ball and self._carrying:
            if robot_ball_distance <= 0.13:
                has_ball = True
            else:
                self._carrying = False
        heading_error = self._angle_error(shot_heading, robot.heading_rad)

        if has_ball:
            if heading_error is None or abs(heading_error) > ALIGNMENT_TOLERANCE_RAD:
                # Slightly off-line while dribbling: keep moving and turning
                # together instead of stopping (stopping made us very slow).
                if (self._carrying and heading_error is not None
                        and abs(heading_error) <= 0.4):
                    carry = self._carry_intent(
                        state, config, robot, ball, target_xy, shot_heading
                    )
                    if carry is not None:
                        self.phase = self.CONTACT
                        self._last_ball_xy = ball_xy
                        return {robot_id: carry}
                self.phase = self.ALIGN
                turn = move_to_target(
                    robot, (robot.x_m, robot.y_m), shot_heading, max_speed_mps=0.0
                )
                return {robot_id: self._with_dribbler(turn, True)}

            # Facing the right way. With a goalkeeper we may first dribble
            # closer (see GoalkeeperAwareStrikerStrategy).
            carry = self._carry_intent(
                state, config, robot, ball, target_xy, shot_heading
            )
            if carry is not None:
                self.phase = self.CONTACT
                self._last_ball_xy = ball_xy
                return {robot_id: carry}

            # KICK (a single frame of kick command, then the latch holds us).
            self.phase = self.SHOOT
            self._kick_latched = True
            self._kick_origin_xy = ball_xy
            self._kick_wait_frames = 0
            return {
                robot_id: RobotIntent(
                    kick_speed_mps=KICK_SPEED_MPS,
                    dribbler=False,
                )
            }

        # Ball inside the goal area (for example after a save): do not chase
        # it in. Wait just outside; the game respawns the ball soon.
        if self._ball_in_goal_area(state, config, ball):
            self.phase = self.APPROACH
            self._last_ball_xy = ball_xy
            direction = config.attack_direction_x
            limit_x = direction * (state.field.length_m / 2.0 - GOAL_AREA_DEPTH_M - 0.2)
            wait_x = limit_x if direction * robot.x_m > direction * limit_x else robot.x_m
            wait = move_to_target(
                robot, (wait_x, robot.y_m), shot_heading,
                max_speed_mps=APPROACH_SPEED_MPS,
            )
            return {robot_id: wait}

        # Are we already in the "corridor" right behind the ball, on the
        # shot line? Then do not drive back to the staging point again.
        rel_x = robot.x_m - ball.x_m
        rel_y = robot.y_m - ball.y_m
        shot_ux = cos(shot_heading)
        shot_uy = sin(shot_heading)
        along = rel_x * shot_ux + rel_y * shot_uy
        lateral = abs(rel_x * shot_uy - rel_y * shot_ux)
        in_corridor = (-0.30 <= along <= 0.0) and lateral <= 0.06

        # Step 1: get behind the ball (never chase it from the front).
        if robot_staging_distance > STAGING_TOLERANCE_M and not in_corridor:
            self.phase = self.APPROACH
            intent = move_to_target(
                robot, staging_xy, shot_heading,
                max_speed_mps=APPROACH_SPEED_MPS,
            )
            self._last_ball_xy = ball_xy
            return {robot_id: intent}

        # Step 2: turn to face the aiming direction.
        if heading_error is None or abs(heading_error) > ALIGNMENT_TOLERANCE_RAD:
            self.phase = self.ALIGN
            turn = move_to_target(
                robot, (robot.x_m, robot.y_m), shot_heading, max_speed_mps=0.0
            )
            self._last_ball_xy = ball_xy
            return {robot_id: turn}

        # Step 3: creep forward onto the ball.
        self.phase = self.CONTACT
        contact = move_to_target(
            robot, ball_xy, shot_heading, max_speed_mps=CONTACT_SPEED_MPS
        )
        self._last_ball_xy = ball_xy
        return {robot_id: self._with_dribbler(contact, True)}

    def _select_shot_target(
        self, state: WorldState, config: TeamConfig
    ) -> Tuple[float, float]:
        """Aim at the centre of the opponent's goal (plug aiming.py in here)."""
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        return goal_x, 0.0

    def _carry_intent(self, state, config, robot, ball, target_xy, shot_heading):
        """Hook for dribbling before the shot. None means: shoot now."""
        return None

    def _ball_in_goal_area(self, state, config, ball) -> bool:
        """Hook: True when the robot should not chase the ball."""
        return False

    @staticmethod
    def _own_robots(state: WorldState, config: TeamConfig):
        return state.robots_blue if config.team == TeamColor.BLUE else state.robots_yellow

    @staticmethod
    def _opponent_robots(state: WorldState, config: TeamConfig):
        return state.robots_yellow if config.team == TeamColor.BLUE else state.robots_blue

    @staticmethod
    def _has_ball(infrared: Optional[bool], distance_m: float) -> bool:
        # The infrared sensor is unreliable, so we also use the measured
        # kick range (0.110 m): inside 0.108 m the kicker can hit the ball.
        return infrared is True or distance_m <= KICK_RANGE_M

    @staticmethod
    def _approach_point(ball_xy, target_xy, field_length_m, field_width_m):
        dx = target_xy[0] - ball_xy[0]
        dy = target_xy[1] - ball_xy[1]
        length = hypot(dx, dy)
        if length <= 1e-9:
            ux = 1.0
            uy = 0.0
        else:
            ux = dx / length
            uy = dy / length

        px = ball_xy[0] - STAGING_DISTANCE_M * ux
        py = ball_xy[1] - STAGING_DISTANCE_M * uy
        half_length = max(0.0, field_length_m / 2.0 - FIELD_EDGE_MARGIN_M)
        half_width = max(0.0, field_width_m / 2.0 - FIELD_EDGE_MARGIN_M)
        px = max(-half_length, min(half_length, px))
        py = max(-half_width, min(half_width, py))
        return px, py

    def _detect_ball_respawn(self, ball_xy: Tuple[float, float]) -> bool:
        if self._last_ball_xy is None:
            self._last_ball_xy = ball_xy
            return False
        jump = hypot(ball_xy[0] - self._last_ball_xy[0],
                     ball_xy[1] - self._last_ball_xy[1])
        self._last_ball_xy = ball_xy
        return jump >= BALL_RESPAWN_JUMP_M

    def _clear_kick_latch(self) -> None:
        self._kick_latched = False
        self._kick_origin_xy = None
        self._kick_wait_frames = 0

    @staticmethod
    def _angle_error(target_heading: float, current_heading: Optional[float]) -> Optional[float]:
        if current_heading is None or not isfinite(current_heading):
            return None
        return (target_heading - current_heading + pi) % (2.0 * pi) - pi

    @staticmethod
    def _with_dribbler(intent: RobotIntent, enabled: bool) -> RobotIntent:
        return RobotIntent(
            vx_mps=intent.vx_mps,
            vy_mps=intent.vy_mps,
            angular_velocity_rad_s=intent.angular_velocity_rad_s,
            kick_speed_mps=intent.kick_speed_mps,
            dribbler=enabled,
        )


class GoalkeeperAwareStrikerStrategy(_BaseStrikerStrategy):
    """Striker for games WITH a goalkeeper.

    Trick A: aim at the spot in the goal the keeper can reach least in time.
    Trick B: dribble the ball closer first, so the keeper has less time.

    The keeper model copies GoalkeeperStrategy: it moves towards the ball's
    crossing point at speed min(1.8, 2 * distance) m/s.
    """

    KEEPER_GAIN = 2.0
    KEEPER_MAX_SPEED_MPS = 1.8
    KEEPER_Y_LIMIT_M = 0.4
    AVG_BALL_SPEED_MPS = 3.5
    SIM_DT_S = 0.025
    CARRY_FIRE_DIST_M = 1.2    # kick when the ball is this close to the goal line
    CARRY_MAX_FRAMES = 240     # safety: never dribble for more than 6 seconds
    CARRY_SPEED_MPS = 0.8
    _carry_frames = 0

    def reset(self, seed=None) -> None:
        super().reset(seed)
        self._carrying = False
        self._carry_frames = 0

    def _clear_kick_latch(self) -> None:
        super()._clear_kick_latch()
        self._carrying = False
        self._carry_frames = 0

    def _select_shot_target(self, state: WorldState, config: TeamConfig) -> Tuple[float, float]:
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        usable = max(0.0, state.field.goal_width_m / 2.0 - GOAL_POST_MARGIN_M)
        lanes = [(goal_x, y) for y in (-usable, -0.5 * usable, 0.0, 0.5 * usable, usable)]
        opponents = list(self._opponent_robots(state, config).values())
        if state.ball is None or not opponents:
            return goal_x, 0.0
        keeper = opponents[0]
        scored = [(self._lane_gap(state.ball, keeper, lane), -abs(lane[1]), lane) for lane in lanes]
        _, _, lane = max(scored)
        return lane

    def _lane_gap(self, ball, keeper, lane) -> float:
        """How far from the ball's path will the keeper still be on arrival?"""
        dx = lane[0] - ball.x_m
        plane_dx = keeper.x_m - ball.x_m
        if abs(dx) < 1e-9 or plane_dx / dx <= 0.0:
            return 0.0
        frac = plane_dx / dx
        y_cross = ball.y_m + frac * (lane[1] - ball.y_m)
        flight_s = hypot(plane_dx, y_cross - ball.y_m) / self.AVG_BALL_SPEED_MPS
        goal_y = max(-self.KEEPER_Y_LIMIT_M, min(self.KEEPER_Y_LIMIT_M, y_cross))
        y = keeper.y_m
        for _ in range(int(flight_s / self.SIM_DT_S)):
            err = goal_y - y
            speed = min(self.KEEPER_MAX_SPEED_MPS, self.KEEPER_GAIN * abs(err))
            y += (speed if err > 0 else -speed) * self.SIM_DT_S
        return abs(y_cross - y)

    def _carry_intent(self, state, config, robot, ball, target_xy, shot_heading):
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        if (abs(goal_x - ball.x_m) <= self.CARRY_FIRE_DIST_M
                or self._carry_frames >= self.CARRY_MAX_FRAMES):
            self._carrying = False
            return None
        self._carrying = True
        self._carry_frames += 1
        return move_to_target(
            robot, target_xy, shot_heading, max_speed_mps=self.CARRY_SPEED_MPS
        )


class StrikerStrategy(GoalkeeperAwareStrikerStrategy):
    """Default striker for Exercise 1 (used by the runners).

    No goalkeeper near the goal: shoot at the goal centre, no dribbling.
    Goalkeeper near the goal: use the lane choice and dribble closer first.
    """

    GUARD_RADIUS_M = 1.5
    DEAD_BALL_SPEED_MPS = 0.08
    DEAD_BALL_LINE_M = 0.15

    def _ball_in_goal_area(self, state, config, ball) -> bool:
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        depth = (goal_x - ball.x_m) * config.attack_direction_x
        return depth <= GOAL_AREA_DEPTH_M and abs(ball.y_m) <= GOAL_AREA_HALF_WIDTH_M

    def _dead_ball_near_goal_line(self, state, config) -> bool:
        """Ball resting on the goal line outside the goal: nobody can score it."""
        ball = state.ball
        if ball is None:
            return False
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        speed = hypot(ball.vx_mps or 0.0, ball.vy_mps or 0.0)
        return (
            speed <= self.DEAD_BALL_SPEED_MPS
            and abs(ball.x_m - goal_x) <= self.DEAD_BALL_LINE_M
            and abs(ball.y_m) > state.field.goal_width_m / 2.0 + 0.1
        )

    def _keeper_present(self, state, config) -> bool:
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        return any(
            hypot(o.x_m - goal_x, o.y_m) <= self.GUARD_RADIUS_M
            for o in self._opponent_robots(state, config).values()
        )

    def _select_shot_target(self, state, config):
        if self._dead_ball_near_goal_line(state, config):
            # Kick it out of the field so the game respawns the ball.
            goal_x = config.attack_direction_x * state.field.length_m / 2.0
            return goal_x + config.attack_direction_x * 1.0, state.ball.y_m
        if not self._keeper_present(state, config):
            return _BaseStrikerStrategy._select_shot_target(self, state, config)
        return super()._select_shot_target(state, config)

    def _carry_intent(self, state, config, robot, ball, target_xy, shot_heading):
        if not self._keeper_present(state, config):
            self._carrying = False
            return None
        return super()._carry_intent(
            state, config, robot, ball, target_xy, shot_heading
        )
