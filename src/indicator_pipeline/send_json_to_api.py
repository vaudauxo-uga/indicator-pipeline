import logging
import os
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

API_URL = "https://staging.mars-database.science/api/internal/v1/recordings"
API_TOKEN = os.getenv("API_TOKEN")

HEADERS: Dict[str, str] = {
    "Authorization": f"Token token={API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def send_recording(payload: Dict[str, Any]) -> int | None:
    """
    Sends a JSON payload to the MARS API and returns the ID created if successful.
    """
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=15)
        if response.status_code == 201:
            data = response.json()
            new_id = data.get("id")
            logger.info(f"✅ Sleeping record created with id {new_id}")
            return new_id
        else:
            logger.error(f"⚠️ API error ({response.status_code}): {response.text[:300]}")
    except requests.RequestException as e:
        logger.exception(f"⛔️ Network error : {e}")

    return None


def send_batch(payloads: List[Dict[str, Any]]) -> None:
    """
    Send a batch of payloads to the API.
    """
    for i, payload in enumerate(payloads, 1):
        logger.info(f"--- Sending the payload {i}/{len(payloads)} ---")
        send_recording(payload)
