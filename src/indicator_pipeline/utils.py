import re
from pathlib import Path
from typing import Optional


def parse_patient_and_visit(filename: str) -> tuple[str, str]:
    """
    Extracts patient id and visit number from filename.
    Returns the patient id and the visit number as string.
    """
    match = re.search(r"PA(\d+)(?:_?V(\d+))?", filename)
    if match:
        patient_id = match.group(1)
        visit_number = match.group(2) or ""
        return patient_id, visit_number
    return "", ""


def extract_subject_id_from_filename(edf_file: Path) -> str:
    """
    Extracts a standardized subject ID from an EDF filename patient id and visit number).
    Returns the subject ID as string "PAxxx_Vx".
    """
    stem: str = edf_file.stem
    patient_id, visit_suffix = parse_patient_and_visit(stem)

    return f"PA{patient_id}_V{visit_suffix}" if visit_suffix else f"PA{patient_id}"


def get_repo_root() -> Path:
    """
    Get the root of the repository. Returns the corresponding Path.
    """
    repo_root: Path = Path(__file__).resolve().parent
    while ".git" not in [p.name for p in repo_root.iterdir()]:
        repo_root = repo_root.parent
    return repo_root


def get_local_slf_output() -> Path:
    """
    Get the root of the local slf output directory.
    Returns the corresponding Path.
    """
    repo_root: Path = get_repo_root()
    outside_repo_dir: Path = repo_root.parent
    local_slf_output: Path = outside_repo_dir / "slf-output"
    local_slf_output.mkdir(parents=True, exist_ok=True)
    return local_slf_output
