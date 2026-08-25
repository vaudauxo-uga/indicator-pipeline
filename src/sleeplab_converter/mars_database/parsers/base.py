from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd


class BaseAnnotationParser(ABC):
    name: str = "Unknown"

    @abstractmethod
    def detect(self, folder: Path, edf_name: str) -> bool:
        """Return True if this parser matches the recording."""
        pass

    @abstractmethod
    def parse(self, path: Path, patient: str, edf_name: str) -> Optional[pd.DataFrame]:
        """Parse annotations and return harmonized dataframe."""
        pass
