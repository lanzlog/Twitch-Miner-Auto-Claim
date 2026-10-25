"""Headless stand-in for TwitchDropsMiner's `gui` module (no tkinter/pystray/PIL).

Every widget is a no-op stub. `_Noop` gives each class a `__getattr__` fallback so an
engine code path we haven't stubbed (e.g. hourly cleanup calling channels.remove())
logs a warning instead of crashing the miner with AttributeError.
"""
from __future__ import annotations

import asyncio
import builtins
import logging
import time
from pathlib import Path

log = logging.getLogger("gui")

HERE = Path(__file__).resolve().parent
ACTIVATE_FILE = HERE / "ACTIVATE.txt"


def print(message: str) -> None:  # noqa: A001 - engine calls gui.print()
    """Engine output channel (claim messages, notices) -> log."""
    log.info("output: %s", message)


class _Noop:
    """Fallback: unknown GUI attributes become harmless no-op callables."""

    def __getattr__(self, name):  # only called when normal lookup fails
        if name.startswith("__"):
            raise AttributeError(name)
        log.warning("headless gui: unstubbed call %s.%s()", type(self).__name__, name)
        return lambda *a, **kw: None


class _Status(_Noop):
    def update(self, text: str) -> None:
        log.info("[status] %s", text)


class _Progress(_Noop):
    """Minute ticker: the engine bumps watch minutes when minute_almost_done() is True."""

    def __init__(self) -> None:
        self._last_tick = 0.0

    def start_timer(self) -> None:
        pass

    def stop_timer(self) -> None:
        self._last_tick = 0.0

    def minute_almost_done(self) -> bool:
        now = time.monotonic()
        if now - self._last_tick >= 55:
            self._last_tick = now
            return True
        return False


class _Tray(_Noop):
    def change_icon(self, name: str) -> None:
        pass

    def notify(self, *a, **kw) -> None:
        pass


class _Channels(_Noop):
    def clear(self) -> None:
        pass

    def clear_watching(self) -> None:
        pass

    def get_selection(self):
        return None

    def set_watching(self, channel) -> None:
        log.info("watching channel: %s", getattr(channel, "name", channel))

    def display(self, channel, *, add: bool = True) -> None:
        log.info(
            "%s channel: %s",
            "add" if add else "remove",
            getattr(channel, "name", channel),
        )

    def remove(self, channel) -> None:
        log.info("drop channel: %s", getattr(channel, "name", channel))


class _Inventory(_Noop):
    def clear(self) -> None:
        pass

    async def add_campaign(self, campaign) -> None:
        pass

    def update_drop(self, *a, **kw) -> None:
        pass


class _Btn(_Noop):
    def config(self, *a, **kw) -> None:
        pass


class _Help(_Noop):
    def __init__(self) -> None:
        self._invalidate_button = _Btn()


class _Websockets(_Noop):
    def remove(self, *a, **kw) -> None:
        pass

    def update(self, *a, **kw) -> None:
        pass


class _Login(_Noop):
    async def ask_enter_code(self, verification_uri, user_code) -> None:
        msg = f"ACTIVATE: {verification_uri}  CODE: {user_code}"
        log.warning(msg)
        ACTIVATE_FILE.write_text(msg + "\n")
        builtins.print(msg, flush=True)

    async def ask_login(self) -> None:
        log.error("Interactive login not available headless; provide cookies.jar.")
        raise RuntimeError("headless: interactive login unsupported")

    def clear(self, *a, **kw) -> None:
        pass

    def update(self, *a, **kw) -> None:
        pass


class GUIManager(_Noop):
    def __init__(self, twitch) -> None:
        self._twitch = twitch
        self.status = _Status()
        self.progress = _Progress()
        self.tray = _Tray()
        self.channels = _Channels()
        self.inv = _Inventory()
        self.help = _Help()
        self.websockets = _Websockets()
        self.login = _Login()
        self.close_requested = False
        self._closed = asyncio.Event()

    def start(self) -> None:
        log.info("headless mode started")

    def close(self) -> None:
        self.close_requested = True
        self._closed.set()

    async def wait_until_closed(self) -> None:
        await self._closed.wait()

    def prevent_close(self) -> None:
        pass

    def print(self, message: str) -> None:
        log.info("%s", message)

    def save(self, *, force: bool = False) -> None:
        try:
            self._twitch.save(force=force)
        except Exception:
            log.debug("save failed", exc_info=True)

    def set_games(self, games) -> None:
        pass

    def clear_drop(self) -> None:
        pass

    def display_drop(self, *a, **kw) -> None:
        pass

    async def coro_unless_closed(self, coro):
        return await coro
