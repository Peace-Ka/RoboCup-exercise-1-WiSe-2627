"""Member 3's shot targeting: begin with the center of the opponent's goal."""

from typing import Tuple

from ssl_strategy_api.models import TeamConfig, WorldState


def choose_target(state: WorldState, config: TeamConfig) -> Tuple[float, float]:
    """Return a goal target in field coordinates, in meters.

    The striker selects when to call this function and how long to keep a target.
    Later, compare left/center/right targets against goalkeeper coverage here.
    """
    goal_x = config.attack_direction_x * state.field.length_m / 2.0
    return goal_x, 0.0
