import os
from pathlib import PurePosixPath, Path

from dotenv import load_dotenv

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

    year: str = "2025"
    year_dir: PurePosixPath = PurePosixPath().joinpath(
        "home", "hp2", "Raw_data", "PSG_data_MARS", "C1", year
    )

    convert_folder_to_slf(year_dir, sftp)

    repo_root = Path(__file__).resolve().parent
    while ".git" not in [p.name for p in repo_root.iterdir()]:
        repo_root = repo_root.parent

    outside_repo_dir = repo_root.parent
    local_output_root = outside_repo_dir / "slf-output"

    upload_slf_folders_to_server(local_output_root, year_dir, sftp_client=sftp)

    sftp.close()


if __name__ == "__main__":
    main()
