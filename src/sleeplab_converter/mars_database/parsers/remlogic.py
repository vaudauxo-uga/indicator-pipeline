from datetime import datetime
from pathlib import Path
from typing import List, Dict

import pandas as pd

from sleeplab_converter.mars_database.parsers.base import BaseAnnotationParser
from sleeplab_converter.mars_database.time_helpers import (
    start_time_to_start_datetime_remlogic,
    DATETIME_FORMAT,
)


def annotation_remlogic(txt_path: Path) -> pd.DataFrame:
    """
    Parses a RemLogic .txt annotation file with variable header structures.
    Returns the cleaned annotations with standardized fields.
    """

    sleep_stages: List[str] = [
        "SLEEP-S0",
        "SLEEP-S1",
        "SLEEP-S2",
        "SLEEP-S3",
        "SLEEP-S4",
        "SLEEP-REM",
        "SLEEP-UNSCORED",
    ]

    with txt_path.open("r", encoding="latin1") as file:
        sample_text: List[str] = file.readlines()
        file.close()
    start_date_str: str = sample_text[3].split(":")[-1].split()[0]

    header_formats: Dict[str, str] = {
        "standard": "Stade de sommeil\tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\n",
        "extra_channel": "Stade de sommeil\tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\tEmplacement\n",
        "missing_position": "Stade de sommeil\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\tEmplacement\n",
        "missing_sleepstage": "Position\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\n",
        "weird_case": "tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]",
    }

    format_type = None
    for fmt, header in header_formats.items():
        try:
            rows_to_skip = sample_text.index(header)
            format_type = fmt
            break
        except ValueError:
            continue

    if format_type is None:
        raise ValueError("Aucun format d'en-tête reconnu dans le fichier texte.")

    columns_by_format: Dict[str, List[str]] = {
        "standard": ["SleepStage", "Position", "Start_time", "Event_label", "Duration"],
        "extra_channel": [
            "SleepStage",
            "Position",
            "Start_time",
            "Event_label",
            "Duration",
            "Scoring_channel",
        ],
        "missing_position": [
            "SleepStage",
            "Start_time",
            "Event_label",
            "Duration",
            "Scoring_channel",
        ],
        "missing_sleepstage": ["Position", "Start_time", "Event_label", "Duration"],
        "weird_case": ["Position", "Start_time", "Event_label", "Duration"],
    }

    txt_events_df = pd.read_table(
        txt_path,
        sep="\t",
        encoding="latin1",
        skiprows=rows_to_skip,
        on_bad_lines="warn",
        names=columns_by_format[format_type],
        header=0,
    )

    start_datetime_dt: datetime = datetime.strptime(
        start_date_str + "-" + txt_events_df.iloc[0]["Start_time"], DATETIME_FORMAT
    )
    start_time_to_start_datetime_remlogic(
        txt_events_df, start_date_str, start_datetime_dt
    )

    from_start_dt: List[int] = []
    for n in range(0, len(txt_events_df)):
        dif = txt_events_df.iloc[n]["Start_time"] - txt_events_df.iloc[0]["Start_time"]
        from_start_dt.append(dif.seconds)

    txt_events_df.loc[:, "Time_from_start"] = from_start_dt

    # Drop sleep stages that are not 30 seconds
    # (e.g. 2014:PA328 don't know where these come from but they seem artifacts because overlapping with standard sleep staging)
    txt_events_df2 = txt_events_df.drop(
        txt_events_df[
            (txt_events_df["Event_label"].isin(sleep_stages))
            & (txt_events_df["Duration"] != 30)
        ].index
    ).copy()

    txt_events_df2.sort_values("Time_from_start", inplace=True, ignore_index=True)
    txt_events_df2.drop_duplicates(inplace=True, ignore_index=True)

    return txt_events_df2


class RemLogicParser(BaseAnnotationParser):
    name = "RemLogic"

    def detect(self, folder: Path, edf_name: str) -> bool:
        txt_path = folder / f"{edf_name}.txt"

        if not txt_path.is_file():
            return False

        with txt_path.open("rb") as f:
            content = f.read()

        return b"RemLogic" in content

    def parse(self, path: Path, patient: str, edf_name: str):
        txt_path = path / patient / f"{edf_name}.txt"
        return annotation_remlogic(txt_path)
