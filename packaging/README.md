# RoboCup exercise 1 WiSe 2627 - team submission

This archive contains the team's strategy source and the supplied course API,
evaluation runner, and goalkeeper assets. It does not require access to the team's
GitHub repository or any contributor's local directories.

## Run in an existing course environment

Extract the entire ZIP. Activate the Python environment with rSoccer and its
dependencies installed, enter the extracted folder, and run:

```sh
python run.py --duration-seconds 90 --seed 1
```

Against the supplied rule-based goalkeeper:

```sh
python run.py --duration-seconds 90 --seed 1 --yellow-strategy ssl_strategy_api.strategies.goalkeeper:GoalkeeperStrategy
```

For a short check without a window:

```sh
python run.py --duration-seconds 2 --seed 1 --no-render
```

The launcher explicitly selects this archive's `src/` directory, even if another
copy of the API was installed in editable mode. It accepts the course evaluation
runner's normal command-line arguments. Running does not download anything.

## Set up dependencies if needed

Python 3.10 is the tested version. With an appropriate isolated environment active:

```sh
python -m pip install -r requirements.txt
python -m pip check
```

Initial installation requires Git and internet access. Compiling the native
physics backend also requires ODE and a C++ compiler if a compatible wheel is
unavailable. This ZIP contains source code, not a bundled Python interpreter or
operating-system-specific simulator binaries.

For a fresh Windows installation, install Miniconda and Visual Studio Build Tools
with the **Desktop development with C++** workload first. Then use PowerShell:

```powershell
conda create -n robocup-ex1 --override-channels -c conda-forge python=3.10 libode pip -y
conda activate robocup-ex1
$odePrefix = $env:CONDA_PREFIX -replace '\\','/'
$env:CMAKE_ARGS = "-DODE_INCLUDE_DIRS=$odePrefix/Library/include"
$env:CMAKE_ARGS += " -DODE_LIBRARY_RELEASE=$odePrefix/Library/lib/ode_double.lib"
$env:CMAKE_ARGS += " -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
python -m pip install -r requirements.txt
python -m pip check
python run.py --duration-seconds 2 --seed 1 --no-render
```

For other operating systems, use the course's rSoccer installation instructions.
Runtime compatibility has so far been checked on Windows with the course environment.

## Strategy entry point and development status

Entry point: `ssl_strategy_api.strategies.striker:StrikerStrategy`.

The three team-owned strategy modules are:

- `src/ssl_strategy_api/strategies/movement.py`: motion helper.
- `src/ssl_strategy_api/strategies/striker.py`: approach, contact, and shooting.
- `src/ssl_strategy_api/strategies/aiming.py`: goal targeting.

The default striker integrates all three modules. It approaches and aligns with
the ball, establishes contact, carries with the dribbler enabled when appropriate,
requests a kick only after its contact check, and recovers after ball respawns.

Against a goalkeeper, `LearnedAimer` estimates goalkeeper motion parameters and ball
speed online, then chooses among five goal targets using predicted clearance. It
starts from priors and learns within each run. No pre-training, internet connection,
or saved striker weights are needed at runtime. This is online model identification
combined with a rule-based controller; it is not reinforcement learning.

The `goalkeeper_q_table.npy` file belongs to the supplied opponent. It is included
so the Q-table goalkeeper can run; it is not the team's learned striker.

The supplied runner is retained for comparison with course evaluation behavior.
Its summary counts goals for either team; use the Blue/Yellow score for striker
performance. Headless execution retains real-time pacing.

## Movement-only demonstration

```sh
python -m pip install --no-deps -e .
python -m ssl_strategy_api.run_demos.run_movement --scenario diagonal
```

The editable installation above selects this archive's source for module execution.
The demonstration compares the course starter with the completed movement helper.

## Other opponent and verification

```sh
python run.py --duration-seconds 90 --seed 1 --yellow-strategy ssl_strategy_api.strategies.goalkeeper_rl:QTableGoalkeeperStrategy
```

For the included tests, install this archive's API without downloading dependencies
(the existing course environment supplies the simulator):

```sh
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
```

All 34 movement, aiming, and striker tests passed in the tested Windows Python 3.10
environment. Member 3's earlier aiming experiment is in `results/aiming/README.md`.
Movement measurements are in `results/movement/`. These results should not be
interpreted as a guarantee for untested seeds or operating systems.

For the final assignment evaluation, use the supplied exercise runner or the
`StrikerStrategy` entry point in the course environment. `run.py` is a convenience
launcher for that same evaluation runner, whose code is unchanged.

The final integrated evaluation and limitations are in `docs/SUBMISSION_REVIEW.md`.
Raw match records are in `results/submission_readiness/`. The movement presentation
notes describe Member 1's component contribution; the review describes team performance.
