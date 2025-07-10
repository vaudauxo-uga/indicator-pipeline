from pathlib import Path
from typing import Optional

import re


def extract_subject_id_from_filename(edf_file: Path) -> Optional[str]:
    """Extracts a standardized subject ID from an EDF filename."""

    stem: str = edf_file.stem

    match = re.search(r"(PA\d+)(V\d+C\d+)?", stem)
    if not match:
        return None

    patient_id: str = match.group(1)
    visit_suffix: str = match.group(2)

    return f"{patient_id}_{visit_suffix}" if visit_suffix else patient_id

def get_repo_root() -> Path:
    """Get the root of the repository."""

    repo_root: Path = Path(__file__).resolve().parent
    while ".git" not in [p.name for p in repo_root.iterdir()]:
        repo_root = repo_root.parent
    return repo_root

def get_local_slf_output() -> Path:
    """Get the root of the local output directory."""

    repo_root: Path = get_repo_root()
    outside_repo_dir: Path = repo_root.parent
    local_slf_output: Path = outside_repo_dir / "slf-output"
    local_slf_output.mkdir(parents=True, exist_ok=True)
    return local_slf_output