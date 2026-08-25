from datetime import datetime, timedelta

import pandas as pd

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
                f"{start_date_str}-{txt_df.iloc[n]['Start_time'].strip()}",
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
