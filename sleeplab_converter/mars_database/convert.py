import argparse
import glob
import json
import logging
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sleeplab_converter import edf
from sleeplab_converter.mars_database import annotation
from sleeplab_format import writer, models

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

    if type(header["startdate"]) is dt:
        start_ts = header["startdate"]
    else:
        start_ts = dt.strptime(
            header["startdate"] + "-" + header["starttime"], "%d.%m.%y-%H.%M.%S"
        )

    sample_arrays = {}
    for s_load_func, s_header in zip(s_load_funcs, sig_headers):
        sample_array = _parse_samplearray(s_load_func, s_header)
        sample_arrays[sample_array.attributes.name] = sample_array

    return start_ts, sample_arrays


def parse_sleep_stage(row) -> models.Annotation[models.AASMSleepStage]:

    # ToDo: Check unique names from all data!! There can be errors

    stage_map = {
        # Deltamed
        "Veille": models.AASMSleepStage.W,
        "Stade 1": models.AASMSleepStage.N1,
        "Stade 2": models.AASMSleepStage.N2,
        "Stade 3": models.AASMSleepStage.N3,
        "Stade 4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
        "S. Paradoxal": models.AASMSleepStage.R,
        "Indéterminé": models.AASMSleepStage.UNSCORED,
        # Remlogic
        "SLEEP-S0": models.AASMSleepStage.W,
        "SLEEP-S1": models.AASMSleepStage.N1,
        "SLEEP-S2": models.AASMSleepStage.N2,
        "SLEEP-S3": models.AASMSleepStage.N3,
        "SLEEP-S4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
        "SLEEP-REM": models.AASMSleepStage.R,
        # BrainRT
        "Sleep stage W": models.AASMSleepStage.W,
        "Sleep stage N1": models.AASMSleepStage.N1,
        "Sleep stage N2": models.AASMSleepStage.N2,
        "Sleep stage N3": models.AASMSleepStage.N3,
        "Sleep stage N4": models.AASMSleepStage.N3,  # RK stage 4 combined to 3 in AASM rules
        "Sleep stage R": models.AASMSleepStage.R,
        "SLEEP-UNSCORED": models.AASMSleepStage.UNSCORED,
    }

    if row["Event_label"] in stage_map.keys():
        return models.Annotation[models.AASMSleepStage](
            name=stage_map[row["Event_label"]],
            start_ts=row["Start_time"],
            start_sec=row["Time_from_start"],
            duration=row["Duration"],
        )
    else:
        return None


def parse_for_aasm_annotation(row) -> models.Annotation[models.AASMEvent]:

    # ToDo: Check unique names from all data!! There can be events missing

    aasm_event_map = {
        #'': models.AASMEvent.UNSURE,
        # Score all artifacts as ARTIFACT
        # Deltamed exports channel-specific aftefacts like 'Artefact (PRES)', check 'original_annotations.a' -file for these
        "SIGNAL-ARTIFACT": models.AASMEvent.ARTIFACT,  # Remlogic
        "SIGNAL-QUALITY-LOW": models.AASMEvent.ARTIFACT,  # Remlogic
        "PLM droit": models.AASMEvent.PLM_RIGHT,  # Deltamed
        "PLM Gauce": models.AASMEvent.PLM_LEFT,  # Deltamed
        "PLM-LM": models.AASMEvent.PLM,  # Remlogic
        "PLM": models.AASMEvent.PLM,  # Remlogic
        "Limb movement : Mouvement de la jambe gauche": models.AASMEvent.PLM,  # csv
        "Arousal non spécifique": models.AASMEvent.AROUSAL,  # Deltamed
        "Arousal cortical": models.AASMEvent.AROUSAL,  # Deltamed
        "AROUSAL": models.AASMEvent.AROUSAL,  # Remlogic
        "Micro-éveil": models.AASMEvent.AROUSAL,  # csv #This is arousal also (manually scored)
        "Arousal d'origine respiratoire": models.AASMEvent.AROUSAL_RES,  # Deltamed
        "AROUSAL-RESP": models.AASMEvent.AROUSAL_RES,  # Remlogic
        "AROUSAL-SNORE": models.AASMEvent.AROUSAL_RES,  # Remlogic
        "AROUSAL-HYPOPNEA": models.AASMEvent.AROUSAL_RES,  # Remlogic
        "AROUSAL-APNEA": models.AASMEvent.AROUSAL_RES,  # Remlogic
        "AROUSAL-DESAT": models.AASMEvent.AROUSAL_RES,  # Remlogic
        "AROUSAL-SPONT": models.AASMEvent.AROUSAL_SPONT,  # Remlogic
        "Arousal autonome": models.AASMEvent.AROUSAL_SPONT,  # Remlogic
        "AROUSAL-PLM": models.AASMEvent.AROUSAL_PLM,  # Remlogic
        "Mouvement + arousal": models.AASMEvent.AROUSAL_LM,  # Deltamed
        "AROUSAL-LM": models.AASMEvent.AROUSAL_LM,  # Remlogic
        "AROUSAL-RERA": models.AASMEvent.RERA,
        "Apnée": models.AASMEvent.APNEA,  # Deltamed
        "APNEA": models.AASMEvent.APNEA,  # Remlogic
        "Apnée Centrale": models.AASMEvent.APNEA_CENTRAL,  # Deltamed
        "APNEA-CENTRAL": models.AASMEvent.APNEA_CENTRAL,  # Remlogic
        "Apnée centrale": models.AASMEvent.APNEA_CENTRAL,  # csv
        "Apnée Obstructive": models.AASMEvent.APNEA_OBSTRUCTIVE,  # Deltamed
        "APNEA-OBSTRUCTIVE": models.AASMEvent.APNEA_OBSTRUCTIVE,  # Remlogic
        "Apnée obstructive": models.AASMEvent.APNEA_OBSTRUCTIVE,  # csv
        "Apnée Mixte": models.AASMEvent.APNEA_MIXED,  # Deltamed
        "APNEA-MIXED": models.AASMEvent.APNEA_MIXED,  # Remlogic
        "Apnée mixte": models.AASMEvent.APNEA_MIXED,  # Remlogic
        #'Hypopnée': models.AASMEvent.HYPOPNEA, # Deltamed - This is obstructive by default (confirmed by Marion from sleep lab)
        "HYPOPNEA": models.AASMEvent.HYPOPNEA,  # Remlogic - These are unclassified hypopneas (confirmed by Marion from sleep lab)
        "hypopnée": models.AASMEvent.HYPOPNEA,  # csv
        "hypopnée Centrale": models.AASMEvent.HYPOPNEA_CENTRAL,  # Deltamed
        "HYPOPNEA-CENTRAL": models.AASMEvent.HYPOPNEA_CENTRAL,  # Remlogic
        "Hypopnée centrale": models.AASMEvent.HYPOPNEA_CENTRAL,  # csv
        "Hypopnée": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Deltamed - This is obstructive by default (confirmed by Marion from sleep lab)
        "HYPOPNEA-OBSTRUCTIVE": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Remlogic
        "hypopnée Obstructive": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # Deltamed
        "Hypopnée obstructive": models.AASMEvent.HYPOPNEA_OBSTRUCTIVE,  # csv
        # There are also mixed hypopneas scored in the data 'Hypopnée Mixte' check all annotation file for these
        # because sleeplab format does not support this as an AASMEvent currently
        # Should we group these into HYPOPNEA? Only around 20 found in the whole dataset
        #'Désaturation': models.AASMEvent.SPO2_DESAT, #Deltamed # UPDATE: this is automatic scoring
        #'DESAT': models.AASMEvent.SPO2_DESAT, #Remlogic # UPDATE: this is automatic scoring
        "Chute de la saturation": models.AASMEvent.SPO2_DESAT,  # csv
        #'Ronflements simples':models.AASMEvent.SNORE, #Deltamed UPDATE: this is automatic scoring
        #'SNORE-SINGLE':models.AASMEvent.SNORE, #Remlogic # UPDATE: this is automatic scoring
        "Périodes de ronflement": models.AASMEvent.SNORE,  # csv
    }

    if row["Event_label"] in aasm_event_map.keys():
        if "Validated" in row.keys():
            if row["Validated"] == "Yes":
                return models.Annotation[models.AASMEvent](
                    name=aasm_event_map[row["Event_label"]],
                    start_ts=row["Start_time"],
                    start_sec=row["Time_from_start"],
                    duration=row["Duration"],
                )
            else:
                return None
        else:
            return models.Annotation[models.AASMEvent](
                name=aasm_event_map[row["Event_label"]],
                start_ts=row["Start_time"],
                start_sec=row["Time_from_start"],
                duration=row["Duration"],
            )
    else:
        return None


def parse_annotations(header, edf_path, edf_name) -> tuple[
    list[models.Annotation[models.AASMEvent]],  # Events
    list[models.Annotation[models.AASMSleepStage]],  # Hypnogram
    list[models.Annotation[str]],  # Other annotations
    dt | None,  # Analysis start
    dt | None,  # Analysis end
    dt | None,  # Lights off
    dt | None,  # Lights on
    str | None,
]:  # recording type

    events = []
    AASMSleepStages = []
    AASMevents = []

    analysis_start = None
    analysis_end = None
    lights_on = None
    lights_off = None

    patient = edf_path.name + "/"
    path = str(edf_path.resolve()).strip(patient)

    annot_df, REC_TYPE = annotation.loadAnnotation(path, patient, edf_name)

    if type(header["startdate"]) is dt:
        st_rec = header["startdate"]
    else:
        st_rec = dt.strptime(
            header["startdate"] + "-" + header["starttime"], "%d.%m.%y-%H.%M.%S"
        )

    if annot_df is not None:
        if st_rec != annot_df.iloc[0]["Start_time"]:
            # print('Warning: annotations start different from recording start') # Don't really need to warn about this
            # logger.info(f'Updating event lag respect to recording start')
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
            AASMSleepStage = parse_sleep_stage(row)
            if AASMSleepStage is not None:
                AASMSleepStages.append(AASMSleepStage)

            # push only AASM standard events here
            AASMevent = parse_for_aasm_annotation(row)

            if AASMevent is not None:
                AASMevents.append(AASMevent)

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

        # if annotations for lights were not found.

        return (
            events,
            AASMSleepStages,
            AASMevents,
            analysis_start,
            analysis_end,
            lights_off,
            lights_on,
            REC_TYPE,
        )
    else:
        return (
            events,
            AASMSleepStages,
            AASMevents,
            analysis_start,
            analysis_end,
            lights_off,
            lights_on,
            REC_TYPE,
        )


def parse_edf(_edf_path: str) -> tuple[dt,]:

    try:
        sig_load_funcs, sig_headers, header = edf.read_edf_export(
            Path(_edf_path), annotations=False
        )
    except:
        sig_load_funcs, sig_headers, header = edf.read_edf_export_mne(
            _edf_path, annotations=False
        )

    start_ts, sample_arrays = parse_samplearrays(sig_load_funcs, sig_headers, header)

    return start_ts, sample_arrays, header


def read_series(src_dir_series: Path, series_name: str) -> models.Series:
    """Read data from `edf file` + `annotation file` and parse to sleeplab Series."""
    subjects = {}
    error_counts = {
        "EDF_does_not_exist": 0,
        "edf_reader_not_working": 0,
        "annot_parse_error": 0,
    }
    for edf_path in src_dir_series.iterdir():

        MULTI_EDF = False  # Flag for having multiple edf in the same file (patient has multiple visits)

        edf_list = glob.glob(str(edf_path.resolve()) + "/" + "*.edf")

        if len(edf_list) == 0:  # Check if no edf file exists in the the patient folder
            logger.info(f"Skipping subject with no .edf file: {edf_path.stem}")
            error_counts["EDF_does_not_exist"] += 1
            continue

        if (
            len(edf_list) > 1
        ):  # Check if there are more than one edf file (also then multiple annotation files are expected)
            logger.info(f"Multiple .edf files detected: {edf_path.stem}")
            MULTI_EDF = True

        logger.info(f"Start parsing subject {edf_path.name}")

        for edfs in edf_list:  # loop through the edf files

            if (
                edfs.split("-")[-2][-2:] != "T1"
            ):  # edf needs to be PSG recording (12 and 13 are MSLT and MWT recordings)
                continue

            try:  # Read signals from edf files
                start_ts, sample_arrays, header = parse_edf(edfs)
            except Exception as e:
                logger.warning(
                    f"Skipping subject {edf_path.stem} and file {edfs} due to error in EDF parsing:"
                )
                logger.warning(e)
                error_counts["edf_reader_not_working"] += 1
                continue
            try:  # Read annotations that correspond to edf filename (will fail if files are not correctly named or don't follow the normal structure)
                (
                    events,
                    AASMSleepStages,
                    AASMevents,
                    analysis_start,
                    analysis_end,
                    lights_off,
                    lights_on,
                    rec_type,
                ) = parse_annotations(
                    header, edf_path, edf_name=edfs.split("\\")[-1].split(".")[0]
                )
                if not events:
                    (
                        events,
                        AASMSleepStages,
                        AASMevents,
                        analysis_start,
                        analysis_end,
                        lights_off,
                        lights_on,
                        rec_type,
                    ) = parse_annotations(
                        header,
                        edf_path,
                        edf_name=edfs.split("\\")[-1].split(".")[0].split()[0],
                    )
                    if not events:
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
                        annotations=AASMSleepStages, scorer="manual"
                    ),
                    "manual_aasmevents": models.AASMEvents(
                        annotations=AASMevents, scorer="manual"
                    ),
                }

            if MULTI_EDF:
                metadata = models.SubjectMetadata(
                    subject_id=edf_path.stem
                    + "_V"
                    + edfs.split("\\")[-1].split(".")[0].split()[0].split("V")[-1],
                    recording_start_ts=start_ts,
                    analysis_start=analysis_start,
                    analysis_end=analysis_end,
                    lights_off=lights_off,
                    lights_on=lights_on,
                    additional_info={"recording_device": rec_type},
                )
            else:
                metadata = models.SubjectMetadata(
                    subject_id=edf_path.stem,
                    recording_start_ts=start_ts,
                    analysis_start=analysis_start,
                    analysis_end=analysis_end,
                    lights_off=lights_off,
                    lights_on=lights_on,
                    additional_info={"recording_device": rec_type},
                )

            subjects[metadata.subject_id] = models.Subject(
                metadata=metadata, sample_arrays=sample_arrays, annotations=annotations
            )

    series = models.Series(name=series_name, subjects=subjects)

    return series, error_counts


ALL_SERIES = [
    "2014",
    "2024",
    "2025",
]


def convert_dataset(
    src_dir: Path,
    dst_dir: Path,
    ds_name: str = "MARS",
    series: list[str] = ALL_SERIES,
    array_format: str = "zarr",
    clevel: int = 7,
    annotation_format: str = "json",
) -> None:

    series_dict = {}
    all_error_counts = {}

    logger.info(f"Converting the data from {src_dir} to {dst_dir}...")
    logger.info(f"Start reading the data from {src_dir}...")

    for series_name in series:
        logger.info(f"Converting series {series_name}...")
        src_dir_series = src_dir.joinpath(series_name)
        _series, _error_counts = read_series(src_dir_series, series_name)
        series_dict[series_name] = _series
        all_error_counts[series_name] = _error_counts

    error_count_path = dst_dir / "conversion_error_counts.json"
    logger.info(f"Writing error counts to {error_count_path}")
    with open(error_count_path, "a+") as f:
        json.dump(all_error_counts, f, indent=4)

    dataset = models.Dataset(name=ds_name, series=series_dict)
    logger.info(f"Start writing the data to {dst_dir}...")
    writer.write_dataset(
        dataset,
        basedir=dst_dir,
        annotation_format=annotation_format,
        array_format=array_format,
        compression_level=clevel,
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src_dir", type=Path, required=True)
    parser.add_argument("--dst_dir", type=Path, required=True)
    parser.add_argument("--ds_name", type=str, default="MARS")
    parser.add_argument("--series", nargs="*", default=ALL_SERIES)
    parser.add_argument("--array-format", default="zarr", help="The SLF array format.")
    parser.add_argument(
        "--clevel",
        type=int,
        default=7,
        help="Zstd compression level if array format is zarr.",
    )
    parser.add_argument(
        "--annotation-format", default="json", help="The SLF annotation format."
    )
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    assert set(args.series).issubset(
        set(ALL_SERIES)
    ), f"Series {set(args.series) - set(ALL_SERIES)} not in {ALL_SERIES}"
    logger.info(f"MARS conversion args: {vars(args)}")
    convert_dataset(**vars(args))
    logger.info(f"Conversion done.")
