# RoboCup exercise 1 WiSe 2627

Team project: build a striker that approaches the ball, aligns, and scores as many
goals as possible during a 90-second evaluation, first against an idle goalkeeper
and then against an active goalkeeper.

## Implemented contributions

The strategy folder already exists at:

```text
ssl_strategy_api-exercise1/src/ssl_strategy_api/strategies/
    movement.py   # Member 1 implemented position and heading control
    striker.py    # Member 2 implemented approach, contact, shooting, and recovery
    aiming.py     # Member 3 implemented online-learned goalkeeper-aware aiming
```

Member 4's assigned responsibility is evaluation and failure analysis. The final
review results are recorded in `docs/SUBMISSION_REVIEW.md`; those records document
what was tested, without assigning unverified individual authorship.
The supplied models, adapters, and evaluation runner were preserved.

The default `StrikerStrategy` is integrated: it uses `movement.py` for motion and
`LearnedAimer` from `aiming.py` to select shots against a goalkeeper. It approaches,
aligns, obtains contact, carries with the dribbler enabled when appropriate, shoots,
and recovers after ball respawns. The aimer fits goalkeeper motion parameters
online during a run; no pre-trained striker model or external service is required.
This is online model identification combined with a rule-based striker, not
reinforcement learning.

Member 1 documentation: [movement handoff](docs/MOVEMENT_HANDOFF.md) and
[presentation notes](docs/MOVEMENT_PRESENTATION.md).

Movement verification (with `rsoccer` activated):

```sh
python -m unittest discover -s tests -v
python -m ssl_strategy_api.run_demos.run_movement --no-render --scenario all
python -m ssl_strategy_api.run_demos.run_movement --scenario diagonal
```

The last command opens a before/after visual comparison with a marked target.
Measured results and charts are in `results/movement/`.

## Submission review

The [submission-readiness report](docs/SUBMISSION_REVIEW.md) records the exact
tested strategy revision, complete-match results, limitations, and improvement
priorities. Raw evaluation logs are in `results/submission_readiness/`.

## Build the ZIP for the grader

Run this from the repository root using Python 3.10 or newer:

```sh
python scripts/build_submission.py
```

This creates `submission/RoboCup-exercise-1-WiSe-2627.zip`. It includes the complete
API source, strategy modules, supplied goalkeeper model, dependency requirements,
and [grader instructions](packaging/README.md). Generated ZIPs are ignored by Git;
all four implementors can build the same submission from the shared source.

After extraction, the grader can activate an existing course rSoccer environment
and run `python run.py --duration-seconds 90 --seed 1`. This uses the ZIP's source
and does not require access to the team's GitHub account. A fresh environment
needs dependencies installed as described in the included README.

Rebuild and retest the ZIP whenever the source changes. It includes all Python
tests under `tests/` and the aiming results notes. Include future learned model
files under `src/ssl_strategy_api/` so the builder includes them automatically.
The goalkeeper Q-table is a supplied opponent asset, not a trained striker model.

After extraction, the grader can run `python -m pip install --no-deps -e .` and
`python -m unittest discover -s tests -v` to verify the included tests in the course
environment. `run.py` directly selects the extracted source without installation.

The team has four equal implementors. GitHub ownership under a personal account is
a hosting arrangement, not a statement of individual project authorship. The grader
can run the ZIP independently of repository permissions.

## Setup for a new teammate (Windows PowerShell)

Install Miniconda and Microsoft Visual Studio Build Tools with the **Desktop
development with C++** workload, following `rSoccer_install_windows.pdf`.
Open a terminal where Conda works, clone this team repository, and enter its root.
Then run:

```powershell
conda create -n rsoccer --override-channels -c conda-forge python=3.10 libode pip -y
conda activate rsoccer

git clone https://github.com/robocin/rSoccer.git
git -C rSoccer checkout 3adf7c3e89fe6d1b47431ee4099dc5ee89420415

$odePrefix = $env:CONDA_PREFIX -replace '\\','/'
$env:CMAKE_ARGS = "-DODE_INCLUDE_DIRS=$odePrefix/Library/include"
$env:CMAKE_ARGS += " -DODE_LIBRARY_RELEASE=$odePrefix/Library/lib/ode_double.lib"
$env:CMAKE_ARGS += " -DCMAKE_POLICY_VERSION_MINIMUM=3.5"

python -m pip install -e .\rSoccer
python -m pip install --no-deps -e .\ssl_strategy_api-exercise1
python -m pip check
python -c "import rsoccer_gym, robosim, ssl_strategy_api; print('Imports OK')"
```

Conda already isolates the environment; no second virtual environment is needed.
Each teammate installs dependencies locally. The downloaded `rSoccer/` directory
and installed environments are excluded from this repository.

The editor should use the `rsoccer` environment's Python interpreter. Changes to
the course package take effect on the next run because it is installed in editable mode.

## Run

With `rsoccer` activated:

```powershell
# Default idle goalkeeper.
python -m ssl_strategy_api.run_demos.run_rsoccer_exercise1_eval --duration-seconds 90 --seed 1

# Active rule-based goalkeeper.
python -m ssl_strategy_api.run_demos.run_rsoccer_exercise1_eval --duration-seconds 90 --seed 1 --yellow-strategy ssl_strategy_api.strategies.goalkeeper:GoalkeeperStrategy
```

Add `--no-render` for a run without a window. Headless mode still runs at real-time
speed. Compare Blue-team goals using the same seeds and opponents.

On the original Windows machine, `run-exercise.cmd` and `run-episode.cmd` select
the environment automatically. They expect Miniconda under `%USERPROFILE%\miniconda3`.
[START_HERE.md](START_HERE.md) records that machine's installation and verification.

## Simple team workflow

1. Pull the latest `main` before starting a task.
2. Create a branch, for example `git switch -c feature/movement`.
3. Each implementor edits their assigned file, verifies it, and commits with a short descriptive message.
4. Push the branch and open a pull request for one teammate to review.
5. Merge small working changes regularly; agree before changing helper signatures.

Movement controls travel and heading. Aiming chooses the shot target. The striker
decides when to use movement, dribble, and kick. Keep those responsibilities separate.

The PDFs and supplied framework are course materials; this repository does not
assign a new license to them.
