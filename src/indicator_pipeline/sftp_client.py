import stat
from pathlib import Path
from typing import List

import paramiko
import logging

logger = logging.getLogger(__name__)


class SFTPClient:
    """
    A simplified wrapper around Paramiko's SFTP client for interacting with remote SFTP servers.

    This class supports both password-based and key-based authentication, and provides methods
    for connecting, listing files, downloading and uploading individual files or entire folders
    recursively, and closing the connection.
    """
    def __init__(
        self,
        host: str,
        user: str = "",
        key_path: str = "",
        password: str = "",
        port: int = 22,
    ):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.password = password
        self.port = port
        self.transport = None
        self.sftp = None

    def connect(self):
        """
        Establishes a connection to the remote SFTP server.
        Uses SSH key authentication if `key_path` is provided; otherwise, falls back to password authentication.
        Initializes the internal SFTP client.
        """
        logger.info(f"Connecting to SFTP server {self.host}:{self.port}")
        if self.key_path:
            private_key = paramiko.RSAKey.from_private_key_file(
                self.key_path, password=self.password
            )
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.user, pkey=private_key)
        else:
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.banner_timeout = 45
            self.transport.connect(username=self.user, password=self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        logger.info("Connection successful")

    def list_files(self, path=".") -> List[str]:
        """
        Lists files names and directories at the specified remote path.
        """
        return self.sftp.listdir(path)

    def is_dir(self, path: str) -> bool:
        """
        Checks if the given remote path is a directory.
        """
        try:
            return stat.S_ISDIR(self.sftp.stat(path).st_mode)
        except IOError:
            return False

    def download_folder_recursive(self, remote_path: str, local_path: Path):
        """
        Recursively downloads a remote folder and its contents to a local directory.
        """
        local_path.mkdir(parents=True, exist_ok=True)
        for item in self.sftp.listdir(remote_path):
            remote_item: str = remote_path + "/" + item
            local_item = local_path / item
            if self.is_dir(remote_item):
                self.download_folder_recursive(remote_item, local_item)
            else:
                self.sftp.get(remote_item, str(local_item))

    def upload_folder_recursive(self, local_path: Path, remote_path: str):
        """
        Recursively uploads a local directory and its content to the SFTP server.
        """
        try:
            self.sftp.stat(remote_path)
        except FileNotFoundError:
            self.sftp.mkdir(remote_path)

        for item in local_path.iterdir():
            remote_item = remote_path + "/" + item.name
            if item.is_dir():
                self.upload_folder_recursive(item, remote_item)
            else:
                self.sftp.put(str(item), remote_item)

    def close(self):
        """
        Closes the SFTP connection and associated resources.
        """
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        logger.info("SFTP connection closed")
