#!/usr/bin/env python3
"""Headless runner for TwitchDropsMiner (no X11, no tkinter)."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / "TwitchDropsMiner"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import headless_gui  # noqa: E402

sys.modules["gui"] = headless_gui  # must happen before twitch.py import

from settings import Settings  # noqa: E402
from twitch import Twitch  # noqa: E402
from exceptions import ExitRequest  # noqa: E402


def build_args() -> argparse.Namespace:
    return argparse.Namespace(
        _verbose=1,
        _debug_ws=0,
        _debug_gql=0,
        log=True,
        tray=False,
        dump=False,
    )


async def amain() -> None:
    cookies = HERE / "cookies.jar"
    if not cookies.exists():
        print(
            "NEED_TOKEN: no cookies.jar found.\n"
            "  env/bin/python set_auth.py <auth-token> [user_id]\n"
            "  (auth-token: twitch.tv → DevTools → Application → Cookies → auth-token)",
            flush=True,
        )
        raise SystemExit(2)
    settings = Settings(build_args())
    twitch = Twitch(settings)
    # Use the SMARTBOX client: WEB/ANDROID device login is disabled and WEB GQL
    # campaign queries now require a browser integrity token (IntegrityCheckFailed).
    try:
        from constants import ClientType, PriorityMode

        twitch._client_type = ClientType.SMARTBOX
        # Operator scope: Albion Online only. PRIORITY_ONLY + priority list means
        # the engine ignores every other game's campaigns.
        twitch.settings.priority_mode = PriorityMode.PRIORITY_ONLY
        twitch.settings.priority = ["Albion Online"]
        twitch.settings.exclude = set()
        twitch.settings.available_drops_check = True
    except Exception:  # pragma: no cover - engine layout change
        pass
    try:
        await twitch.run()
    except (ExitRequest, asyncio.CancelledError):
        pass
    except Exception as exc:  # noqa: BLE001 - surface a clean, actionable error
        if os.getenv("MINER_DEBUG"):
            import traceback

            traceback.print_exc()
        print(
            f"AUTH/RUNTIME FAILED: {type(exc).__name__}: {exc}\n"
            "  Most likely the auth-token cookie is invalid or expired.\n"
            "  Re-run: env/bin/python set_auth.py <fresh auth-token> [user_id]",
            flush=True,
        )
        raise SystemExit(3) from None
    finally:
        await twitch.shutdown()


def main() -> int:
    level = 19 if os.getenv("MINER_VERBOSE") else logging.INFO  # 19 = engine's CALL level
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(HERE / "miner.log", encoding="utf-8"),
        ],
    )
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
