import json
import logging
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from sleeplab_format import writer, models

from sleeplab_converter import edf
from sleeplab_converter.events_mapping import STAGE_MAPPING, AASM_EVENT_MAPPING
from sleeplab_converter.mars_database import annotation

logger = logging.getLogger(__name__)


def parse_samplearrays(s_load_funcs, sig_headers, header):
    """Read the start_ts and SampleArrays from the EDF."""

    def _parse_samplearray(
        _load_func: Callable[[], np.array], _header: dict[str, Any]
    ) -> models.SampleArray:
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
        datetime_str: str = f"{header["startdate"]}-{header["starttime"]}"
        datetime_format: str = "%d.%m.%y-%H.%M.%S"
        start_ts = datetime.strptime(datetime_str, datetime_format)

    sample_arrays: Dict = {}
    for s_load_func, s_header in zip(s_load_funcs, sig_headers):
        sample_array = _parse_samplearray(s_load_func, s_header)
        sample_arrays[sample_array.attributes.name] = sample_array

    return start_ts, sample_arrays


def parse_sleep_stage(row) -> models.Annotation[models.AASMSleepStage]:
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


def parse_for_aasm_annotation(row) -> models.Annotation[models.AASMEvent]:
    """
    Parse a DataFrame row to create an Annotation for AASM events.
    Returns an Annotation if 'Event_label' matches and, if present, 'Validated' is "Yes".
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


def parse_annotations(header: Dict[str, Any], edf_path: Path, edf_name: str) -> tuple[
    List[models.Annotation[str]],  # Events
    List[models.Annotation[models.AASMSleepStage]],  # Hypnogram
    List[models.Annotation[models.AASMEvent]],  # Other annotations
    datetime | None,  # Analysis start
    datetime | None,  # Analysis end
    datetime | None,  # Lights off
    datetime | None,  # Lights on
    str | None,
]:

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
        datetime_str: str = f"{header["startdate"]}-{header["starttime"]}"
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


def parse_edf(_edf_path: Path) -> tuple[datetime, Dict, Dict[str, Any]]:
    """Loads an EDF file and returns the start time, signal data, and header."""

    try:
        sig_load_funcs, sig_headers, header = edf.read_edf_export(
            _edf_path, annotations=False
        )
    except:
        sig_load_funcs, sig_headers, header = edf.read_edf_export_mne(
            str(_edf_path), annotations=False
        )

    start_ts, sample_arrays = parse_samplearrays(sig_load_funcs, sig_headers, header)

    return start_ts, sample_arrays, header


def read_series(input_dir_series: Path, series_name: str) -> Tuple[models.Series, Dict]:
    """Read data from `edf file` + `annotation file` and parse to sleeplab Series."""

    subjects: Dict = {}
    error_counts: Dict[str, int] = {
        "EDF_does_not_exist": 0,
        "edf_reader_not_working": 0,
        "annot_parse_error": 0,
    }
    for edf_path in input_dir_series.iterdir():
        is_multi_edf: bool = False

        edf_list: List[Path] = list(edf_path.glob("*.edf"))

        if not edf_list:
            logger.info(f"Skipping subject with no .edf file: {edf_path.stem}")
            error_counts["EDF_does_not_exist"] += 1
            continue

        if len(edf_list) > 1:
            logger.info(f"Multiple .edf files detected: {edf_path.stem}")
            is_multi_edf = True

        logger.info(f"Start parsing subject {edf_path.name}")

        for edf_file in edf_list:  # loop through the edf files
            if (
                "T1-" not in edf_file.name
            ):  # edf needs to be PSG recording (12 and 13 are MSLT and MWT recordings)
                continue

            try:  # Read signals from edf files
                start_ts, sample_arrays, header = parse_edf(edf_file)
            except Exception as e:
                logger.warning(
                    f"Skipping subject {edf_path.stem} and file {edf_file} due to error in EDF parsing:"
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
                    f"Skipping subject {edf_path.stem} due to error in annotation parsing:"
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

            if is_multi_edf:
                subject_id: str = (
                    f"{edf_path.stem}_V{edf_file.stem.split()[0].split("V")[-1]}"
                )
                metadata = models.SubjectMetadata(
                    subject_id=subject_id,
                    recording_start_ts=start_ts,
                    analysis_start=analysis_start,
                    analysis_end=analysis_end,
                    lights_off=lights_off,
                    lights_on=lights_on,
                    additional_info={"recording_device": recording_type},
                )
            else:
                metadata = models.SubjectMetadata(
                    subject_id=edf_path.stem,
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


if __name__ == "__main__":
    input_dir = Path(__file__).resolve().parent.parent / "input"
    output_dir = Path(__file__).resolve().parent.parent / "output"
    convert_dataset(
        input_dir=input_dir,
        output_dir=output_dir,
        series="2021",
        ds_name="MARS",
    )
