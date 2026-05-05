import logging
import random
import time

from curl_cffi import requests

GLUETUN_URL = "http://127.0.0.1:8000"
SWITCH_WAIT = 5
POLL_INTERVAL = 5
POLL_MAX = 24

logger = logging.getLogger(__name__)


def get_ip_info() -> dict:
    try:
        return requests.get(f"{GLUETUN_URL}/v1/publicip/ip", timeout=5).json()
    except Exception:
        return {}


def wait_for_tunnel() -> bool:
    logger.info("Waiting for VPN tunnel to be ready...")
    for attempt in range(POLL_MAX):
        if get_ip_info().get("public_ip"):
            return True
        logger.debug(f"Tunnel not ready (attempt {attempt + 1}/{POLL_MAX}), retrying in {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
    logger.warning("VPN tunnel did not become ready in time")
    return False


def switch_country(countries: list[str]) -> str:
    current = get_ip_info().get("country", "")
    candidates = [c for c in countries if c.lower() != current.lower()] or countries
    country = random.choice(candidates)
    logger.info(f"Switching VPN to '{country}'...")
    try:
        requests.put(
            f"{GLUETUN_URL}/v1/vpn/settings",
            json={"provider": {"server_selection": {"countries": [country]}}},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"Failed to send VPN switch request: {e}")
        return current
    time.sleep(SWITCH_WAIT)
    return country
