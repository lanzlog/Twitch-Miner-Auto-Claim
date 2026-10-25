#!/usr/bin/env python3
"""SMARTBOX device-code login for Twitch (the WEB/ANDROID device flow is disabled).

Runs the OAuth device flow with the SMARTBOX client id, prints the activation
code, polls until the user authorizes it, then writes cookies.jar + token.txt.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

HERE = Path(__file__).resolve().parent
CLIENT_ID = "ue6666qo983tsx6so1t0vnawi233wa"
UA = "Dalvik/2.1.0 (Linux; U; Android 16; SM-S911B Build/TP1A.220624.014) tv.twitch.android.app/25.3.0/2503006"
COOKIES = HERE / "cookies.jar"
TOKEN_FILE = HERE / "token.json"


async def main() -> int:
    headers = {
        "Client-Id": CLIENT_ID,
        "Accept": "application/json",
        "User-Agent": UA,
        "Origin": "https://www.twitch.tv",
        "Referer": "https://www.twitch.tv/",
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://id.twitch.tv/oauth2/device",
            headers=headers,
            data={"client_id": CLIENT_ID, "scopes": ""},
        ) as r:
            dev = await r.json()
        if "device_code" not in dev:
            print("device flow failed:", dev)
            return 2
        print(f"ACTIVATE_URL: {dev['verification_uri']}")
        print(f"ACTIVATE_CODE: {dev['user_code']}", flush=True)

        deadline = asyncio.get_running_loop().time() + dev["expires_in"]
        interval = dev.get("interval", 5)
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(interval)
            async with s.post(
                "https://id.twitch.tv/oauth2/token",
                headers=headers,
                data={
                    "client_id": CLIENT_ID,
                    "device_code": dev["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            ) as r:
                body = await r.json()
            if r.status == 200 and "access_token" in body:
                token = body["access_token"]
                jar = aiohttp.CookieJar()
                jar.update_cookies(
                    {"auth-token": token},
                    response_url=aiohttp.client.URL("https://www.twitch.tv/"),
                )
                jar.save(COOKIES)
                COOKIES.chmod(0o600)
                TOKEN_FILE.write_text(json.dumps(body, indent=2))
                TOKEN_FILE.chmod(0o600)
                print("LOGIN_OK: token stored", flush=True)
                return 0
            if body.get("message") not in ("authorization_pending", "slow_down"):
                print("poll:", r.status, body, flush=True)
        print("TIMEOUT: code expired", flush=True)
        return 3


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
