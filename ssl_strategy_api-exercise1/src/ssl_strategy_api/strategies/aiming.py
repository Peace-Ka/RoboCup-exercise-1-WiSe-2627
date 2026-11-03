"""Shot aiming for Exercise 1 (Member 3: MJ).

=====================================================================
IDEA
=====================================================================
A shot is good when the goalkeeper cannot reach the ball's path in
time. So for every aiming spot in the goal mouth we PREDICT where the
keeper will be when the ball passes it, and aim where the predicted gap
between keeper and ball is largest.

The prediction needs a model of the opponent keeper:

    keeper speed toward its target = min(v_max, gain * distance_to_target)
    keeper target                  = where the ball path crosses its line,
                                     clamped to +/- y_limit
    ball flight time               = distance / average_ball_speed

=====================================================================
WHAT IS LEARNED (online, while the match is running)
=====================================================================
We do not hard-code the keeper. ``KeeperModel`` starts from a prior and
fits the four parameters (gain, v_max, y_limit, average ball speed) from
what it observes during every shot:

* every frame where the ball flies toward the goal gives one sample
  (distance keeper -> ball path, keeper speed toward it);
* gain and v_max are fitted together to speed = min(v_max, gain * d)
  by a maximum-a-posteriori grid search (least squares + a Gaussian
  prior). If the keeper never reaches top speed, the data cannot
  identify v_max and the prior keeps it sensible;
* y_limit = largest |y| the keeper reached during shots (never below the
  prior, never beyond the goal half-width);
* ball speed = mean observed ball speed during shots.

Each estimate is blended with the prior, weighted by how many samples we
have (a simple Bayesian-style shrinkage), so the model is safe at kick-off
and becomes opponent-specific after a few shots. Against a slow keeper
(e.g. the Q-table keeper moves at 0.8 m/s) the learned model sees that
more spots are reachable for us and aims more aggressively.

The striker calls ``LearnedAimer.choose_target`` every frame; the aimer
also uses those calls to observe the keeper.

=====================================================================
RESULTS (90 s, run_rsoccer_exercise1_eval, headless, seeds 1-6)
=====================================================================
                        fixed prior model     learned model
  rule-based keeper     45 goals              43 goals   (same)
  Q-table (RL) keeper   21 goals              33 goals   (+57 %)
  idle keeper           unchanged (the keeper does not move: no samples)

The prior equals the rule-based keeper's code, so there is little to
gain there. The RL keeper behaves differently (about 0.6-0.7 m/s, bang-bang),
and the learned model adapts to it. Details: results/aiming/README.md.
"""

from math import hypot
from typing import List, Optional, Tuple

from ssl_strategy_api.models import RobotState, TeamColor, TeamConfig, WorldState

SIM_DT_S = 0.025                 # rSoccer step length used by the runners
GOAL_POST_MARGIN_M = 0.08        # keep the aim this far inside the posts
KEEPER_SEARCH_RADIUS_M = 1.5     # an opponent this close to the goal is a keeper
SHOT_MIN_BALL_SPEED_MPS = 1.0    # slower balls are not treated as shots
MAX_SAMPLES = 2000

# Prior keeper model (a generic SSL keeper; refined online).
PRIOR_GAIN = 2.0
PRIOR_V_MAX_MPS = 1.8
PRIOR_Y_LIMIT_M = 0.4
PRIOR_BALL_SPEED_MPS = 3.5
PRIOR_WEIGHT = 30.0              # prior counts as this many samples
PRIOR_GAIN_SD = 1.0              # prior uncertainty of the gain
PRIOR_V_MAX_SD = 0.5             # prior uncertainty of v_max, m/s
FIT_NOISE_SD = 0.2               # measurement noise of keeper speed, m/s
FIT_GAINS = [0.5 + 0.25 * i for i in range(23)]    # 0.5 .. 6.0
FIT_SPEEDS = [0.3 + 0.1 * i for i in range(23)]    # 0.3 .. 2.5 m/s
REFIT_EVERY = 5                  # samples between refits (keeps it cheap)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _blend(prior: float, estimate: Optional[float], n: int) -> float:
    if estimate is None or n <= 0:
        return prior
    return (PRIOR_WEIGHT * prior + n * estimate) / (PRIOR_WEIGHT + n)


class KeeperModel:
    """Online-identified model of the opponent goalkeeper and our shots."""

    def __init__(self) -> None:
        self.gain = PRIOR_GAIN
        self.v_max_mps = PRIOR_V_MAX_MPS
        self.y_limit_m = PRIOR_Y_LIMIT_M
        self.ball_speed_mps = PRIOR_BALL_SPEED_MPS
        # (distance to target, speed toward target) samples during shots.
        self.samples: List[Tuple[float, float]] = []
        self.ball_speeds: List[float] = []
        self.max_abs_y_m = 0.0

    # ---------------------------------------------------------------- learning
    def add_sample(self, distance_m: float, speed_toward_mps: float) -> None:
        self.samples.append((distance_m, speed_toward_mps))
        if len(self.samples) > MAX_SAMPLES:
            self.samples.pop(0)

    def add_ball_speed(self, speed_mps: float) -> None:
        self.ball_speeds.append(speed_mps)
        if len(self.ball_speeds) > MAX_SAMPLES:
            self.ball_speeds.pop(0)

    def add_keeper_position(self, abs_y_m: float) -> None:
        self.max_abs_y_m = max(self.max_abs_y_m, abs_y_m)

    def refit(self, goal_half_width_m: float = 0.5) -> None:
        """Re-estimate the parameters from all samples seen so far (MAP fit)."""
        if self.samples:
            self.gain, self.v_max_mps = self._fit_controller()
            # Seeing the keeper at |y| proves it can reach at least that far.
            seen = min(goal_half_width_m, self.max_abs_y_m)
            self.y_limit_m = max(PRIOR_Y_LIMIT_M, seen)

        if self.ball_speeds:
            mean_speed = sum(self.ball_speeds) / len(self.ball_speeds)
            self.ball_speed_mps = _blend(PRIOR_BALL_SPEED_MPS, mean_speed, len(self.ball_speeds))

    def _fit_controller(self) -> Tuple[float, float]:
        """Fit speed = min(v_max, gain * distance) by grid search.

        Minimises  sum(residual^2) / NOISE^2  +  prior penalty, i.e. a
        maximum-a-posteriori estimate with a Gaussian prior. When the data
        cannot tell a parameter apart (the keeper never reached top speed)
        the prior keeps it at a sensible value instead of guessing.
        """
        best = None
        for gain in FIT_GAINS:
            for v_max in FIT_SPEEDS:
                cost = ((gain - PRIOR_GAIN) / PRIOR_GAIN_SD) ** 2
                cost += ((v_max - PRIOR_V_MAX_MPS) / PRIOR_V_MAX_SD) ** 2
                for d, v in self.samples:
                    r = v - min(v_max, gain * d)
                    cost += (r / FIT_NOISE_SD) ** 2
                if best is None or cost < best[0]:
                    best = (cost, gain, v_max)
        return best[1], best[2]

    # -------------------------------------------------------------- prediction
    def keeper_y_after(self, keeper_y: float, target_y: float, seconds: float) -> float:
        """Roll the keeper controller forward for ``seconds``."""
        target_y = _clamp(target_y, -self.y_limit_m, self.y_limit_m)
        y = keeper_y
        for _ in range(int(max(0.0, seconds) / SIM_DT_S)):
            err = target_y - y
            speed = min(self.v_max_mps, self.gain * abs(err))
            y += (speed if err > 0 else -speed) * SIM_DT_S
        return y

    def describe(self) -> str:
        return (
            "keeper model: gain={:.2f} v_max={:.2f} m/s y_limit={:.2f} m "
            "ball_speed={:.2f} m/s ({} keeper samples, {} ball samples)".format(
                self.gain, self.v_max_mps, self.y_limit_m, self.ball_speed_mps,
                len(self.samples), len(self.ball_speeds),
            )
        )


class LearnedAimer:
    """Chooses a target in the goal mouth using an online-learned keeper model."""

    def __init__(self, lanes: int = 5, learn: bool = True) -> None:
        if lanes < 1:
            raise ValueError("lanes must be at least 1")
        self.lanes = lanes
        self.learn = learn
        self.model = KeeperModel()
        self._prev_keeper: Optional[Tuple[int, float]] = None   # (frame, y)
        self._prev_frame: Optional[int] = None
        self._frame_counter = 0

    # ------------------------------------------------------------- public API
    def choose_target(self, state: WorldState, config: TeamConfig) -> Tuple[float, float]:
        """Return the aiming point (x, y) in field coordinates, metres."""
        self.observe(state, config)

        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        keeper = find_keeper(state, config)
        if state.ball is None or keeper is None:
            return goal_x, 0.0

        best = None
        for lane in self.lane_targets(state, config):
            gap = self.lane_gap(state.ball.x_m, state.ball.y_m, keeper, lane)
            # Tie-break toward the centre: a miss near the post is costly.
            key = (round(gap, 3), -abs(lane[1]))
            if best is None or key > best[0]:
                best = (key, lane)
        return best[1]

    def lane_targets(self, state: WorldState, config: TeamConfig) -> List[Tuple[float, float]]:
        goal_x = config.attack_direction_x * state.field.length_m / 2.0
        usable = max(0.0, state.field.goal_width_m / 2.0 - GOAL_POST_MARGIN_M)
        if self.lanes == 1:
            return [(goal_x, 0.0)]
        step = 2.0 * usable / (self.lanes - 1)
        return [(goal_x, -usable + i * step) for i in range(self.lanes)]

    def lane_gap(self, ball_x: float, ball_y: float, keeper: RobotState,
                 lane: Tuple[float, float]) -> float:
        """Predicted distance between the keeper and the ball when it passes him."""
        dx = lane[0] - ball_x
        plane_dx = keeper.x_m - ball_x
        if abs(dx) < 1e-9 or plane_dx / dx <= 0.0:
            return 0.0          # keeper is behind the ball: no useful prediction
        frac = plane_dx / dx
        y_cross = ball_y + frac * (lane[1] - ball_y)
        flight_s = hypot(plane_dx, y_cross - ball_y) / max(0.5, self.model.ball_speed_mps)
        keeper_y = self.model.keeper_y_after(keeper.y_m, y_cross, flight_s)
        return abs(y_cross - keeper_y)

    # ------------------------------------------------------------ observation
    def observe(self, state: WorldState, config: TeamConfig) -> None:
        """Collect one learning sample from this frame (if it is a shot frame)."""
        if not self.learn:
            return
        frame = state.frame_number
        if frame is None:
            self._frame_counter += 1
            frame = self._frame_counter

        keeper = find_keeper(state, config)
        ball = state.ball
        prev = self._prev_keeper
        self._prev_keeper = (frame, keeper.y_m) if keeper is not None else None
        if keeper is None or ball is None or prev is None:
            return

        steps = frame - prev[0]
        if steps != 1:
            return          # skipped frames: velocity would be unreliable
        keeper_vy = (keeper.y_m - prev[1]) / SIM_DT_S

        if ball.vx_mps is None or ball.vy_mps is None:
            return
        toward_goal = ball.vx_mps * config.attack_direction_x
        ball_speed = hypot(ball.vx_mps, ball.vy_mps)
        ahead = (keeper.x_m - ball.x_m) * config.attack_direction_x
        if toward_goal < SHOT_MIN_BALL_SPEED_MPS or ahead <= 0.1:
            return

        # Where will the ball cross the keeper's line? That is his target.
        y_cross = ball.y_m + ball.vy_mps * (keeper.x_m - ball.x_m) / ball.vx_mps
        target = _clamp(y_cross, -self.model.y_limit_m, self.model.y_limit_m)
        err = target - keeper.y_m
        distance = abs(err)
        if distance < 1e-3:
            return
        speed_toward = keeper_vy if err > 0 else -keeper_vy
        self.model.add_keeper_position(abs(keeper.y_m))
        self.model.add_sample(distance, speed_toward)
        self.model.add_ball_speed(ball_speed)
        if len(self.model.samples) % REFIT_EVERY == 0:
            self.model.refit(state.field.goal_width_m / 2.0)


def find_keeper(state: WorldState, config: TeamConfig) -> Optional[RobotState]:
    """The opponent closest to the goal we attack, if it guards the goal."""
    opponents = state.robots_yellow if config.team == TeamColor.BLUE else state.robots_blue
    goal_x = config.attack_direction_x * state.field.length_m / 2.0
    best = None
    for robot in opponents.values():
        distance = hypot(robot.x_m - goal_x, robot.y_m)
        if distance <= KEEPER_SEARCH_RADIUS_M and (best is None or distance < best[0]):
            best = (distance, robot)
    return best[1] if best else None


_DEFAULT_AIMER = LearnedAimer(learn=False)


def choose_target(state: WorldState, config: TeamConfig) -> Tuple[float, float]:
    """Stateless helper: aim with the prior keeper model (no learning)."""
    return _DEFAULT_AIMER.choose_target(state, config)
