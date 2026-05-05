import logging
import os
from typing import Any

from curl_cffi import requests as cffi_requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

import vpn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="VPN Proxy")

VPN_COUNTRIES = [c.strip() for c in os.environ.get("SERVER_COUNTRIES", "Netherlands").split(",") if c.strip()]
MAX_RETRIES = int(os.environ.get("VPN_MAX_RETRIES", "3"))
BLOCKED_STATUSES = {403, 429, 503}


class RequestPayload(BaseModel):
    url: str
    method: str = "GET"
    headers: dict[str, str] = {}
    body: str | None = None


class RequestResponse(BaseModel):
    status_code: int
    headers: dict[str, str]
    vpn_country: str
    vpn_ip: str
    retries: int


@app.get("/health")
def health() -> dict[str, Any]:
    ip_info = vpn.get_ip_info()
    return {
        "vpn_ip": ip_info.get("public_ip"),
        "vpn_country": ip_info.get("country"),
        "tunnel_ready": bool(ip_info.get("public_ip")),
    }


@app.post("/switch")
def switch() -> dict[str, str]:
    country = vpn.switch_country(VPN_COUNTRIES)
    vpn.wait_for_tunnel()
    ip_info = vpn.get_ip_info()
    return {
        "switched_to": country,
        "vpn_ip": ip_info.get("public_ip", ""),
    }


@app.post("/request", response_model=RequestResponse)
def proxy_request(payload: RequestPayload) -> RequestResponse:
    retries = 0

    for attempt in range(MAX_RETRIES + 1):
        ip_info = vpn.get_ip_info()

        try:
            resp = cffi_requests.request(
                method=payload.method.upper(),
                url=payload.url,
                headers=payload.headers,
                data=payload.body,
                timeout=30,
                impersonate="chrome120",
            )
        except Exception as e:
            if attempt >= MAX_RETRIES:
                raise HTTPException(status_code=502, detail=f"Request failed after {retries} retries: {e}")
            logger.warning(f"Request error (attempt {attempt + 1}): {e}, switching country...")
            vpn.switch_country(VPN_COUNTRIES)
            vpn.wait_for_tunnel()
            retries += 1
            continue

        if resp.status_code in BLOCKED_STATUSES and attempt < MAX_RETRIES:
            logger.info(f"Blocked (HTTP {resp.status_code}) on attempt {attempt + 1}, switching country...")
            vpn.switch_country(VPN_COUNTRIES)
            vpn.wait_for_tunnel()
            retries += 1
            continue

        return RequestResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            vpn_country=ip_info.get("country", ""),
            vpn_ip=ip_info.get("public_ip", ""),
            retries=retries,
        )

    raise HTTPException(status_code=502, detail=f"Request blocked after {retries} country switches")


EXCLUDED_HEADERS = {"host", "content-length", "transfer-encoding", "connection", "user-agent"}


@app.api_route("/proxy/{url:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy(url: str, request: Request) -> Response:
    if request.query_params:
        url = f"{url}?{request.query_params}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in EXCLUDED_HEADERS}
    body = await request.body()

    try:
        resp = cffi_requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=body or None,
            impersonate="chrome120",
            allow_redirects=False,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in {"transfer-encoding", "connection"}}
    return Response(content=resp.content, status_code=resp.status_code, headers=response_headers)
