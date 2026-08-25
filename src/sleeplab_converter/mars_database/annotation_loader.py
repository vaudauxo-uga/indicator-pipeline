import logging
from pathlib import Path
from typing import Tuple, Optional

import pandas as pd

from sleeplab_converter.mars_database.parsers.brainrt import BrainRTParser
from sleeplab_converter.mars_database.parsers.deltamed import DeltamedParser
from sleeplab_converter.mars_database.parsers.remlogic import RemLogicParser

logger = logging.getLogger(__name__)


class AnnotationLoader:
    def __init__(self):
        self.parsers = [
            DeltamedParser(),
            RemLogicParser(),
            BrainRTParser(),
        ]

    def load(
        self,
        path: Path,
        patient: str,
        edf_name: str,
    ) -> Tuple[Optional[pd.DataFrame], str]:

        folder = path / patient

        for parser in self.parsers:
            if parser.detect(folder, edf_name):
                try:
                    data = parser.parse(path, patient, edf_name)
                    return data, parser.name
                except Exception as e:
                    logger.error(
                        f"[ERROR] Impossible to parse the {parser.name} file: {e}"
                    )
                    return None, parser.name

        return None, "Unknown"
