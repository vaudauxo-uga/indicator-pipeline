### Importation des données d'annotation relatives aux signaux de PSG

import datetime as dt
import re
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import striprtf
from sleeplab_converters import edf
from striprtf.striprtf import rtf_to_text


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


def Start_timeToStart_datetime(
    txt_df, start_date_str, start_dt
):  ## We expect the events are in order respect to time from first to last in .txt files and < 24h long
    for n in range(0, len(txt_df)):
        if (
            dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            )
            >= start_dt
        ):
            txt_df.loc[n, "Start_time_real"] = dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            )
        else:
            txt_df.loc[n, "Start_time_real"] = dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            ) + timedelta(days=1)

    return txt_df


def Start_timeToStart_datetime2(
    rtf_df, start_date_str, start_dt
):  ## We expect the events are in order respect to time from first to last in .txt files and < 24h long
    for n in range(0, len(rtf_df)):
        if (
            dt.datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%Hh%Mm%Ss",
            )
            >= start_dt
        ):
            rtf_df.loc[n, "Start_time_real"] = dt.datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%Hh%Mm%Ss",
            )
        else:
            rtf_df.loc[n, "Start_time_real"] = dt.datetime.strptime(
                start_date_str + "-" + rtf_df.iloc[n]["Start_time_real"].strip(),
                "%d/%m/%Y-%Hh%Mm%Ss",
            ) + timedelta(days=1)

    return rtf_df


def Start_timeToStart_datetime_remlogic(
    txt_df, start_date_str, start_dt
):  ## We expect the events are in order respect to time from first to last in .txt files and < 24h long
    for n in range(0, len(txt_df)):
        if (
            dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            )
            >= start_dt
        ):
            txt_df.loc[n, "Start_time"] = dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            )
        else:
            txt_df.loc[n, "Start_time"] = dt.datetime.strptime(
                start_date_str + "-" + txt_df.iloc[n]["Start_time"].strip(),
                "%d/%m/%Y-%H:%M:%S",
            ) + timedelta(days=1)

    return txt_df


def durationToSecond(rtf_df):
    for n in range(0, len(rtf_df)):
        if rtf_df.loc[n, "Duration"] is not None and (
            "00:" in rtf_df.loc[n, "Duration"]
        ):  ## assume if 00: exists this is duration in form "%H:%M:%S"
            time = dt.datetime.strptime(
                str(rtf_df.loc[n, "Duration"]).strip(), "%H:%M:%S"
            )
            rtf_df.loc[n, "Duration"] = (
                time.second + time.minute * 60 + time.hour * 3600
            )
        else:
            rtf_df.loc[n, "Duration"] = 0
    return rtf_df


def time_from_startToSeconds(rtf_df, start_date_str, start_dt, block_endings):
    minus_time = 0  # minus the time between the tests (excluded from the edf signals)
    test = 0
    block_endings.loc[len(block_endings), "Start_time_real"] = rtf_df.loc[
        len(rtf_df) - 1, "Start_time_real"
    ]
    for n in range(0, len(rtf_df)):
        time = dt.datetime.strptime(
            rtf_df.loc[n, "Time_from_start"].strip(), "%Hh%Mm%Ss"
        )

        if (
            rtf_df.loc[n, "Start_time_real"]
            > block_endings.loc[test, "Start_time_real"]
        ):
            minus_time += block_endings.loc[test, "Duration"]
            test = test + 1

        time = time - timedelta(seconds=int(minus_time))
        rtf_df.loc[n, "Time_from_start"] = (
            time.second + time.minute * 60 + time.hour * 3600
        )

    return rtf_df


## Import DELTAMED annotations


def annotationDeltamed(path, patient, edf_name):
    dataTXT_df = pd.read_table(
        path + patient + edf_name + ".TXT",
        skiprows=5,
        sep="\t",
        encoding="latin1",
        index_col=False,
        names=["Start_time_real", "Event_label"],
    )

    # find start date of annotations
    with open(path + patient + edf_name + ".TXT", "r", encoding="latin1") as file:
        sample_text = file.readlines()
        file.close()
    start_date_str = sample_text[2].split("\n")[0]
    start_datetime_dt = dt.datetime.strptime(
        start_date_str + "-" + dataTXT_df.iloc[0]["Start_time_real"],
        "%d/%m/%Y-%H:%M:%S",
    )

    # Only take the first annotation as rest of them are dublicates
    end_of_first_annotations = dataTXT_df[
        dataTXT_df["Start_time_real"] == "[FILE]"
    ].index.to_list()[0]
    dataTXT_df_cut = dataTXT_df.iloc[0:end_of_first_annotations, :].copy()

    Start_timeToStart_datetime(dataTXT_df_cut, start_date_str, start_datetime_dt)

    # Parse only sleep stages and end of block
    stages = [
        "Veille",
        "Stade 1",
        "Stade 2",
        "Stade 3",
        "S. Paradoxal",
        "Indéterminé",
        "//",
    ]
    sleep_df = dataTXT_df_cut.loc[dataTXT_df_cut["Event_label"].isin(stages)].copy()

    # Sleep stage duration info
    diff_dt = []
    for n in range(1, len(sleep_df)):
        dif = (
            sleep_df.iloc[n]["Start_time_real"]
            - sleep_df.iloc[n - 1]["Start_time_real"]
        )
        diff_dt.append(dif.seconds)
    diff_dt.append(30)

    sleep_df.loc[:, "Duration_tmp"] = diff_dt

    # Force sleep stages where duration>30 as 30 seconds (because they are always scored in 30 sec windows so this is the case of uncontinuity)
    stages_sleep = ["Veille", "Stade 1", "Stade 2", "Stade 3", "S. Paradoxal"]
    dur_new = []
    for ind, row in sleep_df.iterrows():
        if row["Event_label"] in stages_sleep and row["Duration_tmp"] > 30:
            dur_new.append(30)
        else:
            dur_new.append(row["Duration_tmp"])

    sleep_df.loc[:, "Duration"] = dur_new

    # for info about uncontinuity during block change
    block_ends = sleep_df.loc[sleep_df["Event_label"] == "//"].copy()
    block_ends.reset_index(inplace=True)

    # Time from start info
    from_start_dt = []
    time_running = 0
    for n in range(0, len(sleep_df)):
        from_start_dt.append(time_running)
        if sleep_df.iloc[n]["Event_label"] != "//":
            time_running += sleep_df.iloc[n]["Duration"]
        else:
            time_running += 0

    sleep_df.loc[:, "Time_from_start"] = from_start_dt

    # TODOO: Update start times to correspond to uncontinous recording? --> just create fake times to match sleeplab format

    start_dt_fake = []
    for n in range(0, len(sleep_df)):
        start_dt_fake.append(
            start_datetime_dt
            + dt.timedelta(seconds=int(sleep_df.iloc[n]["Time_from_start"]))
        )

    sleep_df.loc[:, "Start_time"] = start_dt_fake

    ##############################
    # Read events from RTF
    with open(path + patient + edf_name + ".rtf", "r", encoding="latin1") as file:
        sample_text = file.read()
        text = rtf_to_text(sample_text, encoding="latin1")
        x = re.sub(
            r"{\*?\\.+(;})|\s?\\[A-Za-z0-9]+|\s?{\s?\\[A-Za-z0-9]+\s?|\s?}\s?",
            ";",
            text,
        )
        lines = [line.split("  ") for line in x.split("\n")[15:-3]]
        res = [[el for el in sub if el != ""] for sub in lines]
        for row in res:
            if (
                len(row) > 5
            ):  # If true we assume long string in the end with double spaces and Duree missing
                event_tmp = "-".join(res[50][3:])
                [row.pop() for i in range(3, len(row))]
                row.append(event_tmp)
            if len(row) == 4:  # if True we assume Duree is missing and place '' there
                row.insert(-1, "")

    dataRTF_df = pd.DataFrame(
        res,
        columns=[
            "index",
            "Time_from_start",
            "Start_time_real",
            "Duration",
            "Event_label",
        ],
    )
    dataRTF_df.dropna(inplace=True, ignore_index=True)
    dataRTF_df.drop_duplicates(inplace=True, ignore_index=True)
    dataRTF_df = dataRTF_df.loc[
        dataRTF_df["Start_time_real"] != "Heure réelle"
    ].copy()  # in case of douple annotation inside rtf, drop the extra header rows
    dataRTF_df = dataRTF_df.drop(["index"], axis=1)
    dataRTF_df.reset_index(inplace=True)
    durationToSecond(dataRTF_df)
    Start_timeToStart_datetime2(dataRTF_df, start_date_str, start_datetime_dt)

    time_from_startToSeconds(dataRTF_df, start_date_str, start_datetime_dt, block_ends)

    # create faketime for sleeplab format

    start_dt_fake = []
    for n in range(0, len(dataRTF_df)):
        start_dt_fake.append(
            start_datetime_dt
            + dt.timedelta(seconds=int(dataRTF_df.iloc[n]["Time_from_start"]))
        )

    dataRTF_df.loc[:, "Start_time"] = start_dt_fake

    # Combine sleep stage and event info
    events_df = pd.concat([dataRTF_df, sleep_df], ignore_index=True)

    # Make some sorting and clean duplicates
    events_df.sort_values("Time_from_start", inplace=True, ignore_index=True)
    events_df.drop_duplicates(inplace=True, ignore_index=True)
    events_df = events_df.drop(["index"], axis=1).copy()
    events_df.reset_index(inplace=True)

    return events_df


## Import REMLOGIC annotations


def annotationRemlogic(path, patient, edf_name):
    sleep_stages = [
        # Remlogic
        "SLEEP-S0",
        "SLEEP-S1",
        "SLEEP-S2",
        "SLEEP-S3",
        "SLEEP-S4",
        "SLEEP-REM",
        "SLEEP-UNSCORED",
    ]

    SCORING_CHANNEL_INC = False
    SLEEPSTAGE_CHANNEL_MISSING = False
    POSITION_MISSING = False

    with open(path + patient + edf_name + ".TXT", "r", encoding="latin1") as file:
        sample_text = file.readlines()
        file.close()
    start_date_str = sample_text[3].split(":")[-1].split()[0]

    try:  # this text is before the scorings start
        rows_to_skip = sample_text.index(
            "Stade de sommeil\tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\n"
        )
        SCORING_CHANNEL_INC = False
    except:
        try:  # ...or this text
            rows_to_skip = sample_text.index(
                "Stade de sommeil\tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\tEmplacement\n"
            )
            SCORING_CHANNEL_INC = True
        except:
            try:  # maybe this?
                rows_to_skip = sample_text.index(
                    "Stade de sommeil\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\tEmplacement\n"
                )
                POSITION_MISSING = True
            except:
                try:  # lot of inconsistency....
                    rows_to_skip = sample_text.index(
                        "Position\tHeure [hh:mm:ss]\tEvénement\tDurée[s]\n"
                    )
                    SLEEPSTAGE_CHANNEL_MISSING = True
                except:  # please be this one, otherwise we will lose another patient.... :D
                    rows_to_skip = sample_text.index(
                        "tPosition\tHeure [hh:mm:ss]\tEvénement\tDurée[s]"
                    )
                    SLEEPSTAGE_CHANNEL_MISSING = True

    ## Load data
    if SCORING_CHANNEL_INC:  # sometimes extra scoring channel at the end
        dataTXT_df = pd.read_table(
            path + patient + edf_name + ".TXT",
            sep="\t",
            encoding="latin1",
            skiprows=rows_to_skip,
            on_bad_lines="warn",
            names=[
                "SleepStage",
                "Position",
                "Start_time",
                "Event_label",
                "Duration",
                "Scoring_channel",
            ],
            header=0,
        )
    elif (
        SLEEPSTAGE_CHANNEL_MISSING
    ):  # sometimes only four channels because sleepstage is missing (haven't check if scoring channel can exist in this case)
        dataTXT_df = pd.read_table(
            path + patient + edf_name + ".TXT",
            sep="\t",
            encoding="latin1",
            skiprows=rows_to_skip,
            on_bad_lines="warn",
            names=["Position", "Start_time", "Event_label", "Duration"],
            header=0,
        )
    elif (
        POSITION_MISSING
    ):  # sometimes position channel is missing and scoring channel is there
        dataTXT_df = pd.read_table(
            path + patient + edf_name + ".TXT",
            sep="\t",
            encoding="latin1",
            skiprows=rows_to_skip,
            on_bad_lines="warn",
            names=[
                "SleepStage",
                "Start_time",
                "Event_label",
                "Duration",
                "Scoring_channel",
            ],
            header=0,
        )
    else:  # most common case
        dataTXT_df = pd.read_table(
            path + patient + edf_name + ".TXT",
            sep="\t",
            encoding="latin1",
            skiprows=rows_to_skip,
            on_bad_lines="warn",
            names=["SleepStage", "Position", "Start_time", "Event_label", "Duration"],
            header=0,
        )

    start_datetime_dt = dt.datetime.strptime(
        start_date_str + "-" + dataTXT_df.iloc[0]["Start_time"], "%d/%m/%Y-%H:%M:%S"
    )
    Start_timeToStart_datetime_remlogic(dataTXT_df, start_date_str, start_datetime_dt)

    from_start_dt = []
    for n in range(0, len(dataTXT_df)):
        dif = dataTXT_df.iloc[n]["Start_time"] - dataTXT_df.iloc[0]["Start_time"]
        from_start_dt.append(dif.seconds)

    dataTXT_df.loc[:, "Time_from_start"] = from_start_dt

    # Drop sleep stages that are not 30 seconds
    # (e.g. 2014:PA328 don't know where these come from but they seem artifacts because overlapping with standard sleep staging)
    dataTXT_df2 = dataTXT_df.drop(
        dataTXT_df[
            (dataTXT_df["Event_label"].isin(sleep_stages))
            & (dataTXT_df["Duration"] != 30)
        ].index
    ).copy()

    dataTXT_df2.sort_values("Time_from_start", inplace=True, ignore_index=True)
    dataTXT_df2.drop_duplicates(inplace=True, ignore_index=True)

    return dataTXT_df2


def annotationCSV(path, patient, edf_name):

    data_csv = pd.read_csv(
        path + patient + edf_name + ".csv", encoding="UTF-16", delimiter="\t"
    )

    # Parse start date and time in to one column of datetime
    start_dt = []
    for n in range(0, len(data_csv)):
        datetime_start = dt.datetime.strptime(
            data_csv.iloc[n]["Start Date/Time: Date"]
            + "-"
            + data_csv.iloc[n]["Start Date/Time: Time - HH:MM:SS"],
            "%d/%m/%Y-%H:%M:%S",
        )
        start_dt.append(datetime_start)

    data_csv.loc[:, "Start_time"] = start_dt

    from_start_dt = []
    for n in range(0, len(data_csv)):
        dif = (
            data_csv.iloc[n]["Start_time"] - data_csv.iloc[0]["Start_time"]
        )  # change here the start time of the recording !!!
        from_start_dt.append(dif.seconds)

    data_csv.loc[:, "Time_from_start"] = from_start_dt

    # Parse duration to seconds
    duration_seconds = []
    for n in range(0, len(data_csv)):
        if np.isnan(data_csv.iloc[n]["Duration (total µs)"]):
            duration_seconds.append(0.0)
        else:
            duration_seconds.append(data_csv.iloc[n]["Duration (total µs)"] / 10e5)

    data_csv.loc[:, "Duration"] = duration_seconds

    # Copy Subtype as annotation event name
    event_labels = []
    for n in range(0, len(data_csv)):
        event_labels.append(data_csv.iloc[n]["Subtype"])

    data_csv.loc[:, "Event_label"] = event_labels

    # Parse sleep stages from edf+ header

    try:
        header = edf.read_edf_export(
            Path(path + patient + edf_name + ".edf"), annotations=True
        )[-1]
        st_rec = header["startdate"]
        keys = ["Validated", "Start_time", "Time_from_start", "Duration", "Event_label"]
        ann2 = []
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
## Remlogic annotations are composed of a .TXT file only.
## Some recordings only have .csv of the scoring


def loadAnnotation(path, patient, edf_name):

    # Changed logic because we might have Remlogic and Deltamed export in same folder
    # - thus more safe to read only the annotations that correspond to .edf filename
    # edf filename vs. annotation filename have some extra space ' ' and erros every now and then --> try with various edf_name
    # if annotation filenames don't have correct info, can't read annotations (hard to identify the correct files if patient has multiple edfs and annotations)
    # todo: could try to identify the correct files based on annotation and recording datetimes

    RECORDING_TYPE = None

    # First check if .rtf file exists - this is the most common recording type and .rtf should always exist
    path_ = Path(path + patient + edf_name + ".rtf")
    if path_.is_file():
        data = annotationDeltamed(
            path, patient, edf_name
        )  # Loading data with the function adapted to Deltamed export
        RECORDING_TYPE = "Deltamed"
    else:  # If no .rtf file found corresponding to edf name
        path_ = Path(path + patient + edf_name + ".TXT")
        if path_.is_file():  # check if there is a .TXT file
            with open(
                path + patient + edf_name + ".TXT", "rb"
            ) as file:  # Open .TXT file
                sample_text = file.read()
                file.close()
            if "RemLogic" in str(sample_text):  # Presence of the word RemLogic
                data = annotationRemlogic(
                    path, patient, edf_name
                )  # Loading data with the function adapted to RemLogic export
                RECORDING_TYPE = "RemLogic"
            else:
                RECORDING_TYPE = "Unknown"
                return None, RECORDING_TYPE
        else:  # if no .rtf file or .TXT file with correct filename
            # Check for .csv annotations
            path_ = Path(path + patient + edf_name + ".csv")
            if path_.is_file():
                data = annotationCSV(
                    path, patient, edf_name
                )  # Loading data with the function adapted to .csv annotations
                RECORDING_TYPE = "BrainRT"
            else:
                RECORDING_TYPE = "Unknown"
                # No .rtf, .TXT, or .csv files found inside the folder
                return None, RECORDING_TYPE
    return data, RECORDING_TYPE
