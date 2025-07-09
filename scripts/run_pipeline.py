import os
from pathlib import PurePosixPath

from dotenv import load_dotenv

from src.indicator_pipeline.sftp_client import SFTPClient
from src.indicator_pipeline.slf_conversion import convert_folder_to_slf

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

    year: str = "2025"
    year_dir: PurePosixPath = PurePosixPath().joinpath(
        "home", "hp2", "Raw_data", "PSG_data_MARS", "C1", year
    )

    convert_folder_to_slf(year_dir, sftp)

    sftp.close()


if __name__ == "__main__":
    main()
