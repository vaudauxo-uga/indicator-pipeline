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

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        logger.info("Connexion SFTP fermée")
