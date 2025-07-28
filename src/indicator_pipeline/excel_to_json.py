import json
from pathlib import Path
from typing import List, Set

import pandas as pd

from indicator_pipeline.utils import get_repo_root

PROCESSED_PATH: Path = get_repo_root() / "logs" / "processed.json"


def load_processed() -> Set[str]:
    """Loads json file with all ParameterValues files already processed."""
    if PROCESSED_PATH.exists():
        with open(PROCESSED_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_processed(processed_set):
    """Saves json file with all ParameterValues files already processed."""
    with open(PROCESSED_PATH, "w") as f:
        json.dump(sorted(processed_set), f, indent=2)


def find_parameter_folders(abosa_output_path: Path) -> List[Path]:
    """Based on the abosa output path, makes the list of all ParameterValues folders."""

    parameter_dirs: List[Path] = []

    for year_dir in abosa_output_path.iterdir():
        if year_dir.is_dir():
            for subdir in year_dir.iterdir():
                if subdir.is_dir() and subdir.name.startswith("ParameterValues_"):
                    parameter_dirs.append(subdir)

    return parameter_dirs


def excel_to_json():
    """Processes abosa output Excel files and stores the data in a JSON file."""

    repo_root: Path = get_repo_root()
    outside_repo_dir: Path = repo_root.parent
    abosa_output: Path = outside_repo_dir / "abosa-output"

    processed: Set[str] = load_processed()
    new_processed: Set[str] = set(processed)

    param_dirs = find_parameter_folders(abosa_output)

    for folder in param_dirs:
        rel_path: str = str(folder.relative_to(abosa_output))

        if rel_path in processed:
            print(f"✅ Already processed : {rel_path}")
            continue

        print(f"🚀 Processing : {rel_path}")
        new_processed.add(rel_path)

    save_processed(new_processed)


if __name__ == "__main__":
    excel_to_json()
