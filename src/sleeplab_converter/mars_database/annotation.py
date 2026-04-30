from pathlib import Path
from typing import Tuple, Optional

import pandas as pd

from sleeplab_converter.mars_database.annotation_loader import AnnotationLoader


# Here I have fixed many inconsistency in sleep staging, but the timestamps still correspond to real time and cannot be used to map annotations to discontinous signals

# The final annotation dataframe contains the following columns no matter the source file:
## Time_from_start - Time from the first annotation (analysis start) in seconds (HOX: for sleeplab format this is changed to time from recording start in the converter)
## Start_time - Datetime for annotation/event start moment
## Duration - Duration of the annotation/event in seconds
## Event_label - Name of the event or the annotation label

# extra columns if available:
## Scoring_channel (Sometimes in Remlogig exports)
## Type Subtype Validated Description (csv file annotations)


def load_annotation(
    path: Path, patient: str, edf_name: str
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Main entry point for loading annotations for a given patient and recording.
    - Auto-detects annotation type: Deltamed (.rtf/.txt), RemLogic (.txt), or BrainRT (.csv)
    - Calls the appropriate parser
    - Returns harmonized annotation data

    Returns the annotation DataFrame and a string describing the recording type.
    """
    loader = AnnotationLoader()
    return loader.load(path, patient, edf_name)
