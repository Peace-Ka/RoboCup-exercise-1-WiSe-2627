@echo off
setlocal
set "ROBOCUP_CONDA=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not exist "%ROBOCUP_CONDA%" (
    echo Miniconda was not found at "%ROBOCUP_CONDA%".
    exit /b 1
)
call "%ROBOCUP_CONDA%" run --no-capture-output -n rsoccer python -m ssl_strategy_api.run_demos.run_rsoccer_exercise1 %*
exit /b %errorlevel%
