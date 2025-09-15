import logging
import tempfile
from pathlib import Path, PurePosixPath
from typing import List, Dict, Tuple, Set

from indicator_pipeline.sftp_client import SFTPClient
from indicator_pipeline.utils import parse_patient_and_visit, lowercase_extensions, load_slf_usage, save_slf_usage, \
    extract_visits
from sleeplab_converter.mars_database.convert import convert_dataset

logger = logging.getLogger(__name__)


class SLFConversion:
    """
    Handles the conversion and upload of polysomnographic recordings
    into the SLF (SleepLab Format) structure for a given year.

    Args:
    local_slf_output (Path): Path to the local slf output folder.
    remote_year_dir (PurePosixPath): Remote path to the year folder on the SFTP server (e.g., /.../C1/2025).
    sftp_client (SFTPClient): An active SFTP client for accessing and downloading remote data.
    """

    def __init__(
            self,
            local_slf_output: Path,
            remote_year_dir: PurePosixPath,
            sftp_client: SFTPClient,
    ):
        self.local_slf_output = local_slf_output
        self.remote_year_dir = remote_year_dir
        self.sftp_client = sftp_client

    def add_slf_usage(self):
        """
        Update the SLF usage tracking file (slf_usage.json) with any new SLF datasets.
        This method scans the local `slf_to_compute/<year>` directory to detect
        newly converted SLF folders.
        """
        slf_usage: Dict[str, Dict[str, bool]] = load_slf_usage()

        new_slf_dir = self.local_slf_output / "slf_to_compute" / self.remote_year_dir.name
        new_slf_ids = [d.name for d in new_slf_dir.iterdir() if d.is_dir()]

        for slf_id in new_slf_ids:
            if slf_id not in slf_usage:
                slf_usage[slf_id] = {"abosa": False}
            else:
                slf_usage[slf_id].setdefault("abosa", False)

        save_slf_usage(slf_usage)

    def check_patient_visits(self, remote_patient_path: PurePosixPath) -> Tuple[bool, List[str], bool]:
        """
        Checks whether all T1 visits for a patient already have an associated slf folder.
        Returns :
            - all_psg_converted: bool => if all T1 visits have an associated slf folder
            - missing_visits: List[str] => list of visits (e.g., ["V1", "V2"]) without slf
            - has_valid_psg: bool => if the patient folder has at least one valid T1 visits to convert
        """
        existing_files: List[str] = self.sftp_client.list_files(str(remote_patient_path))
        expected_visits: List[str] = extract_visits(existing_files)
        slf_folders: List[str] = [name for name in existing_files if name.startswith("slf_")]

        if not expected_visits:
            return True, expected_visits, False

        missing_visits: List[str] = []
        for visit in expected_visits:
            if not any(visit in slf for slf in slf_folders):
                missing_visits.append(visit)

        return len(missing_visits) == 0, missing_visits, True

    def convert_folder_to_slf(self, patients: List[str]):
        """
        Downloads all patient folders for a given year from a remote SFTP server in a temporary folder,
        skips those that already contain an SLF output folder,
        and converts the remaining ones to the .slf format using MARS sleeplab-converter.
        The resulting .slf folders are saved outside the Git repository, in a sibling folder named 'slf-output'.
        """

        with tempfile.TemporaryDirectory() as tmp_root_dir:
            tmp_root_path: Path = Path(tmp_root_dir)

            local_year_dir: Path = tmp_root_path / self.remote_year_dir.name
            local_year_dir.mkdir(parents=True, exist_ok=True)

            downloaded_count: int = 0
            for patient_id in patients:
                remote_patient_path: PurePosixPath = self.remote_year_dir / patient_id
                all_psg_converted, missing_visits, has_valid_psg = self.check_patient_visits(remote_patient_path)

                if not has_valid_psg:
                    logger.info(f"[SKIP] No valid T1 PSG found for {patient_id}")
                    continue

                if all_psg_converted:
                    logger.info(f"[SKIP] All SLF already exist for {patient_id}")
                    continue
                else:
                    logger.info(f"[PROCESS] Missing visits for {patient_id}: {missing_visits}")

                local_patient_dir: Path = local_year_dir / patient_id
                remote_files: List[str] = self.sftp_client.list_files(str(remote_patient_path))
                valid_exts = (".edf", ".txt", ".rtf", ".csv")

                files_to_download: List[str] = [
                    f
                    for f in remote_files
                    if f.lower().endswith(valid_exts) and "T1-" in f and any(visit in f for visit in missing_visits)
                ]

                for f in files_to_download:
                    remote_file_path = remote_patient_path / f
                    local_file_path = local_patient_dir / f
                    self.sftp_client.download_file(str(remote_file_path), local_file_path)

                logger.info(f"[COPY] Copied missing visits {missing_visits} locally to {local_patient_dir}")
                lowercase_extensions(local_patient_dir)
                downloaded_count += 1

            if downloaded_count > 0:
                logger.info(
                    f"[SUMMARY] Downloaded {downloaded_count} patient(s). Starting conversion..."
                )

                convert_dataset(
                    input_dir=tmp_root_path,
                    output_dir=self.local_slf_output,
                    series=self.remote_year_dir.name,
                    ds_name="slf_to_compute",
                )

                self.add_slf_usage()

                logger.info(f"[CONVERT] Finished conversion for {downloaded_count} patient(s)")

    def upload_slf_folders_to_server(self):
        """
        Uploads all SLF folders from a local output directory to the corresponding year directory on the remote server.
        Skips uploads if the patient folder name does not match the .edf filename(s) found on the remote server.
        """

        local_year_dir: Path = (
                self.local_slf_output / "slf_to_compute" / self.remote_year_dir.name
        )
        if not local_year_dir.exists():
            logger.warning(f"Local year directory not found: {local_year_dir}")
            return

        for patient_folder in local_year_dir.iterdir():
            if not patient_folder.is_dir():
                continue

            folder_patient_id: str = patient_folder.name.split("_")[0]

            remote_raw_dir: PurePosixPath = self.remote_year_dir / folder_patient_id
            all_psg_converted, missing_visits = self.check_patient_visits(remote_raw_dir)
            if all_psg_converted:
                logger.info(f"[SKIP] All SLF already exist for {folder_patient_id}")
                continue
            else:
                logger.info(f"[UPLOAD] Missing SLF for visits: {missing_visits}")

            try:
                remote_files: List[str] = self.sftp_client.list_files(
                    str(remote_raw_dir)
                )
            except Exception as e:
                logger.warning(
                    f"[SKIP] Unable to list remote files for {remote_raw_dir}: {e}"
                )
                continue

            edf_files: List[str] = [
                f for f in remote_files if f.lower().endswith(".edf")
            ]

            inconsistent: bool = False
            for edf in edf_files:
                expected_patient_id, _ = parse_patient_and_visit(edf)
                if (
                        expected_patient_id
                        and expected_patient_id != folder_patient_id.replace("PA", "")
                ):
                    logger.warning(
                        f"[SKIP] Inconsistent patient ID: folder = {folder_patient_id}, "
                        f"EDF = {edf} (expected = {expected_patient_id})"
                    )
                    inconsistent = True
                    break

            if inconsistent:
                continue

            for visit in missing_visits:
                expected_name = f"{folder_patient_id}_{visit}"
                local_visit_folder = local_year_dir / expected_name
                if not local_visit_folder.exists():
                    logger.warning(f"[SKIP] Missing local folder {expected_name}")
                    continue

                slf_remote_name = f"slf_{local_visit_folder.name}"
                remote_visit_dir = self.remote_year_dir / folder_patient_id / slf_remote_name

                logger.info(f"[UPLOAD] Uploading {local_visit_folder} to {remote_visit_dir}")
                self.sftp_client.upload_folder_recursive(
                    local_visit_folder, str(remote_visit_dir)
                )
