from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd

from sleeplab_converter.edf_reader import EDFReader
from sleeplab_converter.mars_database.parsers.base import BaseAnnotationParser
from sleeplab_converter.mars_database.time_helpers import DATETIME_FORMAT


def annotation_csv(path: Path, patient: str, edf_name: str) -> pd.DataFrame:
    """
    Parses annotations from a .csv file (BrainRT export).
    Return the annotations with time, duration, and label, ready for Sleeplab format.
    """
    csv_path: Path = path / patient / f"{edf_name}.csv"
    data_csv: pd.DataFrame = pd.read_csv(csv_path, encoding="UTF-16", delimiter="\t")

    # Parse start date and time in to one column of datetime
    start_dt: List[datetime] = []
    for n in range(0, len(data_csv)):
        datetime_start = datetime.strptime(
            f"{data_csv.iloc[n]['Start Date/Time: Date']}-{data_csv.iloc[n]['Start Date/Time: Time - HH:MM:SS']}",
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
    edf_path: Path = path / patient / f"{edf_name}.edf"
    try:
        header = EDFReader(edf_path, annotations=True).read()[-1]
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


class BrainRTParser(BaseAnnotationParser):
    name = "BrainRT"

    def detect(self, folder: Path, edf_name: str) -> bool:
        return (folder / f"{edf_name}.csv").is_file()

    def parse(self, path: Path, patient: str, edf_name: str):
        return annotation_csv(path, patient, edf_name)
