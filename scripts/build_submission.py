"""Build a portable source submission using only Python's standard library."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = Path("RoboCup-exercise-1-WiSe-2627")


def main() -> None:
    package = ROOT / "ssl_strategy_api-exercise1"
    files = {
        ROOT / "packaging/README.md": Path("README.md"),
        ROOT / "packaging/requirements.txt": Path("requirements.txt"),
        ROOT / "packaging/run.py": Path("run.py"),
        package / "pyproject.toml": Path("pyproject.toml"),
    }
    for source in sorted((package / "src").rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(package)
        if any(part in {"__pycache__", ".git", ".venv"} or part.endswith(".egg-info")
               for part in relative.parts):
            continue
        if source.suffix in {".pyc", ".pyo"}:
            continue
        files[source] = relative

    required = {
        Path("src/ssl_strategy_api/strategies/striker.py"),
        Path("src/ssl_strategy_api/strategies/movement.py"),
        Path("src/ssl_strategy_api/strategies/aiming.py"),
        Path("src/ssl_strategy_api/strategies/goalkeeper_q_table.npy"),
        Path("src/ssl_strategy_api/run_demos/run_rsoccer_exercise1_eval.py"),
    }
    missing = required - set(files.values())
    if missing:
        raise SystemExit("Missing required submission files: " + str(sorted(map(str, missing))))
    for source in files:
        if not source.is_file():
            raise SystemExit(f"Missing submission file: {source}")

    output = ROOT / "submission" / (ARCHIVE_ROOT.name + ".zip")
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for source, relative in files.items():
            archive.write(source, (ARCHIVE_ROOT / relative).as_posix())
    print(f"Created {output} ({len(files)} files)")
    print("Development snapshot: rebuild and test after each strategy change.")


if __name__ == "__main__":
    main()
