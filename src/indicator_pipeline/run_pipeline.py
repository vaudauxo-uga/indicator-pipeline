import argparse
import os
from pathlib import PurePosixPath, Path

from dotenv import load_dotenv

from indicator_pipeline.logging_config import setup_logging
from indicator_pipeline.sftp_client import SFTPClient
from indicator_pipeline.slf_conversion import SLFConversion
from indicator_pipeline.utils import get_local_slf_output


def parse_args():

    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Convert EDF files to SLF format and upload them via SFTP."
    )
    parser.add_argument(
        "--years",
        nargs="+",
        required=True,
        help="One or more years to process (e.g. --years 2023 2024)",
    )

    return parser.parse_args()


def main():

    args = parse_args()
    setup_logging(args.years)

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

        slf_converter: SLFConversion = SLFConversion(
            local_slf_output, server_year_dir, sftp
        )
        slf_converter.convert_folder_to_slf()
        slf_converter.upload_slf_folders_to_server()

    sftp.close()


if __name__ == "__main__":
    main()
