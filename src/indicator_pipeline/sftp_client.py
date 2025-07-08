import stat
from pathlib import Path

import paramiko
import logging

logger = logging.getLogger(__name__)


class SFTPClient:
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
        logger.info(f"Connexion au serveur SFTP {self.host}:{self.port}")
        if self.key_path:
            private_key = paramiko.RSAKey.from_private_key_file(
                self.key_path, password=self.password
            )
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.user, pkey=private_key)
        else:
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.user, password=self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        logger.info("Connexion réussie")

    def list_files(self, path="."):
        return self.sftp.listdir(path)

    def download_file(self, remote_path, local_path):
        self.sftp.get(remote_path, local_path)

    def is_dir(self, path) -> bool:
        try:
            return stat.S_ISDIR(self.sftp.stat(path).st_mode)
        except IOError:
            return False

    def download_folder_recursive(self, remote_path: str, local_path: Path):
        local_path.mkdir(parents=True, exist_ok=True)
        for item in self.sftp.listdir(remote_path):
            remote_item: str = remote_path + "/" + item
            local_item = local_path / item
            if self.is_dir(remote_item):
                self.download_folder_recursive(remote_item, local_item)
            else:
                self.sftp.get(remote_item, str(local_item))

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        logger.info("Connexion SFTP fermée")
