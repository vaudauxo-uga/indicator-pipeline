import argparse
import logging
import os
from pathlib import PurePosixPath, Path

from dotenv import load_dotenv

from indicator_pipeline.excel_to_json import excel_to_json
from indicator_pipeline.logging_config import setup_logging
from indicator_pipeline.sftp_client import SFTPClient
from indicator_pipeline.slf_conversion import SLFConversion
from indicator_pipeline.utils import get_local_slf_output

logger = logging.getLogger(__name__)


def parse_args():

    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Convert EDF files to SLF format and upload them via SFTP."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        required=False,
        help="One or more years to process (e.g. --years 2023 2024)",
    )
    parser.add_argument(
        "--step",
        required=True,
        type=str,
        choices=["slf_conversion", "import_to_mars"],
        help="Choice of the pipeline's step to execute : 'slf_conversion' to convert psg data to slf folder or 'import_to_mars' to dump the data computed by ABOSA to MARS",
    )

    args = parser.parse_args()
    if args.step == "slf_conversion" and not args.years:
        parser.error("--years is required when --step is 'slf_conversion'")

    return parser.parse_args()


def main():

    args = parse_args()
    setup_logging(args.step)

    if args.step == "slf_conversion":
        logger.info(f"[START] Converting psg data for year(s) {'_'.join(args.years)}")

        host: str = os.getenv("SFTP_HOST")
        username: str = os.getenv("SFTP_USER")
        key_path: str = os.getenv("SFTP_KEY_PATH")
        password = os.getenv("SFTP_PASSWORD")
        port: int = int(os.getenv("SFTP_PORT"))
        sftp = SFTPClient(
            host=host, user=username, key_path=key_path, password=password, port=port
        )
        sftp.connect()

        for year in args.years:
            server_year_dir: PurePosixPath = PurePosixPath().joinpath(
                "home", "hp2", "Raw_data", "PSG_data_MARS", "C1", year
            )
            local_slf_output: Path = get_local_slf_output()

            try:
                patients = sftp.list_files(str(server_year_dir))
                logger.info(f"Found {len(patients)} patient folders: {patients}")
            except FileNotFoundError:
                logger.warning(
                    f"[SKIP] Année {year} introuvable sur le SFTP ({server_year_dir}). Passage à l'année suivante.")
                continue

            if not patients:
                logger.info(f"[INFO] Aucune donnée trouvée pour l'année {year}.")
                continue

            slf_converter: SLFConversion = SLFConversion(
                local_slf_output, server_year_dir, sftp
            )
            slf_converter.convert_folder_to_slf(year, patients)
            slf_converter.upload_slf_folders_to_server()

        sftp.close()

    else:
        excel_to_json()


if __name__ == "__main__":
    main()
