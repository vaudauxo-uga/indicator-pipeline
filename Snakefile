import os
from datetime import datetime
from pathlib import Path

DESKTOP = os.path.expanduser("~/Desktop")
SLF_OUTPUT = Path(DESKTOP) / "slf-output"
LOGS_DIR = Path(DESKTOP) / "indicator-pipeline" / "logs"
ABOSA_OUTPUT = Path(DESKTOP) / "abosa-output"

DEFAULT_YEAR = str(datetime.now().year)
YEARS = config.get("years",DEFAULT_YEAR).split()


def docker_path(p):
    """
    Convert a Windows-style file path to a Docker-compatible Unix-style path.
    """
    p = Path(p).absolute()
    drive = p.drive[0].lower()
    path_no_drive = str(p)[len(p.drive):].replace('\\','/')
    return f"/{drive}{path_no_drive}"


rule all:
    input:
        "step2.done"


rule run_pipeline:
    output:
        touch("step1.done")
    params:
        years=" ".join(str(y) for y in YEARS),
        slf_output=docker_path(SLF_OUTPUT),
        logs_dir=docker_path(LOGS_DIR)
    shell:
        """
        docker run --rm \
          --env-file .env \
          -v {params.logs_dir}:/app/logs \
          -v {params.slf_output}:/app/slf-output \
          indicator-pipeline run-pipeline --step slf_conversion --years {params.years}
        """


rule wait_for_manual_step:
    input:
        "step1.done"
    output:
        "manual_ready.flag"
    message:
        "==> Étape manuelle requise : préparez les données, puis créez le fichier 'manual_ready.flag' pour continuer"
    run:
        print("⚠️ Étape manuelle requise. Créez le fichier 'manual_ready.flag' pour continuer.")
        import sys

        sys.exit("Arrêt volontaire : étape manuelle à réaliser.")


rule import_to_mars:
    input:
        "manual_ready.flag"
    output:
        touch("step2.done")
    params:
        logs_dir=docker_path(LOGS_DIR),
        abosa_output=docker_path(ABOSA_OUTPUT)
    shell:
        """
        docker run --rm \
          --env-file .env \
          -v {params.logs_dir}:/app/logs \
          -v {params.abosa_output}:/abosa-output \
          indicator-pipeline run-pipeline --step import_to_mars
        """

rule clean:
    run:
        import os

        for f in ["step1.done", "step2.done", "manual_ready.flag"]:
            try:
                os.remove(f)
                print(f"Supprimé : {f}")
            except FileNotFoundError:
                pass
        print("✅ Tous les fichiers .done et .flag ont été supprimés.")
