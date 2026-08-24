from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sleeplab_format.models import Annotation, AASMSleepStage, AASMEvent

from sleeplab_converter.events_mapping import STAGE_MAPPING, AASM_EVENT_MAPPING


@dataclass
class AnnotationMappingResult:
    events: list[Annotation[str]]
    sleep_stages: list[Annotation[AASMSleepStage]]
    aasm_events: list[Annotation[AASMEvent]]
    analysis_start: Optional[datetime]
    analysis_end: Optional[datetime]
    lights_off: Optional[datetime]
    lights_on: Optional[datetime]


class AnnotationMapper:

    LIGHTS_OFF_LABELS = {
        "Lumières éteintes",
        " LUMIERE ETEINTE",
        " ETEINT LA LUMIERE",
    }

    LIGHTS_ON_LABELS = {
        "Lumières éteintes",
        " LUMIERE ALLUMEE",
        " ALLUME LA LUMIERE",
        " LUMIERE ALLUMEE 6H01",
    }

    ANALYSIS_START_LABEL = "ANALYSIS-START"
    ANALYSIS_STOP_LABEL = "ANALYSIS-STOP"

    def __init__(self, start_datetime: datetime, annot_df: pd.DataFrame):
        self.start_datetime = start_datetime
        self.annot_df = annot_df

    def map(self) -> AnnotationMappingResult:
        """
        Convert annotation dataframe rows into structured annotation objects.
        """
        if self.annot_df.empty:
            return AnnotationMappingResult(
                events=[],
                sleep_stages=[],
                aasm_events=[],
                analysis_start=None,
                analysis_end=None,
                lights_off=None,
                lights_on=None,
            )

        self.annot_df = self.annot_df.copy()
        self._synchronize_time_from_start()

        events: list[Annotation[str]] = []
        sleep_stages: list[Annotation[AASMSleepStage]] = []
        aasm_events: list[Annotation[AASMEvent]] = []

        analysis_start = None
        analysis_end = None
        lights_off = None
        lights_on = None

        for _, row in self.annot_df.iterrows():
            events.append(
                Annotation[str](
                    name=row["Event_label"],
                    start_ts=row["Start_time"],
                    start_sec=row["Time_from_start"],
                    duration=row["Duration"],
                )
            )

            sleep_stage = self._parse_sleep_stage(row)
            if sleep_stage is not None:
                sleep_stages.append(sleep_stage)

            aasm_event = self._parse_aasm_event(row)
            if aasm_event is not None:
                aasm_events.append(aasm_event)

            if row["Event_label"] == "ANALYSIS-START":
                analysis_start = row["Start_time"]

            if row["Event_label"] == "ANALYSIS-STOP":
                analysis_end = row["Start_time"]

            if row["Event_label"] in self.LIGHTS_OFF_LABELS:
                lights_off = row["Start_time"]

            if row["Event_label"] in self.LIGHTS_ON_LABELS:
                lights_on = row["Start_time"]

        if analysis_start is None:
            analysis_start = events[0].start_ts

        if analysis_end is None:
            analysis_end = events[-1].start_ts + timedelta(seconds=events[-1].duration)

        return AnnotationMappingResult(
            events=events,
            sleep_stages=sleep_stages,
            aasm_events=aasm_events,
            analysis_start=analysis_start,
            analysis_end=analysis_end,
            lights_off=lights_off,
            lights_on=lights_on,
        )

    def _synchronize_time_from_start(self) -> None:
        """
        Recompute Time_from_start relative to EDF recording start.
        """
        first_annotation_start = self.annot_df.iloc[0]["Start_time"]

        if self.start_datetime == first_annotation_start:
            return

        for idx, row in self.annot_df.iterrows():
            delta = row["Start_time"] - self.start_datetime
            self.annot_df.loc[idx, "Time_from_start"] = delta.seconds

    @staticmethod
    def _parse_sleep_stage(row: pd.Series) -> Optional[Annotation[AASMSleepStage]]:
        """Parses row and return the sleep stage in the sleeplab format."""

        if row["Event_label"] in STAGE_MAPPING.keys():
            return Annotation[AASMSleepStage](
                name=STAGE_MAPPING[row["Event_label"]],
                start_ts=row["Start_time"],
                start_sec=row["Time_from_start"],
                duration=row["Duration"],
            )

        return None

    @staticmethod
    def _parse_aasm_event(row: pd.Series) -> Optional[Annotation[AASMEvent]]:
        """Parses row and return the aasm event in the sleeplab format."""

        if row["Event_label"] not in AASM_EVENT_MAPPING:
            return None

        if "Validated" in row and row["Validated"] != "Yes":
            return None

        return Annotation[AASMEvent](
            name=AASM_EVENT_MAPPING[row["Event_label"]],
            start_ts=row["Start_time"],
            start_sec=row["Time_from_start"],
            duration=row["Duration"],
        )
