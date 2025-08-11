import json
import logging
import os
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Union

import pandas as pd

from indicator_pipeline.utils import get_repo_root, parse_patient_and_visit

logger = logging.getLogger(__name__)
DEFAULT_LOG_DIR = Path(os.environ.get("LOG_OUTPUT_PATH", "logs"))
DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_PATH: Path = DEFAULT_LOG_DIR / "processed.json"


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


def df_to_json_payloads(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert each row of an Excel DataFrame into a compliant JSON payload.
    """

    def extract(patient_row, keys: List[str]) -> Dict[str, Any]:
        return {key: try_parse_number(patient_row.get(key)) for key in keys}

    payloads: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        filename = str(row.get("Filename", "")).strip()
        patient_id, numero_visite = parse_patient_and_visit(filename)

        if not patient_id and not numero_visite:
            logger.warning(f"⛔️ Skipped invalid filename: {filename}")
            continue

        payload: Dict[str, Any] = {
            "patient_id": try_parse_number(patient_id, as_int=True),
            "numero_visite": try_parse_number(numero_visite, as_int=True),
            "TST": try_parse_number(row.get("TST")),
            "n_desat": try_parse_number(row.get("n_desat"), as_int=True),
            "n_reco": try_parse_number(row.get("n_reco"), as_int=True),
            "ODI": try_parse_number(row.get("ODI")),
            "desaturation": extract(
                row,
                [
                    "DesSev",
                    "DesSev100",
                    "DesDur",
                    "avg_des_dur",
                    "avg_des_area",
                    "avg_des_area100",
                    "avg_des_slope",
                    "avg_des_depth",
                    "avg_des_max",
                    "avg_des_nadir",
                    "med_des_dur",
                    "med_des_area",
                    "med_des_area100",
                    "med_des_slope",
                    "med_des_depth",
                    "med_des_max",
                    "med_des_nadir",
                ],
            ),
            "recovery": extract(
                row,
                [
                    "RecSev",
                    "RecSev100",
                    "RecDur",
                    "avg_reco_dur",
                    "avg_reco_area",
                    "avg_reco_area100",
                    "avg_reco_slope",
                    "avg_reco_depth",
                    "avg_reco_max",
                    "avg_reco_nadir",
                    "med_reco_dur",
                    "med_reco_area",
                    "med_reco_area100",
                    "med_reco_slope",
                    "med_reco_depth",
                    "med_reco_max",
                    "med_reco_nadir",
                ],
            ),
            "ratios": extract(
                row,
                [
                    "avg_duration_ratio",
                    "avg_depth_ratio",
                    "avg_area_ratio",
                    "avg_area100_ratio",
                    "avg_slope_ratio",
                    "med_duration_ratio",
                    "med_depth_ratio",
                    "med_area_ratio",
                    "med_area100_ratio",
                    "med_slope_ratio",
                ],
            ),
            "severity": extract(
                row,
                [
                    "TotalSev_integrated",
                    "TotalSev_block",
                    "TotalSev100",
                    "TotalDur",
                    "total_area_below100",
                ],
            ),
            "spo2": extract(
                row, ["avg_spO2", "med_spO2", "max_spO2", "nadir_spO2", "variance_spO2"]
            ),
            "time_below_thresholds": extract(
                row,
                [
                    "t100",
                    "t98",
                    "t95",
                    "t92",
                    "t90",
                    "t88",
                    "t85",
                    "t80",
                    "t75",
                    "t70",
                    "t65",
                    "t60",
                    "t55",
                    "t50",
                ],
            ),
        }
        payloads.append(payload)

    return payloads


def excel_to_json() -> None:
    """
    Processes abosa output Excel files and stores the data in JSON payloads.
    """

    custom_path: str = os.environ.get("ABOSA_OUTPUT_PATH")
    if custom_path:
        abosa_output: Path = Path(custom_path)
    else:
        repo_root: Path = get_repo_root()
        outside_repo_dir: Path = repo_root.parent
        abosa_output: Path = outside_repo_dir / "abosa-output"

    processed: Set[str] = load_processed()
    new_processed: Set[str] = set(processed)

    param_dirs: List[Path] = find_parameter_folders(abosa_output)

    for folder in param_dirs:
        rel_path: str = str(folder.relative_to(abosa_output))

        if rel_path in processed:
            logger.info(f"✅ Already processed : {rel_path}")
            continue

        logger.info(f"🚀 Processing : {rel_path}")
        indicator_df: pd.DataFrame = get_excel_from_rel_path(folder, rel_path)
        payloads: List[Dict[str, Any]] = df_to_json_payloads(indicator_df)

        output_dir: Path = DEFAULT_LOG_DIR / "json_dumps"
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = rel_path.replace("/", "__").replace("\\", "__") + ".json"
        output_file = output_dir / safe_filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payloads, f, indent=2, ensure_ascii=False)

        new_processed.add(rel_path)

    save_processed(new_processed)
