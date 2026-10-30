# RoboCup SSL - Exercise 1

Team project: build a striker that approaches the ball, aligns, and scores as many
goals as possible during a 90-second evaluation, first against an idle goalkeeper
and then against an active goalkeeper.

## Where to work

The strategy folder already exists at:

```text
ssl_strategy_api-exercise1/src/ssl_strategy_api/strategies/
    movement.py   # Member 1: move to a point and control heading
    striker.py    # Member 2: approach/contact/kick behavior
    aiming.py     # Member 3: choose a target inside the goal
```

Member 4 runs the existing evaluation runner, records results, and reports failures.
Keep the supplied models, adapters, and evaluation runner unchanged initially.

`striker.py` currently retains the supplied circular-motion placeholder.
`movement.py` defines the agreed interface but deliberately raises
`NotImplementedError` until Member 1 implements it. `aiming.py` supplies a working
center-of-goal baseline for Member 3 to improve. The placeholder striker does not
call these helpers yet, so the existing demo still runs.

Member 1 starts with [the movement handoff](docs/MOVEMENT_HANDOFF.md).

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

Select the `rsoccer` environment's Python interpreter in your editor. Changes to
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
3. Edit your assigned file, verify it, and commit with a short descriptive message.
4. Push the branch and open a pull request for one teammate to review.
5. Merge small working changes regularly; agree before changing helper signatures.

Movement controls travel and heading. Aiming chooses the shot target. The striker
decides when to use movement, dribble, and kick. Keep those responsibilities separate.

The PDFs and supplied framework are course materials; this repository does not
assign a new license to them.
