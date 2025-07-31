import logging
from datetime import datetime
from pathlib import Path
from typing import List


def setup_logging(years: List[str]) -> None:
    """
    Sets up logging for the pipeline with one main and one warning/error log file.
    The logs are stored in the "logs" directory and include the specified years and a timestamp.
    """
    Path("logs").mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    years_str = "_".join(years)
    full_log = f"logs/pipeline_{years_str}_{timestamp}.log"
    warn_log = f"logs/warnings_and_errors_{years_str}_{timestamp}.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(full_log, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    warn_handler = logging.FileHandler(warn_log, encoding="utf-8")
    warn_handler.setLevel(logging.WARNING)
    warn_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(warn_handler)
    logger.addHandler(stream_handler)

    logging.info(f"Logging initialized. Full log: {full_log}")
    logging.info(f"Warnings & errors logged to: {warn_log}")
