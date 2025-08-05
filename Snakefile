import os
from pathlib import Path

DESKTOP = os.path.expanduser("~/Desktop")
SLF_OUTPUT = Path(DESKTOP) / "slf-output"

YEARS = config.get("years",[2022])

rule all:
    input:
        expand(str(SLF_OUTPUT / "slf_to_compute" / "{year}" / "PA21843_V2"),year=YEARS)

rule run_pipeline:
    output:
        directory(SLF_OUTPUT / "slf_to_compute" / "{year}" / "PA21843_V2")
    params:
        year="{year}",
        slf_output=str(SLF_OUTPUT)
    shell:
        """
        docker run --rm \
        --env-file .env \
          -v {params.slf_output}:/app/slf-output \
          indicator-pipeline run-pipeline --years {params.year}
        """
