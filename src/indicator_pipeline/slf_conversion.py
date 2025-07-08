import logging
import tempfile
from pathlib import Path, PurePosixPath

from sleeplab_converter.mars_database.convert import convert_dataset
from src.indicator_pipeline.sftp_client import SFTPClient

logger = logging.getLogger(__name__)


def convert_folder_to_slf(year_dir: PurePosixPath, sftp_client: SFTPClient):
    """
    Downloads all patient folders for a given year from a remote SFTP server in a temporary folder,
    skips those that already contain an SLF output folder,
    and converts the remaining ones to the .slf format using MARS sleeplab-converter.
    The resulting .slf folders are saved outside the Git repository, in a sibling folder named 'slf-output'.

    Args:
        year_dir (PurePosixPath): Remote path to the year folder on the SFTP server (e.g., /.../C1/2025).
        sftp_client (SFTPClient): An active SFTP client for accessing and downloading remote data.

    Returns:
        None
    """

    repo_root = Path(__file__).resolve().parent
    while ".git" not in [p.name for p in repo_root.iterdir()]:
        repo_root = repo_root.parent

    outside_repo_dir = repo_root.parent
    local_output_root = outside_repo_dir / "slf-output"
    print(local_output_root)
    local_output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_root_dir:
        tmp_root_path: Path = Path(tmp_root_dir)

        local_year_dir: Path = tmp_root_path / year_dir.name
        local_year_dir.mkdir(parents=True, exist_ok=True)

        patients = sftp_client.list_files(str(year_dir))
        for patient_id in patients:
            remote_patient_path: PurePosixPath = year_dir / patient_id
            slf_folder_name: str = f"slf_{patient_id}_V1"
            remote_slf_path: PurePosixPath = remote_patient_path / slf_folder_name

            if slf_folder_name in sftp_client.list_files(str(remote_patient_path)):
                logger.info(f"[SKIP] SLF already exists: {remote_slf_path}")
                continue

            local_patient_dir: Path = local_year_dir / patient_id
            sftp_client.download_folder_recursive(
                str(remote_patient_path), local_patient_dir
            )
            logger.info(
                f"[COPY] Copied patient {patient_id} locally to {local_patient_dir}"
            )

        convert_dataset(
            input_dir=tmp_root_path,
            output_dir=local_output_root,
            series=year_dir.name,
            ds_name="slf_to_compute",
        )
