"""Run the code beside this file, independently of any team member's checkout."""

from pathlib import Path
import sys


def main() -> int:
    # Prefer this ZIP's source over any editable API installed on the grader's PC.
    source = Path(__file__).resolve().parent / "src"
    if not source.is_dir():
        raise SystemExit("Missing src/ directory. Extract the entire submission ZIP first.")
    sys.path.insert(0, str(source))

    from ssl_strategy_api.run_demos.run_rsoccer_exercise1_eval import main as evaluate

    return evaluate()


if __name__ == "__main__":
    raise SystemExit(main())
