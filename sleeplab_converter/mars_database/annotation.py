### Importation des données d'annotation relatives aux signaux de PSG

import re
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd
from striprtf.striprtf import rtf_to_text

from sleeplab_converter import edf

# These functions are for reading the various annotation files of mars database
# and build for compatibility with the sleeplab format converter

# Here I have fixed many inconsistency in sleep staging, but the timestamps still correspond to real time and cannot be used to map annotations to discontinous signals

# The final annotation dataframe contains the following columns no matter the source file:
## Time_from_start - Time from the first annotation (analysis start) in seconds (HOX: for sleeplab format this is changed to time from recording start in the converter)
## Start_time - Datetime for annotation/event start moment
## Duration - Duration of the annotation/event in seconds
## Event_label - Name of the event or the annotation label

# extra columns if available:
## Scoring_channel (Sometimes in Remlogig exports)
## Type Subtype Validated Description (csv file annotations)

DATETIME_FORMAT: str = "%d/%m/%Y-%H:%M:%S"
DATETIME_FORMAT_RTF: str = "%d/%m/%Y-%Hh%Mm%Ss"


def start_time_to_start_datetime(
    txt_df: pd.DataFrame, start_date_str: str, start_dt: datetime
) -> pd.DataFrame:
    """
    Convert 'Start_time_real' strings to datetime objects using the given start date and format.
    Adds one day if the parsed datetime is earlier than the reference start datetime to handle overnight events.
    We expect the events are in order respect to time from first to last in .txt files and < 24h long.
    Returns the updated DataFrame.
    """

    for n in range(0, len(txt_df)):
        if (
            datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]['Start_time_real'].strip()}",
                DATETIME_FORMAT,
            )
            >= start_dt
        ):
            txt_df.loc[n, "Start_time_real"] = datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]['Start_time_real'].strip()}",
                DATETIME_FORMAT,
            )
        else:
            txt_df.loc[n, "Start_time_real"] = datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]['Start_time_real'].strip()}",
                DATETIME_FORMAT,
            ) + timedelta(days=1)

    return txt_df


def start_time_to_start_datetime2(
    rtf_df: pd.DataFrame, start_date_str: str, start_dt: datetime
) -> pd.DataFrame:
    """
    Convert 'Start_time_real' strings to datetime objects based on the given start date.
    If the parsed time is earlier than the reference start datetime, adds one day to handle overnight events.
    We expect the events are in order respect to time from first to last in .txt files and < 24h long.
    Returns the updated DataFrame.
    """
    for n in range(0, len(rtf_df)):
        if (
            datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                DATETIME_FORMAT_RTF,
            )
            >= start_dt
        ):
            rtf_df.loc[n, "Start_time_real"] = datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                DATETIME_FORMAT_RTF,
            )
        else:
            rtf_df.loc[n, "Start_time_real"] = datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                DATETIME_FORMAT_RTF,
            ) + timedelta(days=1)

    return rtf_df


def start_time_to_start_datetime_remlogic(
    txt_df: pd.DataFrame, start_date_str: str, start_dt: datetime
) -> pd.DataFrame:
    """
    Convert 'Start_time' strings to datetime objects using the given start date and format.
    If the parsed time is earlier than the reference start datetime, adds one day to account for events crossing midnight.
    We expect the events are in order respect to time from first to last in .txt files and < 24h long.
    Returns the updated DataFrame.
    """
    for n in range(0, len(txt_df)):
        if (
            datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]['Start_time'].strip()}",
                DATETIME_FORMAT,
            )
            >= start_dt
        ):
            txt_df.loc[n, "Start_time"] = datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]['Start_time'].strip()}",
                DATETIME_FORMAT,
            )
        else:
            txt_df.loc[n, "Start_time"] = datetime.strptime(
                f"{start_date_str}-{txt_df.iloc[n]["Start_time"].strip()}",
                DATETIME_FORMAT,
            ) + timedelta(days=1)

    return txt_df


def duration_to_second(rtf_df: pd.DataFrame):
    """
    Convert 'Duration' strings in "%H:%M:%S" format to total seconds as integers.
    Sets duration to 0 if format is not recognized.
    Returns the modified DataFrame.
    """

    for n in range(0, len(rtf_df)):
        if rtf_df.loc[n, "Duration"] is not None and (
            "00:" in rtf_df.loc[n, "Duration"]
        ):  ## assume if 00: exists this is duration in form "%H:%M:%S"
            time = datetime.strptime(str(rtf_df.loc[n, "Duration"]).strip(), "%H:%M:%S")
            rtf_df.loc[n, "Duration"] = (
                time.second + time.minute * 60 + time.hour * 3600
            )
        else:
            rtf_df.loc[n, "Duration"] = 0
    return rtf_df


def time_from_start_to_seconds(rtf_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert 'Time_from_start' strings in "%Hh%Mm%Ss" format to total seconds as integers.
    Returns the updated DataFrame.
    """
    for n in range(0, len(rtf_df)):
        time = datetime.strptime(rtf_df.loc[n, "Time_from_start"].strip(), "%Hh%Mm%Ss")
        rtf_df.loc[n, "Time_from_start"] = (
            time.second + time.minute * 60 + time.hour * 3600
        )
    return rtf_df


## Import DELTAMED annotations


def annotation_deltamed(path: Path, patient: str, edf_name: str):
    txt_path: Path = path / patient / f"{edf_name.strip()}.txt"
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
    rtf_path: Path = path / patient / f"{edf_name.strip()}.rtf"
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


## Import REMLOGIC annotations
def annotation_remlogic(txt_path: Path):
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

    # Colonnes selon le format détecté
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


def annotation_csv(path: Path, patient: str, edf_name: str):

    csv_path: Path = path / patient / f"{edf_name.strip()}.csv"
    data_csv: pd.DataFrame = pd.read_csv(csv_path, encoding="UTF-16", delimiter="\t")

    # Parse start date and time in to one column of datetime
    start_dt: List[datetime] = []
    for n in range(0, len(data_csv)):
        datetime_start = datetime.strptime(
            f"{data_csv.iloc[n]["Start Date/Time: Date"]}-{data_csv.iloc[n]["Start Date/Time: Time - HH:MM:SS"]}",
            DATETIME_FORMAT,
        )
        start_dt.append(datetime_start)

    data_csv.loc[:, "Start_time"] = start_dt

    from_start_dt: List[int] = []
    for n in range(0, len(data_csv)):
        dif = (
            data_csv.iloc[n]["Start_time"] - data_csv.iloc[0]["Start_time"]
        )  # change here the start time of the recording !!!
        from_start_dt.append(dif.seconds)

    data_csv.loc[:, "Time_from_start"] = from_start_dt

    # Parse duration to seconds
    duration_seconds: List[float] = []
    for n in range(0, len(data_csv)):
        if np.isnan(data_csv.iloc[n]["Duration (total µs)"]):
            duration_seconds.append(0.0)
        else:
            duration_seconds.append(data_csv.iloc[n]["Duration (total µs)"] / 10e5)

    data_csv.loc[:, "Duration"] = duration_seconds

    # Copy Subtype as annotation event name
    event_labels: List[str] = []
    for n in range(0, len(data_csv)):
        event_labels.append(data_csv.iloc[n]["Subtype"])

    data_csv.loc[:, "Event_label"] = event_labels

    # Parse sleep stages from edf+ header
    edf_path: Path = path / patient / f"{edf_name.strip()}.edf"
    try:
        header = edf.read_edf_export(edf_path, annotations=True)[-1]
        st_rec: datetime = header["startdate"]
        keys: List[str] = [
            "Validated",
            "Start_time",
            "Time_from_start",
            "Duration",
            "Event_label",
        ]
        ann2: List = []
        for ann in header["annotations"]:
            if ann[2][0:5] == "Sleep":
                if ann[1] > 30:
                    for x in range(int(ann[1] / 30)):
                        ann2.append([ann[0] + x * 30, 30.0, ann[2]])
                else:
                    ann2.append(ann)
        for ann in ann2:
            if ann[2][0:5] == "Sleep" or ann[2][0:4] == "Limb":
                d = {list(keys)[i]: None for i in range(len(keys))}
                d["Event_label"] = ann[2]
                d["Start_time"] = st_rec + timedelta(seconds=ann[0])
                d["Time_from_start"] = ann[0]
                d["Duration"] = ann[1]
                d["Validated"] = "Yes"
                data_csv.loc[len(data_csv)] = d

    except:
        print("Annotation reading from EDF header failed")

    data_csv.sort_values(by=["Time_from_start"])

    return data_csv


## DATA IMPORT

## Note: DELTAMED annotations are composed of a .TXT file and an .rtf_df file.
## Remlogic annotations are composed of a .txt file only.
## Some recordings only have .csv of the scoring


def load_annotation(path: Path, patient: str, edf_name: str):
    # Changed logic because we might have Remlogic and Deltamed export in same folder
    # - thus more safe to read only the annotations that correspond to .edf filename
    # edf filename vs. annotation filename have some extra space ' ' and erros every now and then --> try with various edf_name
    # if annotation filenames don't have correct info, can't read annotations (hard to identify the correct files if patient has multiple edfs and annotations)
    # todo: could try to identify the correct files based on annotation and recording datetimes

    # First check if .rtf file exists - this is the most common recording type and .rtf should always exist
    rtf_path: Path = path / patient / f"{edf_name.strip()}.rtf"
    if rtf_path.is_file():
        data = annotation_deltamed(path, patient, edf_name)
        recording_type: str = "Deltamed"
    else:
        txt_path: Path = path / patient / f"{edf_name.strip()}.txt"
        if txt_path.is_file():
            with txt_path.open("rb") as txt_file:
                sample_text = txt_file.read()
                txt_file.close()
            if "RemLogic" in str(sample_text):
                try:
                    data = annotation_remlogic(txt_path)
                except ValueError as e:
                    print(f"[ERREUR] Impossible de parser le fichier : {e}")
                    data = None
                recording_type = "RemLogic"
            else:
                recording_type = "Unknown"
                return None, recording_type
        else:  # if no .rtf file or .txt file with correct filename
            # Check for .csv annotations
            report_path: Path = path / patient / f"{edf_name.strip()}.csv"
            if report_path.is_file():
                data = annotation_csv(path, patient, edf_name)
                recording_type = "BrainRT"
            else:
                recording_type = "Unknown"
                # No .rtf, .txt, or .csv files found inside the folder
                return None, recording_type
    return data, recording_type
