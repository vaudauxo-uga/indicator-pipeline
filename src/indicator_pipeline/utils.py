import json
import os
import re
from pathlib import Path
from typing import Optional, Union, Set, Dict, List, Tuple


def parse_recording_number(filename: str) -> str:
    """Extracts recording number FExxxx from edf or slf filename."""

    match = re.search(r"FE(\d+)", filename)
    if match:
        return match.group(1)
    return ""


def parse_patient_visit_recording(filename: str) -> Tuple[str, str, str]:
    """
    Extracts patient id, visit number and recording number from filename.
    Returns these numbers as strings.
    """
    match = re.search(r"PA(\d+)(?:_?V(\d+))?", filename)
    recording_number = parse_recording_number(filename)

    if match:
        patient_id = match.group(1)
        visit_number = match.group(2) or ""
        return patient_id, visit_number, recording_number
    return "", "", ""


def extract_subject_id_from_filename(edf_file: Path) -> str:
    """
    Extracts a standardized subject ID from an EDF filename patient id, visit number and recording number.
    Returns the subject ID as string "PAxxx_Vx_FExxxx".
    """
    stem: str = edf_file.stem
    patient_id, visit_suffix, recording_number = parse_patient_visit_recording(stem)

    parts: List[str] = [f"PA{patient_id}"]
    if visit_suffix:
        parts.append(f"V{visit_suffix}")
    if recording_number:
        parts.append(f"FE{recording_number}")

    return "_".join(parts)


def extract_recording_values(file_list: List[str]) -> List[Tuple[str, str]]:
    """
    Extracts (visit, recording) tuples from EDF filenames.
    Returns: [('V1', 'FE0001'), ('V1', 'FE0002'), ('V2', 'FE0001')]
    """
    recordings: Set = set()
    pattern = re.compile(r"FE(\d+)T1-PA\w+V(\d+)C\d+")

    for filename in file_list:
        if not filename.lower().endswith(".edf"):
            continue
        match = pattern.search(filename)
        if match:
            visit = f"V{match.group(2)}"
            recording = f"FE{match.group(1)}"
            recordings.add((visit, recording))

    return sorted(recordings)


def try_parse_number(value, as_int: bool = False) -> Optional[Union[int, float]]:
    """
    Converts a string to an int or float. Replaces commas with periods to handle European decimal formats.
    Returns None if the conversion fails.
    """
    try:
        if isinstance(value, str):
            value = value.replace(",", ".")
        number = round(float(value), 2)
        return int(number) if as_int else number
    except (ValueError, TypeError):
        return None


def get_repo_root() -> Path:
    """
    Get the root of the repository. Returns the corresponding Path.
    """
    repo_root: Path = Path(__file__).resolve().parent
    max_levels = 10

    for _ in range(max_levels):
        if repo_root.name == "indicator-pipeline":
            return repo_root
        if repo_root.parent == repo_root:
            break
        repo_root = repo_root.parent

    return Path(__file__).resolve().parent


def get_local_slf_output() -> Path:
    """
    Get the root of the local slf output directory.
    Returns the corresponding Path.
    """
    custom_path = os.environ.get("SLF_OUTPUT_PATH")
    if custom_path:
        local_slf_output = Path(custom_path)
    else:
        repo_root: Path = get_repo_root()
        outside_repo_dir: Path = repo_root.parent
        local_slf_output = outside_repo_dir / "slf-output"

    local_slf_output.mkdir(parents=True, exist_ok=True)
    return local_slf_output


def lowercase_extensions(dir_path: Path):
    """
    Lower all file extensions in a given folder.
    """
    for file in dir_path.rglob("*"):
        if file.is_file():
            new_path = file.with_suffix(file.suffix.lower())
            if new_path != file:
                file.rename(new_path)


def get_log_dir() -> Path:
    """
    Returns the log directory, creating it if it doesn't exist.
    Uses LOG_OUTPUT_PATH environment variable if set, else defaults to 'logs'.
    """
    log_dir = Path(os.environ.get("LOG_OUTPUT_PATH", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def load_slf_usage() -> Dict[str, Dict[str, bool]]:
    """
    Load the tracking file (slf_usage.json) that records the processing status
    of SLF datasets.
    """
    log_dir: Path = get_log_dir()
    slf_usage_path = log_dir / "slf_usage.json"

    if slf_usage_path.exists():
        with slf_usage_path.open("r") as f:
            return json.load(f)
    return {}


def save_slf_usage(data: Dict[str, Dict[str, bool]]) -> None:
    """
    Saves the current state of slf_usage.json.
    """
    log_dir: Path = get_log_dir()
    slf_usage_path = log_dir / "slf_usage.json"
    slf_usage_path.parent.mkdir(parents=True, exist_ok=True)

    with slf_usage_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
