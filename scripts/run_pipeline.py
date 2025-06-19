import os

from dotenv import load_dotenv

from src.indicator_pipeline.sftp_client import SFTPClient

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

    files = sftp.list_files()
    print("Fichiers disponibles :", files)

    sftp.close()


if __name__ == "__main__":
    main()
