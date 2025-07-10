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
