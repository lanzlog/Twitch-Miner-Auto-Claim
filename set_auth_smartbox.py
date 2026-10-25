#!/usr/bin/env python3
"""Write cookies.jar for the SMARTBOX client URL (android.tv.twitch.tv).

Engine's cookie restore filters cookies by client URL, so an auth-token stored
for `twitch.tv` is invisible to the SMARTBOX client.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

HERE = Path(__file__).resolve().parent
COOKIES = HERE / "cookies.jar"
TOKEN_FILE = HERE / "token.json"


async def main() -> int:
    token = json.loads(TOKEN_FILE.read_text())["access_token"]
    jar = aiohttp.CookieJar()
    for url in ("https://android.tv.twitch.tv/", "https://www.twitch.tv/"):
        jar.update_cookies(
            {"auth-token": token}, response_url=aiohttp.client.URL(url)
        )
    jar.save(COOKIES)
    COOKIES.chmod(0o600)
    print(f"wrote {COOKIES} for android.tv.twitch.tv + www.twitch.tv")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
