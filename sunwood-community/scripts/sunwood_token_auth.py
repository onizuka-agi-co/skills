#!/usr/bin/env python3
"""Shared X OAuth token loading and refresh helpers for sunwood-community scripts."""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
DATA_X_DIR = WORKSPACE_ROOT / "data" / "x"
HOST_CONFIG_DATA_DIR = WORKSPACE_ROOT.parent.parent / "x-filtered-stream" / "data"
CONTAINER_CONFIG_DATA_DIR = Path("/config/x-filtered-stream/data")
TOKEN_ENV_VAR = "SUNWOOD_COMMUNITY_TOKEN_FILE"
CLIENT_CREDENTIALS_ENV_VAR = "SUNWOOD_COMMUNITY_CLIENT_CREDENTIALS_FILE"


def unique_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def resolve_data_file(env_var: str, default_name: str) -> Path:
    candidates: list[Path] = []
    env_value = os.environ.get(env_var)
    if env_value:
        candidates.append(Path(env_value).expanduser())

    candidates.extend(
        [
            DATA_X_DIR / default_name,
            CONTAINER_CONFIG_DATA_DIR / default_name,
            HOST_CONFIG_DATA_DIR / default_name,
        ]
    )

    for candidate in unique_paths(candidates):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"{default_name} not found. Checked env {env_var} and: "
        + ", ".join(str(path) for path in unique_paths(candidates))
    )


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def compute_expires_at(token_data: dict[str, Any]) -> float | None:
    raw_expires_at = token_data.get("expires_at")
    if isinstance(raw_expires_at, (int, float)):
        return float(raw_expires_at)

    expires_in = token_data.get("expires_in")
    obtained_at = token_data.get("obtained_at")
    if isinstance(expires_in, (int, float)) and isinstance(obtained_at, (int, float)):
        return float(obtained_at) + float(expires_in)

    return None


def is_token_expired(token_data: dict[str, Any]) -> bool:
    expires_at = compute_expires_at(token_data)
    if expires_at is None:
        return False
    return datetime.now(timezone.utc).timestamp() > (expires_at - 300)


def refresh_access_token(
    token_file: Path,
    credentials_file: Path,
    token_data: dict[str, Any],
) -> dict[str, Any]:
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(f"refresh_token is missing in {token_file}")

    credentials = load_json(credentials_file)
    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    if not client_id or not client_secret:
        raise ValueError(f"client_id/client_secret are missing in {credentials_file}")

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.x.com/2/oauth2/token",
        data=body,
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        refreshed = json.loads(response.read().decode("utf-8"))

    refreshed["obtained_at"] = int(datetime.now(timezone.utc).timestamp())
    if "expires_in" in refreshed and "expires_at" not in refreshed:
        refreshed["expires_at"] = refreshed["obtained_at"] + int(refreshed["expires_in"])
    save_json(token_file, refreshed)
    return refreshed


def load_token_context() -> dict[str, Any]:
    token_file = resolve_data_file(TOKEN_ENV_VAR, "x-tokens.json")
    token_data = load_json(token_file)
    if "access_token" not in token_data:
        raise ValueError(f"access_token is missing in {token_file}")

    credentials_file = resolve_data_file(CLIENT_CREDENTIALS_ENV_VAR, "x-client-credentials.json")
    return {
        "token_file": token_file,
        "credentials_file": credentials_file,
        "token_data": token_data,
    }


def ensure_valid_token(context: dict[str, Any], *, force_refresh: bool = False) -> str:
    token_data = context["token_data"]
    if force_refresh or is_token_expired(token_data):
        token_data = refresh_access_token(
            context["token_file"],
            context["credentials_file"],
            token_data,
        )
        context["token_data"] = token_data

    token = token_data.get("access_token", "")
    if not token:
        raise ValueError(f"access_token is missing in {context['token_file']}")
    return token


def request_httpx(
    method: str,
    url: str,
    token_context: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
    **kwargs: Any,
) -> httpx.Response:
    attempts = [False, True]
    for force_refresh in attempts:
        token = ensure_valid_token(token_context, force_refresh=force_refresh)
        merged_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            merged_headers.update(headers)

        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, headers=merged_headers, **kwargs)

        if response.status_code == 401 and not force_refresh:
            continue
        response.raise_for_status()
        return response

    raise RuntimeError("HTTP request failed after token refresh retry.")
