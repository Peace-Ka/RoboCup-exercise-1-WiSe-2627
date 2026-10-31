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

This is currently a **development snapshot**, not the finished assignment solution.
The striker is still the provided circular-motion starter. The movement helper
is implemented and tested but has not yet been integrated into the striker.
Rebuild the ZIP after completing the strategy,
and update this status before the final submission.

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
