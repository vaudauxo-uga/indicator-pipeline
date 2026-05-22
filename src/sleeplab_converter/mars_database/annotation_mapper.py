from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sleeplab_format.models import Annotation, AASMSleepStage, AASMEvent


@dataclass
class AnnotationMappingResult:
    events: List[Annotation[str]]
    sleep_stages: List[Annotation[AASMSleepStage]]
    aasm_events: List[Annotation[AASMEvent]]
    analysis_start: Optional[datetime]
    analysis_end: Optional[datetime]
    lights_off: Optional[datetime]
    lights_on: Optional[datetime]
