import json
import logging
import os
import datetime
from pathlib import Path
from typing import List, Set, Dict, Any

import pandas as pd

from indicator_pipeline.excel_mapping import (
    DESATURATION_MAP,
    RECOVERY_MAP,
    RATIOS_MAP,
    SEVERITY_MAP,
    SPO2_MAP,
    TIME_BELOW_THRESHOLDS_MAP,
)
from indicator_pipeline.utils import (
    get_repo_root,
    parse_patient_visit_recording,
    try_parse_number,
    get_log_dir,
    load_slf_usage,
    save_slf_usage,
)

logger = logging.getLogger(__name__)
PROCESSED_PATH: Path = get_log_dir() / "processed.json"


def load_processed() -> Set[str]:
    """
    Loads json file with all ParameterValues files already processed.
    """
    if PROCESSED_PATH.exists():
        with open(PROCESSED_PATH, "r") as f:
            return set(json.load(f))
    return set()


def save_processed(processed_set) -> None:
    """
    Saves json file with all ParameterValues files already processed.
    """
    with open(PROCESSED_PATH, "w") as f:
        json.dump(sorted(processed_set), f, indent=2)


def find_parameter_folders(abosa_output_path: Path) -> List[Path]:
    """
    Based on the abosa output path, makes the list of all ParameterValues folders.
    """

    parameter_dirs: List[Path] = []

    for year_dir in abosa_output_path.iterdir():
        if year_dir.is_dir():
            for subdir in year_dir.iterdir():
                if subdir.is_dir() and subdir.name.startswith("ParameterValues_"):
                    parameter_dirs.append(subdir)

    return parameter_dirs


def get_excel_from_rel_path(folder_path: Path, rel_path: str) -> pd.DataFrame:
    """
    Loads the Excel file from folder path in a dataframe.
    """
    xlsx_files: List[Path] = list(folder_path.glob("*.xlsx"))

    if not xlsx_files:
        logger.error(f"⛔️ No .xlsx file found in folder: {rel_path}")
        raise FileNotFoundError(f"No .xlsx file found in {rel_path}")

    file: Path = xlsx_files[0]
    df: pd.DataFrame = pd.read_excel(file)
    return df


def df_to_json_payloads(df: pd.DataFrame, abosa_version: str) -> List[Dict[str, Any]]:
    """
    Convert each row of an Excel DataFrame into a compliant JSON payload.
    """

    def extract(patient_row, mapping: Dict[str, str]) -> Dict[str, Any]:
        return {
            new_key: try_parse_number(patient_row.get(old_key))
            for old_key, new_key in mapping.items()
        }

    payloads: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        filename = str(row.get("Filename", "")).strip()
        patient_id, visit_number, recording_number = parse_patient_visit_recording(
            filename
        )

        if not patient_id and not visit_number:
            logger.warning(f"⛔️ Skipped invalid filename: {filename}")
            continue

        payload: Dict[str, Any] = {
            "patient_id": try_parse_number(patient_id, as_int=True),
            "visit_number": try_parse_number(visit_number, as_int=True),
            "recording_type": None,
            "recording_date": None,
            "recording_number": try_parse_number(recording_number, as_int=True),
            "recording_equipment": None,
            "oximetry_records": {
                "computing_date_abosa": datetime.date.today().isoformat(),
                "abosa_version": abosa_version,
                "tst_abosa": try_parse_number(row.get("TST")),
                "n_desat_abosa": try_parse_number(row.get("n_desat"), as_int=True),
                "n_reco_abosa": try_parse_number(row.get("n_reco"), as_int=True),
                "odi_abosa": try_parse_number(row.get("ODI")),
                "desaturation_events": extract(row, DESATURATION_MAP),
                "recovery_events": extract(row, RECOVERY_MAP),
                "ratios": extract(row, RATIOS_MAP),
                "severity_indices": extract(row, SEVERITY_MAP),
                "spo2_stats": extract(row, SPO2_MAP),
                "time_below_thresholds": extract(row, TIME_BELOW_THRESHOLDS_MAP),
            },
        }
        payloads.append(payload)

    return payloads


def excel_to_json(abosa_version: str) -> None:
    """
    Processes abosa output Excel files and stores the data in JSON payloads.
    """

    slf_usage: Dict[str, Dict[str, bool]] = load_slf_usage()

    custom_path: str = os.environ.get("ABOSA_OUTPUT_PATH")
    if custom_path:
        abosa_output: Path = Path(custom_path)
    else:
        repo_root: Path = get_repo_root()
        outside_repo_dir: Path = repo_root.parent
        abosa_output: Path = outside_repo_dir / "abosa-output"

    if not abosa_output.exists():
        logger.error(f"The expected folder does not exist : {abosa_output}")
        raise FileNotFoundError(f"The abosa-output folder is missing : {abosa_output}")

    processed: Set[str] = load_processed()
    new_processed: Set[str] = set(processed)

    param_dirs: List[Path] = find_parameter_folders(abosa_output)

    if not param_dirs:
        logger.error("No folders to process in abosa-output")
        raise RuntimeError("No folders to process in abosa-output")

    for folder in param_dirs:
        rel_path: str = str(folder.relative_to(abosa_output))

        if rel_path in processed:
            logger.info(f"✅ Already processed : {rel_path}")
            continue

        logger.info(f"🚀 Processing : {rel_path}")
        indicator_df: pd.DataFrame = get_excel_from_rel_path(folder, rel_path)
        payloads: List[Dict[str, Any]] = df_to_json_payloads(
            indicator_df, abosa_version
        )

        for payload in payloads:
            slf_id = f"PA{payload['patient_id']}_V{payload['visit_number']}"
            print(f"slf_id: {slf_id}")
            if slf_id not in slf_usage:
                slf_usage[slf_id] = {}
            slf_usage[slf_id]["abosa"] = True

        output_dir: Path = get_log_dir() / "json_dumps"
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = rel_path.replace("/", "__").replace("\\", "__") + ".json"
        output_file = output_dir / safe_filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payloads, f, indent=2, ensure_ascii=False)

        new_processed.add(rel_path)

    save_processed(new_processed)
    save_slf_usage(slf_usage)
