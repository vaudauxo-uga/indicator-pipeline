import os
from datetime import datetime
from pathlib import Path

DESKTOP = os.path.expanduser("~/Desktop")
SLF_OUTPUT = Path(DESKTOP) / "slf-output"
LOGS_DIR = Path(DESKTOP) / "indicator-pipeline" / "logs"
ABOSA_OUTPUT = Path(DESKTOP) / "abosa-output"

DEFAULT_YEAR = str(datetime.now().year)
YEARS = str(config.get("years",DEFAULT_YEAR)).split()
ABOSA_VERSION = str(config.get("abosa_version", "v1.2.2"))


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
        "cleanup.done"


rule run_pipeline:
    output:
        touch("slf_conversion.done")
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
        "slf_conversion.done"
    output:
        "abosa_complete.flag"
    message:
        "==> Étape manuelle requise : préparez les données, puis créez le fichier 'abosa_complete.flag' pour continuer"
    run:
        print("⚠️ Étape manuelle requise. Créez le fichier 'abosa_complete.flag' pour continuer.")
        import sys

        sys.exit("Arrêt volontaire : étape manuelle à réaliser.")


rule import_to_mars:
    input:
        "abosa_complete.flag"
    output:
        touch("analysis_complete.done")
    params:
        logs_dir=docker_path(LOGS_DIR),
        abosa_output=docker_path(ABOSA_OUTPUT),
        abosa_version=ABOSA_VERSION
    shell:
        """
        docker run --rm \
          --env-file .env \
          -v {params.logs_dir}:/app/logs \
          -v {params.abosa_output}:/abosa-output \
          indicator-pipeline run-pipeline --step import_to_mars --abosa-version {params.abosa_version}
        """

rule cleanup_slf:
    input:
        "analysis_complete.done",
    output:
        touch("cleanup.done")
    run:
        import json
        from pathlib import Path
        import shutil

        slf_usage_file = LOGS_DIR / "slf_usage.json"
        slf_dir = SLF_OUTPUT / "slf_to_compute"

        with open(slf_usage_file) as f:
            slf_usage = json.load(f)

        cleaned = []
        skipped = []

        for sample, indicators in slf_usage.items():
            if all(indicators.values()):
                sample_files = list(slf_dir.glob(f"*/{sample}*"))
                if not sample_files:
                    skipped.append(sample)
                    continue
                for f in sample_files:
                    try:
                        if f.is_file():
                            f.unlink()
                        elif f.is_dir():
                            shutil.rmtree(f)
                        cleaned.append(str(f))
                    except Exception as e:
                        print(f"⚠️ Erreur suppression {f}: {e}")
            else:
                skipped.append(sample)

        if cleaned:
            print("✅ Fichiers supprimés :")
            for f in cleaned:
                print("  -",f)

        if skipped:
            print("⏩ Non supprimés (indicateurs incomplets) :")
            for s in skipped:
                print("  -",s)


rule clean:
    run:
        import os

        for f in [
            "slf_conversion.done",
            "analysis_complete.done",
            "cleanup.done",
            "abosa_complete.flag"
        ]:
            try:
                os.remove(f)
                print(f"Supprimé : {f}")
            except FileNotFoundError:
                pass
        print("✅ Tous les fichiers .done et .flag ont été supprimés.")
