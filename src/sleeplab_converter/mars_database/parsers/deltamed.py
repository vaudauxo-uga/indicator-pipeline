import re
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List

import pandas as pd
from striprtf.striprtf import rtf_to_text

from sleeplab_converter.mars_database.parsers.base import BaseAnnotationParser
from sleeplab_converter.mars_database.time_helpers import (
    start_time_to_start_datetime,
    duration_to_second,
    start_time_to_start_datetime2,
    time_from_start_to_seconds,
    DATETIME_FORMAT,
)


def annotation_deltamed(path: Path, patient: str, edf_name: str) -> pd.DataFrame:
    """
    Loads and parses Deltamed annotations from both .txt and .rtf files.
    Returns the combined annotations with unified time, duration, and label format.
    """
    txt_path: Path = path / patient / f"{edf_name}.txt"
    txt_events_df: pd.DataFrame = pd.read_table(
        txt_path,
        skiprows=5,
        sep="\t",
        encoding="latin1",
        index_col=False,
        names=["Start_time_real", "Event_label"],
    )

    # find start date of annotations
    with txt_path.open("r", encoding="latin1") as file:
        sample_text: List[str] = file.readlines()
        file.close()
    start_date_str: str = sample_text[2].strip()
    start_datetime_dt: datetime = datetime.strptime(
        f"{start_date_str}-{txt_events_df.iloc[0]['Start_time_real']}",
        DATETIME_FORMAT,
    )

    start_time_to_start_datetime(txt_events_df, start_date_str, start_datetime_dt)

    # Parse only sleep stages and end of block
    stages: List[str] = [
        "Veille",
        "Stade 1",
        "Stade 2",
        "Stade 3",
        "S. Paradoxal",
        "Indéterminé",
        "//",
    ]
    sleep_df: pd.DataFrame = txt_events_df.loc[
        txt_events_df["Event_label"].isin(stages)
    ].copy()

    # Sleep stage duration info
    diff_dt: List[int] = []
    for n in range(1, len(sleep_df)):
        dif: timedelta = (
            sleep_df.iloc[n]["Start_time_real"]
            - sleep_df.iloc[n - 1]["Start_time_real"]
        )
        diff_dt.append(dif.seconds)
    diff_dt.append(30)

    sleep_df.loc[:, "Duration_tmp"] = diff_dt

    sleep_df = sleep_df.loc[sleep_df["Event_label"] != "//"].copy()

    # Drop sleep stages that have duration zero
    sleep_df = sleep_df.loc[sleep_df["Duration_tmp"] != 0].copy()

    # Force rest of the sleep stages where duration>30 as 30 seconds (because they are always scored in 30 sec windows so this is the case of uncontinuity)
    dur_new: List[int] = []
    for ind, row in sleep_df.iterrows():
        if row["Duration_tmp"] > 30:
            dur_new.append(30)
        else:
            dur_new.append(row["Duration_tmp"])

    sleep_df.loc[:, "Duration"] = dur_new

    # Time from start info
    from_start_dt: List = []
    time_running: int = 0
    for n in range(0, len(sleep_df)):
        from_start_dt.append(time_running)
        time_running += sleep_df.iloc[n]["Duration"]

    sleep_df.loc[:, "Time_from_start"] = from_start_dt

    # TODOO: Update start times to correspond to uncontinous recording? --> just create fake times to match sleeplab format

    start_dt_fake: List[datetime] = []
    for n in range(0, len(sleep_df)):
        start_dt_fake.append(
            start_datetime_dt
            + timedelta(seconds=int(sleep_df.iloc[n]["Time_from_start"]))
        )

    sleep_df.loc[:, "Start_time"] = start_dt_fake

    ##############################
    # Read events from RTF
    rtf_path: Path = path / patient / f"{edf_name}.rtf"
    with rtf_path.open("r", encoding="latin1") as rtf_file:
        sample_text: str = rtf_file.read()
        text = rtf_to_text(sample_text, encoding="latin1")
        x: str = re.sub(
            r"{\*?\\.+(;})|\s?\\[A-Za-z0-9]+|\s?{\s?\\[A-Za-z0-9]+\s?|\s?}\s?",
            ";",
            text,
        )
        lines: List[List[str]] = [line.split("  ") for line in x.split("\n")[15:-3]]
        res: List[List[str]] = [[el for el in sub if el != ""] for sub in lines]
        for row in res:
            if (
                len(row) > 5
            ):  # If true we assume long string in the end with double spaces and Duree missing
                event_tmp = "-".join(res[50][3:])
                [row.pop() for i in range(3, len(row))]
                row.append(event_tmp)
            if len(row) == 4:  # if True we assume Duree is missing and place '' there
                row.insert(-1, "")

    rtf_events_df: pd.DataFrame = pd.DataFrame(
        res,
        columns=[
            "index",
            "Time_from_start",
            "Start_time_real",
            "Duration",
            "Event_label",
        ],
    )
    rtf_events_df.dropna(inplace=True, ignore_index=True)
    rtf_events_df.drop_duplicates(inplace=True, ignore_index=True)
    rtf_events_df = rtf_events_df.loc[
        rtf_events_df["Start_time_real"] != "Heure réelle"
    ].copy()  # in case of douple annotation inside rtf, drop the extra header rows
    rtf_events_df = rtf_events_df.drop(["index"], axis=1)
    rtf_events_df.reset_index(inplace=True)
    duration_to_second(rtf_events_df)
    start_time_to_start_datetime2(rtf_events_df, start_date_str, start_datetime_dt)
    time_from_start_to_seconds(rtf_events_df)

    # create faketime
    start_dt_fake: List[datetime] = []
    for n in range(0, len(rtf_events_df)):
        start_dt_fake.append(
            start_datetime_dt
            + timedelta(seconds=int(rtf_events_df.iloc[n]["Time_from_start"]))
        )

    rtf_events_df.loc[:, "Start_time"] = start_dt_fake

    # Combine sleep stage and event info
    events_df: pd.DataFrame = pd.concat([rtf_events_df, sleep_df], ignore_index=True)

    # UPDATE datetimes!!! # TODOO: Update times to correspond to uncontinous recording?

    # Make some sorting and clean duplicates
    events_df.sort_values("Time_from_start", inplace=True, ignore_index=True)
    events_df.drop_duplicates(inplace=True, ignore_index=True)

    return events_df


class DeltamedParser(BaseAnnotationParser):
    name = "Deltamed"

    def detect(self, folder: Path, edf_name: str) -> bool:
        return (folder / f"{edf_name}.rtf").is_file()

    def parse(self, path: Path, patient: str, edf_name: str):
        return annotation_deltamed(path, patient, edf_name)
