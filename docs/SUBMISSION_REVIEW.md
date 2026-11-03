# Submission-readiness review - November 3, 2026

## Verdict

The integrated striker is runnable and ready to submit in the tested course
Windows/Python 3.10 environment. No strategy/runtime change was needed to pass
this review. Performance is variable and further optimization is possible.

I tested the team code at commit `5273557` (Member 2's updated striker plus Member 3's
finished aiming). I preserved an as-is ZIP locally before correcting packaging.
I left `movement.py`, `striker.py`, `aiming.py`, the API models/adapters, and the
course runners unchanged. My changes add verification, correct stale documentation,
and include the full tests/results in the submission ZIP.

## Assignment coverage

- The robot approaches the ball and aligns before shooting.
- The updated striker checks contact again before firing and enables the dribbler
  while carrying. The two earlier review findings are fixed in this revision.
- The strategy recovers after ball respawns and continues attempting shots.
- The exercise is tested for 90 seconds against idle and active goalkeepers.
- The learned aimer identifies an opponent motion model from observed shots and
  uses it to choose among five goal targets. This is online model identification
  with model-based shot selection, not reinforcement learning.
- No saved striker weights or account access are required. The included Q-table
  file is the supplied goalkeeper's asset.

## Continuous evaluation: unmodified official runner

I used `run_rsoccer_exercise1_eval.run_evaluation`, with no rendering, fresh striker
and goalkeeper instances for every trial, and seeds 1, 2, and 3. Each match lasted
90 seconds and completed all 3,600 steps. I parsed Blue/Yellow scores separately
because the runner's aggregate `goals` field counts goals for either side.

| Opponent | Aiming | Seed 1 | Seed 2 | Seed 3 | Total | Mean per 90 s |
|---|---|---:|---:|---:|---:|---:|
| Idle | Default | 15 | 7 | 15 | 37 | 12.33 |
| Rule-based | Learned | 5 | 7 | 6 | 18 | 6.00 |
| Q-table | Learned | 6 | 7 | 5 | 18 | 6.00 |
| Q-table | Fixed prior | 8 | 1 | 1 | 10 | 3.33 |

No Yellow-team goals occurred. These are the measurements from this review, not
promised scores for every future run. The Q-table comparisons use the same current
code and opponents; only `AIM_LEARNING` differs. Learning gave 18 vs 10 total goals
(an 80% increase in this three-seed sample), but lost on seed 1. Three seeds do not
establish statistical significance or a universal improvement. Member 3's earlier
six-seed experiment is separately retained in `results/aiming/README.md`.

Across all twelve full matches I observed:

- No crashes, non-finite command failures, or skipped simulation steps.
- No requested planar/angular motion exceeding the API limits.
- No kick requests outside the explicit firing range without infrared contact.
- No moving-carry commands with the dribbler disabled.
- The 95th-percentile strategy decision time stayed below 1 ms in each run.
  The longest individual decision was about 27.2 ms; the runner still completed
  3,600 steps in every match.

The range check is not a proof that every kick hits the ball: ball orientation,
physical contact, collisions, and blocking still matter.

## Single-episode checks

I also exercised the supplied `Exercise1Env` for seeds 1-10 against each opponent,
using its actual observations, commands, and terminal conditions. These checks
advance simulation directly without the demonstration runner's wall-clock sleeps;
they are episode outcome checks, not additional 90-second scoring measurements.

| Opponent | Goals | Other endings |
|---|---:|---|
| Idle | 10/10 | None |
| Rule-based | 9/10 | 1 out-of-bounds |
| Q-table | 7/10 | 1 out-of-bounds, 1 idle ball in goal area, 1 robot goal-area entry |

The continuous evaluation also recorded goal-area occupancy. Its
`blue_goal_area_entries` counter counts frames spent inside, not distinct entries.
This is why episode termination and continuous evaluation must be distinguished.

## Automated and packaging checks

- All 26 pre-existing movement/aiming tests passed.
- I added eight focused striker checks for contact, dribbler use, shot cooldown,
  respawn recovery, missing observations, and misalignment. All 34 tests passed.
- `pip check` found no broken dependencies in the `rsoccer` environment.
- I built a non-editable API wheel and installed it into an isolated temporary
  directory. It imports the integrated striker and loads the goalkeeper Q-table.
- I extracted the submission ZIP into a separate temporary directory. Its strategy
  files matched the checkout by SHA256, all 34 tests passed from extracted source,
  and `run.py` completed short smoke runs against all three opponents.
- The builder now includes all tests, aiming notes, this review, and the raw review
  results. It creates a SHA256 sidecar for the final ZIP.

A fresh simulator/dependency installation was not repeated during this review.
Tests reused the previously installed course environment. Linux/macOS and other
Python versions were not independently verified; the ZIP documents that limit.

## Improvements, in priority order

1. **Reduce alignment stalls.** In rule-based seed 1, the default striker spent
   1,492 frames (37.3 simulated seconds) in ALIGN. Keep a shot target stable during
   final approach/contact and add a timeout that restages the robot if alignment
   makes no progress. Continue observing the keeper while holding the target.
   These are candidate changes and need matched-seed testing before adoption.
2. **Improve recovery and boundary planning.** Q-table learned seed 3 produced five
   out-of-bounds restarts, and a single-episode test ended on robot goal-area entry.
   Plan robot waypoints around the area, rather than only checking the ball's
   position, and test rebounds near corners and posts.
3. **Validate ball position relative to the kicker.** The proximity fallback uses
   centre distance. A front-of-robot check would make the contact approximation
   more explicit when infrared is false. No out-of-range firing was observed in
   these matches, so this is a robustness improvement rather than a reproduced
   blocker for the tested integrated version.
4. **Expand the learning comparison.** Use more held-out seeds and report both
   improvements and losses. Treat fitted maximum speed as an effective short-shot
   response, not a proven physical maximum. The prior/model fit does not identify
   every parameter equally well from a small number of shots.
5. **Keep refitting inexpensive for longer matches.** The current grid search is
   adequate for the tested 90-second runs. At the 2,000-sample cap, `len(samples)`
   stays divisible by five and would trigger fitting every sample; use a separate
   total-sample counter if long-run training/evaluation is added.

I did not apply speculative strategy changes just before submission. The tested
team behavior is preserved, with its strengths and limitations documented.

## Reproduction and submission

With `rsoccer` activated, from the repository root:

```sh
python -m unittest discover -s tests -v
python scripts/evaluate_readiness.py 1
python scripts/evaluate_readiness.py 1 --fixed
```

Repeat the two evaluation commands for seeds 2 and 3 to reproduce the full-match
comparison. Each evaluation command writes JSON and an official-runner log under
`results/submission_readiness/`; use `--output-dir` to preserve the archived records.

```sh
python scripts/build_submission.py
```

Submit `submission/RoboCup-exercise-1-WiSe-2627.zip` through Ilias. The grader can
extract it, activate the existing course environment, and run:

```sh
python run.py --duration-seconds 90 --seed 1
```

The included README gives active-goalkeeper commands and optional dependency setup.
GitHub login and access to any contributor's computer are unnecessary.

## Strategy source fingerprints

These identify the exact strategy files tested from team commit `5273557`:

- `movement.py`: `51b1b60139b4a7d47d1ee5756669ed4ee54efb8bcc7f57ad105095bda30c763e`
- `striker.py`: `62b6a7fd0ce4f0c990e1da056342e22524b20494cff2f00f507e4c0943cfe7f1`
- `aiming.py`: `89d3abe2ded82f3c300c12fb55edfc97d5f3eec454c700ae9a42437a6a1c6be2`
