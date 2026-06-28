"""Async HTTP client for the Snark REST API.

Each method maps to one Snark endpoint and returns the parsed JSON. Any
non-2xx response or network failure is surfaced as ``SnarkAPIError`` with a
message suitable for showing to an LLM.
"""

from typing import Any
from urllib.parse import quote

import httpx

from .config import API_PREFIX, REQUEST_TIMEOUT, api_base_url


class SnarkAPIError(Exception):
    """The Snark API returned an error or could not be reached."""


class SnarkClient:
    def __init__(self, base_url: str | None = None, timeout: float = REQUEST_TIMEOUT):
        self._base_url = (base_url or api_base_url()).rstrip("/")
        self._timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{API_PREFIX}/{path}"

    @staticmethod
    def _params(values: dict) -> dict:
        # Drop None/empty values so we never send blank query params.
        return {k: v for k, v in values.items() if v}

    @staticmethod
    def _parse(resp: httpx.Response) -> Any:
        if resp.is_success:
            return resp.json()
        try:
            message = resp.json().get("error", resp.text)
        except Exception:
            message = resp.text or f"HTTP {resp.status_code}"
        raise SnarkAPIError(f"Snark API error ({resp.status_code}): {message}")

    async def _get(self, path: str, params: dict | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    self._url(path),
                    params=self._params(params or {}),
                    headers={"Accept": "application/json"},
                )
        except httpx.RequestError as exc:
            raise SnarkAPIError(
                f"Could not reach the Snark API at {self._base_url}: {exc}"
            ) from exc
        return self._parse(resp)

    async def _post(self, path: str, body: dict) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._url(path),
                    json=body,
                    headers={"Accept": "application/json"},
                )
        except httpx.RequestError as exc:
            raise SnarkAPIError(
                f"Could not reach the Snark API at {self._base_url}: {exc}"
            ) from exc
        return self._parse(resp)

    async def wit(self, persona, q="", mood=None, length=None, lang=None) -> dict:
        return await self._get(
            f"{persona}/", {"q": q, "mood": mood, "length": length, "lang": lang}
        )

    async def roast(self, name, mood=None, length=None, lang=None) -> dict:
        return await self._get(
            f"roast/{quote(name, safe='')}/", {"mood": mood, "length": length, "lang": lang}
        )

    async def roast_github(self, username, mood=None, length=None, lang=None) -> dict:
        return await self._get(
            f"roast-github/{quote(username, safe='')}/",
            {"mood": mood, "length": length, "lang": lang},
        )

    async def worth_it(self, thing, mood=None, length=None, lang=None) -> dict:
        return await self._get(
            "worth-it/", {"q": thing, "mood": mood, "length": length, "lang": lang}
        )

    async def reply(self, post, mood=None, length=None, lang=None) -> dict:
        body = {"post": post}
        for key, value in {"mood": mood, "length": length, "lang": lang}.items():
            if value:
                body[key] = value
        return await self._post("reply/", body)

    async def list_personas(self) -> list:
        return await self._get("personas/")
