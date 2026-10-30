# Running Exercise 1 on this machine

The simulator source is in `rSoccer/`. The course framework and your strategy are in
`ssl_strategy_api-exercise1/`. Both packages use editable installations in the
Miniconda environment named `rsoccer` (Python 3.10).

## Verified installation

Setup completed on October 30, 2026:

- Miniconda and Microsoft Visual Studio Build Tools 2022 with the C++ workload installed.
- Python 3.10.22 and Conda ODE 0.16.6 in the `rsoccer` environment.
- rSoccer 1.0.0 from commit `3adf7c3e89fe6d1b47431ee4099dc5ee89420415`.
- The native `rc-robosim` 1.2 backend compiled successfully on Windows.
- Course API 0.1.0 installed in editable mode.
- `pip check` and imports of all six required modules passed.
- Headless evaluation completed 120 steps in 3 seconds.
- Evaluation with rendering enabled completed 400 steps in 10 seconds.
- Active rule-based goalkeeper evaluation completed 120 steps in 3 seconds.
- The single-episode launcher completed 80 steps in 2 seconds.

`installed-packages.txt` records the Python package inventory for diagnostics. It contains
machine-specific editable paths and Conda metadata; it is not a portable requirements file.

## Run from PowerShell

Open a terminal in this folder. These launchers select the environment for you:

```powershell
# Continuous evaluation with the default idle goalkeeper (window opens).
.\run-exercise.cmd --duration-seconds 90 --seed 1

# Active rule-based goalkeeper.
.\run-exercise.cmd --duration-seconds 90 --seed 1 --yellow-strategy ssl_strategy_api.strategies.goalkeeper:GoalkeeperStrategy

# Headless evaluation.
.\run-exercise.cmd --duration-seconds 90 --seed 1 --no-render

# One episode: stops at the first terminal event.
.\run-episode.cmd --duration-seconds 90 --seed 1
```

Headless mode still uses the runners' real-time pacing. It is not a fast training loop.
The current striker is the supplied placeholder; installing the simulator does not train it.

## Edit the strategy

Start with `ssl_strategy_api-exercise1/src/ssl_strategy_api/strategies/striker.py`.
The editable installation picks up changes on the next run.

Recommended sequence:

1. Move to a target and control heading.
2. Approach a point behind the ball along the shot line.
3. Align, approach slowly with the dribbler, and confirm infrared contact.
4. Kick toward a target inside the goal opening.
5. Recover when the ball respawns; evaluation does not reset the strategy each time.
6. Respect the opponent penalty-area boundary. The episode runner terminates on entry.
7. Compare several seeds against idle and rule-based goalkeepers before adding learning.

The RL goalkeeper supplied with the course only commands lateral movement; inspect its
position visually before using it as a benchmark. The evaluation summary counts goals
for either side, so check the Blue/Yellow score for striker performance.

## Editor interpreter and environment

Select this interpreter in your editor:

```text
C:\Users\peace\miniconda3\envs\rsoccer\python.exe
```

To activate the environment in the current PowerShell session without modifying your
PowerShell profile:

```powershell
(& "$env:USERPROFILE\miniconda3\Scripts\conda.exe" shell.powershell hook) | Out-String | Invoke-Expression
conda activate rsoccer
python -m pip check
python -c "import numpy, gymnasium, pygame, rsoccer_gym, robosim, ssl_strategy_api; print('All imports OK')"
```

## Reinstall the local packages if needed

With `rsoccer` activated, from this folder:

```powershell
$odePrefix = $env:CONDA_PREFIX -replace '\\','/'
$env:CMAKE_ARGS = "-DODE_INCLUDE_DIRS=$odePrefix/Library/include"
$env:CMAKE_ARGS += " -DODE_LIBRARY_RELEASE=$odePrefix/Library/lib/ode_double.lib"
$env:CMAKE_ARGS += " -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
python -m pip install -e .\rSoccer
python -m pip install --no-deps -e .\ssl_strategy_api-exercise1
```

Keep the Conda ODE package installed: the native simulator needs its DLLs at runtime.
