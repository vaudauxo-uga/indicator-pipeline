import re
from pathlib import Path
from typing import Optional


def parse_patient_and_visit(filename: str) -> tuple[str, str]:
    """Extracts patient id and visit number from filename"""

    match = re.match(r"PA(\d+)_V(\d+)", filename)
    if match:
        patient_id = match.group(1)
        numero_visite = match.group(2)
        return patient_id, numero_visite
    return "", ""


def extract_subject_id_from_filename(edf_file: Path) -> Optional[str]:
    """Extracts a standardized subject ID from an EDF filename."""

    stem: str = edf_file.stem
    patient_id, visit_suffix = parse_patient_and_visit(stem)

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
