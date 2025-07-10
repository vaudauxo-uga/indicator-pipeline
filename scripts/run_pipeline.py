import os
from pathlib import PurePosixPath, Path
from typing import List

from dotenv import load_dotenv

from scripts.utils import get_local_slf_output
from src.indicator_pipeline.sftp_client import SFTPClient
from src.indicator_pipeline.slf_conversion import (
    convert_folder_to_slf,
    upload_slf_folders_to_server,
)

load_dotenv()


def main():
    host: str = os.getenv("SFTP_HOST")
    username: str = os.getenv("SFTP_USER")
    key_path: str = os.getenv("SFTP_KEY_PATH")
    password = os.getenv("SFTP_PASSWORD")
    port: int = int(os.getenv("SFTP_PORT"))
    sftp = SFTPClient(
        host=host, user=username, key_path=key_path, password=password, port=port
    )
    sftp.connect()

    years: List[str] = ["2020", "2023"]

    for year in years:
        server_year_dir: PurePosixPath = PurePosixPath().joinpath(
            "home", "hp2", "Raw_data", "PSG_data_MARS", "C1", year
        )
        local_slf_output: Path = get_local_slf_output()

        convert_folder_to_slf(local_slf_output, server_year_dir, sftp)
        upload_slf_folders_to_server(local_slf_output, server_year_dir, sftp_client=sftp)

    sftp.close()


if __name__ == "__main__":
    main()
