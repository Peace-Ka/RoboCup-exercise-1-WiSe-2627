# Aiming (MJ): online-learned goalkeeper model

Code: `ssl_strategy_api-exercise1/src/ssl_strategy_api/strategies/aiming.py`
Tests: `tests/test_aiming.py` (8 tests, no simulator needed)

## Method

1. Split the goal mouth into 5 aiming spots (8 cm inside the posts).
2. For each spot, predict where the keeper will be when the ball crosses
   its line: roll its controller `speed = min(v_max, gain * distance)` forward
   for the ball's flight time (`distance / ball_speed`).
3. Aim at the spot with the largest predicted keeper-to-ball gap.

The keeper parameters are **learned online** during the match. Each frame in which
the ball flies toward the goal gives one sample (distance from keeper to the ball
path, keeper speed toward it). `gain` and `v_max` are fitted together by a
maximum-a-posteriori grid search (least squares + Gaussian prior around a generic
keeper). `y_limit` and the average ball speed are learned from the same frames.
The model persists across ball respawns, so it improves during the 90 seconds.

## Results

`run_rsoccer_exercise1_eval`, 90 s, headless, same striker, only aiming differs.

| Goalkeeper   | Aiming          | Goals, seeds 1–6 | Total  |
|--------------|-----------------|------------------|--------|
| Rule-based   | fixed prior     | 11 7 8 8 7 4     | 45     |
| Rule-based   | learned         | 5 7 6 8 6 11     | 43     |
| Q-table (RL) | fixed prior     | 8 1 1 2 5 4      | 21     |
| Q-table (RL) | learned         | 5 7 4 6 4 7      | **33** |
| Idle         | either          | 15 (seed 1)      | —      |

Learned parameters at the end of each run:

| Goalkeeper   | gain        | v_max (m/s) | y_limit (m) | ball speed (m/s) | samples per run |
|--------------|-------------|-------------|-------------|------------------|-----------------|
| Rule-based   | 2.0–2.25    | 0.4–0.5     | 0.40–0.42   | 3.47–3.54        | 57–117          |
| Q-table (RL) | 2.25–5.5    | 0.6–0.7 (one run 1.8) | 0.40–0.50 | 3.44–3.51 | 57–132          |

## Interpretation

* The prior equals the rule-based keeper's code, so learning cannot gain much
  there: results are the same within seed noise (45 vs 43).
* The model recovers the rule keeper's gain (2.0) exactly. Its learned top speed
  (0.4–0.5 m/s) is far below the 1.8 m/s in its code: during our short, close
  shots (about 0.3 s) the keeper never accelerates to full speed.
* The RL keeper behaves differently: it moves at a near-constant 0.6–0.7 m/s.
  The learned model detects this (high gain, low v_max) and aims accordingly:
  **+57 % goals** (33 vs 21) against a keeper the hand-written model was not made for.
* Seed-to-seed variance is large (e.g. 1 to 8 goals), so six seeds per setting
  are a minimum. Seed 2 of the RL keeper is a short run with few samples; there
  the prior is kept (v_max 1.8).

## Earlier negative result

A Q-table that learned the aiming spot directly from 694 random shots scored
worse than the model-based aiming and was removed (see `striker.py` notes).
Learning the keeper's dynamics instead needs far fewer samples, because the
physics model provides the structure.
