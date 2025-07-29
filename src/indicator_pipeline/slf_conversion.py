import logging
import tempfile
from pathlib import Path, PurePosixPath
from typing import List

from indicator_pipeline.sftp_client import SFTPClient
from indicator_pipeline.utils import parse_patient_and_visit
from sleeplab_converter.mars_database.convert import convert_dataset

logger = logging.getLogger(__name__)


def convert_folder_to_slf(
    local_slf_output: Path, year_dir: PurePosixPath, sftp_client: SFTPClient
):
    """
    Downloads all patient folders for a given year from a remote SFTP server in a temporary folder,
    skips those that already contain an SLF output folder,
    and converts the remaining ones to the .slf format using MARS sleeplab-converter.
    The resulting .slf folders are saved outside the Git repository, in a sibling folder named 'slf-output'.

    Args:
        local_slf_output (Path): Path to the local slf output folder.
        year_dir (PurePosixPath): Remote path to the year folder on the SFTP server (e.g., /.../C1/2025).
        sftp_client (SFTPClient): An active SFTP client for accessing and downloading remote data.

    Returns:
        None
    """

    with tempfile.TemporaryDirectory() as tmp_root_dir:
        tmp_root_path: Path = Path(tmp_root_dir)

        local_year_dir: Path = tmp_root_path / year_dir.name
        local_year_dir.mkdir(parents=True, exist_ok=True)

        patients = sftp_client.list_files(str(year_dir))
        for patient_id in patients:
            remote_patient_path: PurePosixPath = year_dir / patient_id
            existing_folders = sftp_client.list_files(str(remote_patient_path))
            slf_folders: List[str] = [
                name
                for name in existing_folders
                if name.startswith(f"slf_{patient_id}")
            ]

            if slf_folders:
                logger.info(f"[SKIP] SLF already exists")
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
            output_dir=local_slf_output,
            series=year_dir.name,
            ds_name="slf_to_compute",
        )


def upload_slf_folders_to_server(
    local_slf_output: Path, remote_year_dir: PurePosixPath, sftp_client: SFTPClient
):
    """
    Uploads all SLF folders from a local output directory to the corresponding year directory on the remote server.
    Skips uploads if the patient folder name does not match the .edf filename(s) found on the remote server.
    """

    local_year_dir: Path = local_slf_output / "slf_to_compute" / remote_year_dir.name
    if not local_year_dir.exists():
        logger.warning(f"Local year directory not found: {local_year_dir}")
        return

    for patient_folder in local_year_dir.iterdir():
        if not patient_folder.is_dir():
            continue

        folder_patient_id: str = patient_folder.name.split("_")[0]
        slf_remote_name: str = f"slf_{patient_folder.name}"
        remote_patient_dir: PurePosixPath = remote_year_dir / folder_patient_id / slf_remote_name

        remote_raw_dir: PurePosixPath = remote_year_dir / folder_patient_id
        try:
            remote_files: List[str] = sftp_client.list_files(str(remote_raw_dir))
        except Exception as e:
            logger.warning(f"[SKIP] Unable to list remote files for {remote_raw_dir}: {e}")
            continue

        edf_files: List[str] = [f for f in remote_files if f.lower().endswith(".edf")]

        inconsistent: bool = False
        for edf in edf_files:
            expected_patient_id, _ = parse_patient_and_visit(edf)
            if expected_patient_id and expected_patient_id != folder_patient_id.replace("PA", ""):
                logger.warning(
                    f"[SKIP] Inconsistent patient ID: folder = {folder_patient_id}, "
                    f"EDF = {edf} (expected = {expected_patient_id})"
                )
                inconsistent = True
                break

        if inconsistent:
            continue

        logger.info(f"[UPLOAD] Uploading {patient_folder} to {remote_patient_dir}")
        sftp_client.upload_folder_recursive(patient_folder, str(remote_patient_dir))
