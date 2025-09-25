import json
import logging
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sleeplab_format import writer, models
from sleeplab_format.models import SampleArray

from indicator_pipeline.utils import extract_subject_id_from_filename
from sleeplab_converter.edf import read_edf_export, read_edf_export_mne
from sleeplab_converter.events_mapping import STAGE_MAPPING, AASM_EVENT_MAPPING
from sleeplab_converter.mars_database import annotation

logger = logging.getLogger(__name__)


def parse_sample_arrays(
    s_load_funcs: List[Callable[[], np.array]],
    sig_headers: List[Dict[str, Any]],
    header: Dict[str, Any],
) -> Tuple[datetime, Dict[str, SampleArray]]:
    """
    Parses signal data and metadata from EDF into sleeplab-format SampleArrays.
    Returns:
        - the recording start timestamp,
        - a dictionary of SampleArrays (one for each signal).
    """

    def _parse_sample_array(
        _load_func: Callable[[], np.array], _header: dict[str, Any]
    ) -> SampleArray:
        array_attributes = models.ArrayAttributes(
            # Replace '/' with '_' to avoid errors in filepaths
            name=_header["label"].replace("/", "_").replace("?", "").replace(".", ""),
            start_ts=start_ts,
            sampling_rate=_header["sample_frequency"],
            unit=_header["dimension"].strip(),
            sensor_info=_header["transducer"].strip(),
            amplifier_info=_header["prefilter"].strip(),
        )
        return models.SampleArray(attributes=array_attributes, values_func=_load_func)

    if type(header["startdate"]) is datetime:
        start_ts = header["startdate"]
    else:
        datetime_str: str = f"{header['startdate']}-{header['starttime']}"
        datetime_format: str = "%d.%m.%y-%H.%M.%S"
        start_ts = datetime.strptime(datetime_str, datetime_format)

    sample_arrays: Dict = {}
    for s_load_func, s_header in zip(s_load_funcs, sig_headers):
        sample_array = _parse_sample_array(s_load_func, s_header)
        sample_arrays[sample_array.attributes.name] = sample_array

    return start_ts, sample_arrays


def parse_sleep_stage(
    row: pd.Series,
) -> Optional[models.Annotation[models.AASMSleepStage]]:
    """
    Parse a DataFrame row to create an Annotation object for recognized sleep stages.
    Returns an Annotation if the 'Event_label' matches a known stage; otherwise, returns None.
    """
    # ToDo: Check unique names from all data!! There can be errors
    if row["Event_label"] in STAGE_MAPPING.keys():
        return models.Annotation[models.AASMSleepStage](
            name=STAGE_MAPPING[row["Event_label"]],
            start_ts=row["Start_time"],
            start_sec=row["Time_from_start"],
            duration=row["Duration"],
        )
    else:
        return None


def parse_for_aasm_annotation(
    row: pd.Series,
) -> Optional[models.Annotation[models.AASMEvent]]:
    """
    Parse a DataFrame row to create an Annotation for AASM events.
    Returns an Annotation if 'Event_label' matches and, if present, 'Validated' is 'Yes'.
    Otherwise, returns None.
    """
    # ToDo: Check unique names from all data!! There can be events missing
    if row["Event_label"] in AASM_EVENT_MAPPING.keys():
        if "Validated" in row.keys():
            if row["Validated"] == "Yes":
                return models.Annotation[models.AASMEvent](
                    name=AASM_EVENT_MAPPING[row["Event_label"]],
                    start_ts=row["Start_time"],
                    start_sec=row["Time_from_start"],
                    duration=row["Duration"],
                )
            else:
                return None
        else:
            return models.Annotation[models.AASMEvent](
                name=AASM_EVENT_MAPPING[row["Event_label"]],
                start_ts=row["Start_time"],
                start_sec=row["Time_from_start"],
                duration=row["Duration"],
            )
    else:
        return None


def parse_annotations(header: Dict[str, Any], edf_path: Path, edf_name: str) -> Tuple[
    List[models.Annotation[str]],
    List[models.Annotation[models.AASMSleepStage]],
    List[models.Annotation[models.AASMEvent]],
    Optional[datetime],
    Optional[datetime],
    Optional[datetime],
    Optional[datetime],
    Optional[str],
]:
    """
    Parses and categorizes annotations (sleep stages, AASM events, lights on/off, etc.)
    from corresponding annotation files for a given EDF recording.
    Returns:
        - list of all original events,
        - list of hypnogram stages,
        - list of valid AASM events,
        - analysis start timestamp,
        - analysis end timestamp,
        - lights off timestamp,
        - lights on timestamp,
        - recording device type.
    """

    events: List[models.Annotation[str]] = []
    aasm_sleep_stages: List[models.Annotation[models.AASMSleepStage]] = []
    aasm_events: List[models.Annotation[models.AASMEvent]] = []

    analysis_start = None
    analysis_end = None
    lights_on = None
    lights_off = None

    patient: str = edf_path.name
    path: Path = edf_path.parent.resolve()

    annot_df, recording_type = annotation.load_annotation(path, patient, edf_name)

    if type(header["startdate"]) is datetime:
        st_rec = header["startdate"]
    else:
        datetime_str: str = f"{header['startdate']}-{header['starttime']}"
        datetime_format: str = "%d.%m.%y-%H.%M.%S"
        st_rec = datetime.strptime(datetime_str, datetime_format)

    if annot_df is not None:
        if st_rec != annot_df.iloc[0]["Start_time"]:
            for n in range(
                0, len(annot_df)
            ):  # Update event lag from start of recording
                dif = (
                    annot_df.iloc[n]["Start_time"] - st_rec
                )  # compare here to the start time of the recording
                annot_df.loc[n, "Time_from_start"] = dif.seconds

        for index, row in annot_df.iterrows():
            # push all events with original labels into event list
            events.append(
                models.Annotation[str](
                    name=row["Event_label"],
                    start_ts=row["Start_time"],
                    start_sec=row["Time_from_start"],
                    duration=row["Duration"],
                )
            )

            # push only sleep stages into AASM sleep stage list
            aasm_sleep_stage = parse_sleep_stage(row)
            if aasm_sleep_stage is not None:
                aasm_sleep_stages.append(aasm_sleep_stage)

            # push only AASM standard events here
            aasm_event = parse_for_aasm_annotation(row)

            if aasm_event is not None:
                aasm_events.append(aasm_event)

            # Find analysis start and end times
            if row["Event_label"] == "ANALYSIS-START":
                analysis_start = row["Start_time"]

            if row["Event_label"] == "ANALYSIS-STOP":
                analysis_end = row["Start_time"]

            # Find lights off
            if row["Event_label"] == "Lumières éteintes":
                lights_off = row["Start_time"]
            elif row["Event_label"] == " LUMIERE ETEINTE":
                lights_off = row["Start_time"]
            elif row["Event_label"] == " ETEINT LA LUMIERE":
                lights_off = row["Start_time"]

            # Find lights on
            if row["Event_label"] == "Lumières éteintes":
                lights_on = row["Start_time"]
            elif row["Event_label"] == " LUMIERE ALLUMEE":
                lights_on = row["Start_time"]
            elif row["Event_label"] == " ALLUME LA LUMIERE":
                lights_on = row["Start_time"]
            elif row["Event_label"] == " LUMIERE ALLUMEE 6H01":
                lights_on = row["Start_time"]

        # if annotations for analysis start and end were not found.
        if analysis_start is None:
            analysis_start = events[0].start_ts
        if analysis_end is None:
            analysis_end = events[-1].start_ts + timedelta(seconds=events[-1].duration)

    return (
        events,
        aasm_sleep_stages,
        aasm_events,
        analysis_start,
        analysis_end,
        lights_off,
        lights_on,
        recording_type,
    )


def convert_dataset(
    input_dir: Path,
    output_dir: Path,
    series: str,
    ds_name: str = "MARS",
    array_format: str = "numpy",
    clevel: int = 7,
    annotation_format: str = "json",
) -> None:
    """
    Converts a dataset from a source directory to sleeplab format and structure in a destination directory.
    It processes multiple data series (years), logs any conversion errors.
    Saves slf files in the output directory.
    """

    series_dict: Dict = {}
    all_error_counts: Dict = {}

    logger.info(f"Converting the data from {input_dir} to {output_dir}...")
    logger.info(f"Start reading the data from {input_dir}...")

    logger.info(f"Converting series {series}...")
    input_dir_series = input_dir.joinpath(series)
    _series, _error_counts = read_series(input_dir_series, series)
    series_dict[series] = _series
    all_error_counts[series] = _error_counts

    error_count_path: Path = output_dir / "conversion_error_counts.json"
    logger.info(f"Writing error counts to {error_count_path}")
    with open(error_count_path, "a+") as f:
        json.dump(all_error_counts, f, indent=4)

    dataset = models.Dataset(name=ds_name, series=series_dict)
    logger.info(f"Start writing the data to {output_dir}...")
    writer.write_dataset(
        dataset,
        basedir=str(output_dir),
        annotation_format=annotation_format,
        array_format=array_format,
        compression_level=clevel,
    )


def parse_edf(_edf_path: Path) -> Tuple[datetime, Dict, Dict[str, Any]]:
    """
    Parses EDF signals using pyEDFlib or MNE depending on compatibility.
    Returns the start time, signal data, and header.
    """
    try:
        sig_load_funcs, sig_headers, header = read_edf_export(
            _edf_path, annotations=False
        )
    except:
        sig_load_funcs, sig_headers, header = read_edf_export_mne(
            str(_edf_path), annotations=False
        )
    start_ts, sample_arrays = parse_sample_arrays(sig_load_funcs, sig_headers, header)

    return start_ts, sample_arrays, header


def read_series(
    input_dir_series: Path, series_name: str
) -> Tuple[models.Series, Dict[str, int]]:
    """
    Reads and parses all subjects from a given series folder containing EDF and annotation files.
    For each subject, loads EDF signals, parses annotations, and builds Subject objects
    compatible with sleeplab format.
    Returns the parsed sleeplab Series object and counts of errors encountered during parsing.
    """
    subjects: Dict = {}
    error_counts: Dict[str, int] = {
        "EDF_does_not_exist": 0,
        "edf_reader_not_working": 0,
        "annot_parse_error": 0,
    }

    for edf_path in input_dir_series.iterdir():
        edf_list: List[Path] = list(edf_path.glob("*.edf"))

        if not edf_list:
            logger.warning(f"Skipping subject with no .edf file: {edf_path.stem}")
            error_counts["EDF_does_not_exist"] += 1
            continue

        logger.info(f"Start parsing subject {edf_path.name}")

        for edf_file in edf_list:
            if (
                "T1-" not in edf_file.name
            ):  # edf needs to be PSG recording (12 and 13 are MSLT and MWT recordings)
                continue

            try:  # Read signals from edf files
                start_ts, sample_arrays, header = parse_edf(edf_file)
            except Exception as e:
                logger.warning(
                    f"[SKIP] Skipping subject {edf_path.stem} and file {edf_file} due to error in EDF parsing:"
                )
                logger.warning(e)
                error_counts["edf_reader_not_working"] += 1
                continue
            try:  # Read annotations that correspond to edf filename (will fail if files are not correctly named or don't follow the normal structure)
                (
                    events,
                    aasm_sleep_stages,
                    aasm_events,
                    analysis_start,
                    analysis_end,
                    lights_off,
                    lights_on,
                    recording_type,
                ) = parse_annotations(header, edf_path, edf_name=edf_file.stem)
                if not events:
                    (
                        events,
                        aasm_sleep_stages,
                        aasm_events,
                        analysis_start,
                        analysis_end,
                        lights_off,
                        lights_on,
                        recording_type,
                    ) = parse_annotations(
                        header,
                        edf_path,
                        edf_name=edf_file.stem,
                    )
                    logger.warning(
                        f"Cannot find annotations for subject {edf_path.stem}"
                    )
            except Exception as e:
                logger.warning(
                    f"[SKIP] Skipping subject {edf_path.stem} due to error in annotation parsing:"
                )
                logger.warning(e)
                error_counts["annot_parse_error"] += 1
                continue

            if not events:
                annotations = {}
            else:
                annotations = {
                    "original_annotations": models.Annotations(
                        annotations=events, scorer="original"
                    ),
                    "manual_hypnogram": models.Hypnogram(
                        annotations=aasm_sleep_stages, scorer="manual"
                    ),
                    "manual_aasmevents": models.AASMEvents(
                        annotations=aasm_events, scorer="manual"
                    ),
                }

            subject_id: str = extract_subject_id_from_filename(edf_file)

            metadata = models.SubjectMetadata(
                subject_id=subject_id,
                recording_start_ts=start_ts,
                analysis_start=analysis_start,
                analysis_end=analysis_end,
                lights_off=lights_off,
                lights_on=lights_on,
                additional_info={"recording_device": recording_type},
            )

            subjects[metadata.subject_id] = models.Subject(
                metadata=metadata, sample_arrays=sample_arrays, annotations=annotations
            )

    series = models.Series(name=series_name, subjects=subjects)

    return series, error_counts
